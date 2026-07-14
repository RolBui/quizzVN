import hashlib
import logging
import secrets
import string
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import hash_password, utc_now, verify_password
from app.models.admin_invitation import AdminInvitation
from app.models.classroom import Classroom
from app.models.classroom_membership import ClassroomMembership
from app.models.exam import Exam
from app.models.exam_attempt import ExamAttempt
from app.models.exam_attempt_answer import ExamAttemptAnswer  # noqa: F401 - registers SQLAlchemy relationships.
from app.models.exam_question import ExamQuestion
from app.models.exam_question_option import ExamQuestionOption  # noqa: F401 - registers SQLAlchemy relationships.
from app.models.learning_document import LearningDocument
from app.models.oauth_account import OAuthAccount  # noqa: F401 - registers SQLAlchemy relationships.
from app.models.oauth_provider import OAuthProvider  # noqa: F401 - registers SQLAlchemy relationships.
from app.models.role import Role
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_session import UserSession
from app.services.auth_service import (
    ADMIN_ACCESS_ROLE_NAMES,
    ADMIN_PERMISSION_KEYS,
    ADMIN_ROLE_NAME,
    ADMINISTRATOR_ROLE_NAME,
    build_username_from_email,
    create_admin_password_setup_token,
    encode_admin_permissions,
    get_or_create_role,
    normalize_admin_permissions,
)
from app.services.email_templates import render_action_email, render_notice_email, render_otp_email
from app.services.email_verification_service import send_email
from app.services.exam_creator_metadata import build_exam_creator_metadata, get_ai_generated_exam_ids
from app.services.media_service import delete_document_file, upload_document_file
from app.services.teacher_service import (
    SCOPE_CLASS,
    SCOPE_SYSTEM,
    _normalize_exam_grade,
    _replace_exam_questions,
    _serialize_exam_detail,
    _validate_exam_questions,
    _validate_exam_schedule,
)

ATTEMPT_STATUS_SUBMITTED = "submitted"
ADMIN_MUTABLE_STATUSES = {"active", "disabled"}
ADMIN_INVITATION_PENDING_STATUSES = {"otp_pending", "pending_approval"}
ADMIN_INVITATION_STATUSES = {"otp_pending", "pending_approval", "approved", "rejected", "expired"}
TEACHER_ROLE_NAME = "teacher"
STUDENT_ROLE_NAME = "student"
USER_ACTIVITY_WINDOW = timedelta(hours=1)
ADMIN_INVITATION_OTP_RESEND_COOLDOWN = timedelta(seconds=60)
DEFAULT_EXAM_GRADE = "Chưa phân loại"
logger = logging.getLogger(__name__)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _recent_activity_user_ids(db: Session, user_ids: list[int]) -> set[int]:
    if not user_ids:
        return set()

    active_after = utc_now() - USER_ACTIVITY_WINDOW
    return {
        user_id
        for (user_id,) in db.query(UserSession.user_id)
        .filter(
            UserSession.user_id.in_(user_ids),
            UserSession.is_revoked.is_(False),
            func.coalesce(UserSession.last_used_at, UserSession.created_at) >= active_after,
        )
        .all()
    }


def _start_of_month(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _start_of_day(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return value.replace(year=year, month=month, day=1)


def _start_of_year(value: datetime) -> datetime:
    return value.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)


def _count_between(db: Session, model, column, start: datetime, end: datetime) -> int:
    return int(
        db.query(func.count(model.id))
        .filter(column >= start, column < end)
        .scalar()
        or 0
    )


def _crm_period_window(now: datetime, period: str) -> dict:
    if period == "30d":
        day_count = 30
        current_start = _start_of_day(now) - timedelta(days=day_count - 1)
        previous_start = current_start - timedelta(days=day_count)
        return {
            "period": "30d",
            "label": "30 ngày qua",
            "current_start": current_start,
            "current_end": now,
            "previous_start": previous_start,
            "previous_end": current_start,
            "day_count": day_count,
            "granularity": "day",
        }

    if period == "year":
        current_start = _start_of_year(now)
        previous_start = current_start.replace(year=current_start.year - 1)
        previous_end = previous_start + (now - current_start)
        return {
            "period": "year",
            "label": "năm nay",
            "current_start": current_start,
            "current_end": now,
            "previous_start": previous_start,
            "previous_end": previous_end,
            "day_count": None,
            "granularity": "month",
        }

    day_count = 7
    current_start = _start_of_day(now) - timedelta(days=day_count - 1)
    previous_start = current_start - timedelta(days=day_count)
    return {
        "period": "7d",
        "label": "7 ngày qua",
        "current_start": current_start,
        "current_end": now,
        "previous_start": previous_start,
        "previous_end": current_start,
        "day_count": day_count,
        "granularity": "day",
    }


def _count_active_users_between(db: Session, start: datetime, end: datetime) -> int:
    rows = (
        db.query(UserSession.user_id, UserSession.created_at, UserSession.last_used_at)
        .join(User, User.id == UserSession.user_id)
        .filter(
            User.status == "active",
            UserSession.is_revoked.is_(False),
            or_(UserSession.created_at >= start, UserSession.last_used_at >= start),
            or_(UserSession.created_at < end, UserSession.last_used_at < end),
        )
        .all()
    )

    active_user_ids = set()
    for user_id, created_at, last_used_at in rows:
        activity_at = _normalize_datetime(last_used_at) or _normalize_datetime(created_at)
        if activity_at is not None and start <= activity_at < end:
            active_user_ids.add(user_id)
    return len(active_user_ids)


def _recent_month_starts(now: datetime, count: int = 12) -> list[datetime]:
    current_month_start = _start_of_month(now)
    return [
        _add_months(current_month_start, offset)
        for offset in range(-(count - 1), 1)
    ]


def _build_monthly_counts(
    db: Session,
    model,
    column,
    starts: list[datetime],
    *criteria,
) -> list[int]:
    if not starts:
        return []

    end = _add_months(starts[-1], 1)
    counts = {(start.year, start.month): 0 for start in starts}
    query = db.query(column).filter(column >= starts[0], column < end)
    if criteria:
        query = query.filter(*criteria)
    rows = query.all()

    for (created_at,) in rows:
        normalized = _normalize_datetime(created_at)
        if normalized is None:
            continue
        key = (normalized.year, normalized.month)
        if key in counts:
            counts[key] += 1

    return [counts[(start.year, start.month)] for start in starts]


def _build_cumulative_monthly_counts(
    db: Session,
    model,
    column,
    starts: list[datetime],
    *criteria,
) -> list[int]:
    if not starts:
        return []

    query = db.query(func.count(model.id)).filter(column < starts[0])
    if criteria:
        query = query.filter(*criteria)
    running_total = int(query.scalar() or 0)
    monthly_counts = _build_monthly_counts(db, model, column, starts, *criteria)
    totals = []

    for count in monthly_counts:
        running_total += count
        totals.append(running_total)

    return totals


def _build_monthly_active_user_counts(db: Session, starts: list[datetime]) -> list[int]:
    if not starts:
        return []

    end = _add_months(starts[-1], 1)
    buckets = {(start.year, start.month): set() for start in starts}
    rows = (
        db.query(
            UserSession.user_id,
            UserSession.created_at,
            UserSession.last_used_at,
        )
        .join(User, User.id == UserSession.user_id)
        .filter(
            User.status == "active",
            UserSession.is_revoked.is_(False),
            or_(
                UserSession.created_at >= starts[0],
                UserSession.last_used_at >= starts[0],
            ),
            or_(UserSession.created_at < end, UserSession.last_used_at < end),
        )
        .all()
    )

    for user_id, created_at, last_used_at in rows:
        activity_at = _normalize_datetime(last_used_at) or _normalize_datetime(created_at)
        if activity_at is None or activity_at < starts[0] or activity_at >= end:
            continue
        key = (activity_at.year, activity_at.month)
        if key in buckets:
            buckets[key].add(user_id)

    return [len(buckets[(start.year, start.month)]) for start in starts]


def _status_label(status: str | None) -> str:
    if status == "active":
        return "Hoạt động"
    if status == "disabled":
        return "Vô hiệu hóa"
    return status or "Không rõ"


def _metric(
    key: str,
    label: str,
    value: float,
    suffix: str = "",
    trend: str = "0%",
    is_up: bool = True,
    subtext: str = "",
    sparkline: list[int] | None = None,
) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "suffix": suffix,
        "trend": trend,
        "is_up": is_up,
        "subtext": subtext,
        "sparkline": sparkline or [],
    }


def _count_by(rows: list[tuple[int | None, int]]) -> dict[int, int]:
    return {key: int(value or 0) for key, value in rows if key is not None}


def _serialize_exam_grade(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or DEFAULT_EXAM_GRADE


def _format_percent_trend(current: int, previous: int) -> str:
    if previous == 0:
        if current == 0:
            return "0%"
        return "+100%"
    return f"{((current - previous) / previous) * 100:+.1f}%"


def _format_number_trend(current: int, previous: int) -> str:
    return f"{current - previous:+d}"


def _score_percent(score: float | None, total_points: float | None) -> float:
    if not total_points:
        return 0.0
    return round(((score or 0) / total_points) * 100, 2)


def _score_label(score_percent: float) -> str:
    return f"{score_percent / 10:.1f}"


def _build_metrics(db: Session, now: datetime, period: str = "7d") -> list[dict]:
    window = _crm_period_window(now, period)
    current_start = window["current_start"]
    current_end = window["current_end"]
    previous_start = window["previous_start"]
    previous_end = window["previous_end"]
    period_label = window["label"]
    sparkline_months = _recent_month_starts(now)

    current_period_exams = _count_between(
        db, Exam, Exam.created_at, current_start, current_end
    )
    previous_period_exams = _count_between(
        db, Exam, Exam.created_at, previous_start, previous_end
    )

    current_period_users = _count_between(
        db, User, User.created_at, current_start, current_end
    )
    previous_period_users = _count_between(
        db, User, User.created_at, previous_start, previous_end
    )

    active_users = _count_active_users_between(db, current_start, current_end)
    previous_active_users = _count_active_users_between(db, previous_start, previous_end)
    total_users = int(db.query(func.count(User.id)).scalar() or 0)
    monthly_exam_creations = _build_monthly_counts(
        db, Exam, Exam.created_at, sparkline_months
    )
    monthly_user_creations = _build_monthly_counts(
        db, User, User.created_at, sparkline_months
    )
    monthly_active_users = _build_monthly_active_user_counts(db, sparkline_months)
    monthly_total_users = _build_cumulative_monthly_counts(
        db, User, User.created_at, sparkline_months
    )

    return [
        {
            "key": "total_exams",
            "label": "Tổng đề thi",
            "value": current_period_exams,
            "trend": _format_percent_trend(current_period_exams, previous_period_exams),
            "is_up": current_period_exams >= previous_period_exams,
            "sparkline": monthly_exam_creations,
            "subtext": period_label,
        },
        {
            "key": "new_users",
            "label": "User mới",
            "value": current_period_users,
            "trend": _format_percent_trend(current_period_users, previous_period_users),
            "is_up": current_period_users >= previous_period_users,
            "sparkline": monthly_user_creations,
            "subtext": period_label,
        },
        {
            "key": "active_users",
            "label": "Đang hoạt động",
            "value": active_users,
            "trend": _format_percent_trend(active_users, previous_active_users),
            "is_up": active_users >= previous_active_users,
            "sparkline": monthly_active_users,
            "subtext": period_label,
        },
        {
            "key": "total_users",
            "label": "Tổng user",
            "value": total_users,
            "trend": _format_percent_trend(current_period_users, previous_period_users),
            "is_up": current_period_users >= previous_period_users,
            "sparkline": monthly_total_users,
            "subtext": "tổng tài khoản hệ thống",
        },
    ]


def _build_daily_traffic(db: Session, now: datetime, period: str) -> list[dict]:
    window = _crm_period_window(now, period)
    day_count = int(window["day_count"] or 7)
    current_start = window["current_start"]
    previous_start = window["previous_start"]
    current_counts = [0 for _ in range(day_count)]
    previous_counts = [0 for _ in range(day_count)]
    current_end = current_start + timedelta(days=day_count)

    rows = (
        db.query(ExamAttempt.created_at)
        .filter(
            ExamAttempt.created_at >= previous_start,
            ExamAttempt.created_at < current_end,
        )
        .all()
    )

    for (created_at,) in rows:
        normalized = _normalize_datetime(created_at)
        if normalized is None:
            continue
        if current_start <= normalized < current_end:
            current_counts[(normalized.date() - current_start.date()).days] += 1
        elif previous_start <= normalized < current_start:
            previous_counts[(normalized.date() - previous_start.date()).days] += 1

    return [
        {
            "name": (current_start + timedelta(days=index)).strftime("%d/%m"),
            "current": current_counts[index],
            "last": previous_counts[index],
        }
        for index in range(day_count)
    ]


def _build_traffic(db: Session, now: datetime, period: str = "year") -> list[dict]:
    if period in {"7d", "30d"}:
        return _build_daily_traffic(db, now, period)

    current_year_start = _start_of_year(now)
    previous_year_start = current_year_start.replace(year=current_year_start.year - 1)
    next_year_start = current_year_start.replace(year=current_year_start.year + 1)
    current_counts = [0 for _ in range(12)]
    previous_counts = [0 for _ in range(12)]

    rows = (
        db.query(ExamAttempt.created_at)
        .filter(
            ExamAttempt.created_at >= previous_year_start,
            ExamAttempt.created_at < next_year_start,
        )
        .all()
    )

    for (created_at,) in rows:
        normalized = _normalize_datetime(created_at)
        if normalized is None:
            continue
        if normalized.year == current_year_start.year:
            current_counts[normalized.month - 1] += 1
        elif normalized.year == previous_year_start.year:
            previous_counts[normalized.month - 1] += 1

    return [
        {
            "name": f"T{month}",
            "current": current_counts[month - 1],
            "last": previous_counts[month - 1],
        }
        for month in range(1, 13)
    ]


def _build_score_distribution(
    db: Session,
    start: datetime,
    end: datetime,
) -> list[dict]:
    bucket_names = ["< 5", "5-6", "6-7", "7-8", "8-9", "9-10"]
    bucket_counts = {name: 0 for name in bucket_names}
    rows = (
        db.query(ExamAttempt.score, ExamAttempt.total_points)
        .filter(
            ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED,
            ExamAttempt.submitted_at >= start,
            ExamAttempt.submitted_at < end,
        )
        .all()
    )

    for score, total_points in rows:
        percent = _score_percent(score, total_points)
        if percent < 50:
            bucket_counts["< 5"] += 1
        elif percent < 60:
            bucket_counts["5-6"] += 1
        elif percent < 70:
            bucket_counts["6-7"] += 1
        elif percent < 80:
            bucket_counts["7-8"] += 1
        elif percent < 90:
            bucket_counts["8-9"] += 1
        else:
            bucket_counts["9-10"] += 1

    return [{"name": name, "users": bucket_counts[name]} for name in bucket_names]


def _build_recent_results(
    db: Session,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict]:
    query = (
        db.query(
            ExamAttempt.id,
            ExamAttempt.score,
            ExamAttempt.total_points,
            ExamAttempt.submitted_at,
            User.full_name,
            Exam.title,
        )
        .join(User, User.id == ExamAttempt.user_id)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .filter(
            ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED,
            ExamAttempt.submitted_at.isnot(None),
        )
    )
    if start is not None:
        query = query.filter(ExamAttempt.submitted_at >= start)
    if end is not None:
        query = query.filter(ExamAttempt.submitted_at < end)

    rows = query.order_by(ExamAttempt.submitted_at.desc(), ExamAttempt.id.desc()).limit(5).all()

    results = []
    for attempt_id, score, total_points, submitted_at, student_name, exam_title in rows:
        score_percent = _score_percent(score, total_points)
        results.append(
            {
                "attempt_id": attempt_id,
                "code": f"#EX{attempt_id:04d}",
                "student_name": student_name,
                "exam_title": exam_title,
                "submitted_at": submitted_at,
                "score_label": _score_label(score_percent),
                "score_percent": score_percent,
                "status": "Hoàn thành" if score_percent >= 50 else "Cần cải thiện",
            }
        )
    return results


def get_admin_crm_overview(db: Session, period: str = "7d") -> dict:
    now = utc_now()
    window = _crm_period_window(now, period)
    return {
        "metrics": _build_metrics(db, now, window["period"]),
        "traffic": _build_traffic(db, now, window["period"]),
        "score_distribution": _build_score_distribution(
            db,
            window["current_start"],
            window["current_end"],
        ),
        "recent_results": _build_recent_results(
            db,
            window["current_start"],
            window["current_end"],
        ),
        "last_updated_at": now,
    }


def get_admin_teachers_overview(db: Session) -> dict:
    now = utc_now()
    month_start = _start_of_month(now)
    previous_month_start = _add_months(month_start, -1)
    sparkline_months = _recent_month_starts(now)

    teachers = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.role))
        .filter(
            User.role.has(Role.name == TEACHER_ROLE_NAME),
            User.status != "deleted",
        )
        .order_by(User.created_at.desc(), User.id.desc())
        .all()
    )
    teacher_ids = [teacher.id for teacher in teachers]

    class_counts: dict[int, int] = {}
    exam_counts: dict[int, int] = {}
    document_counts: dict[int, int] = {}
    if teacher_ids:
        class_counts = _count_by(
            db.query(Classroom.created_by_user_id, func.count(Classroom.id))
            .filter(Classroom.created_by_user_id.in_(teacher_ids))
            .group_by(Classroom.created_by_user_id)
            .all()
        )
        exam_counts = _count_by(
            db.query(Exam.created_by_user_id, func.count(Exam.id))
            .filter(Exam.created_by_user_id.in_(teacher_ids))
            .group_by(Exam.created_by_user_id)
            .all()
        )
        document_counts = _count_by(
            db.query(LearningDocument.created_by_user_id, func.count(LearningDocument.id))
            .filter(LearningDocument.created_by_user_id.in_(teacher_ids))
            .group_by(LearningDocument.created_by_user_id)
            .all()
        )

    current_month_teachers = int(
        db.query(func.count(User.id))
        .filter(
            User.role.has(Role.name == TEACHER_ROLE_NAME),
            User.status != "deleted",
            User.created_at >= month_start,
        )
        .scalar()
        or 0
    )
    previous_month_teachers = int(
        db.query(func.count(User.id))
        .filter(
            User.role.has(Role.name == TEACHER_ROLE_NAME),
            User.status != "deleted",
            User.created_at >= previous_month_start,
            User.created_at < month_start,
        )
        .scalar()
        or 0
    )
    active_teachers = 0
    total_teacher_sparkline = _build_cumulative_monthly_counts(
        db,
        User,
        User.created_at,
        sparkline_months,
        User.role.has(Role.name == TEACHER_ROLE_NAME),
        User.status != "deleted",
    )
    active_teacher_sparkline = [0 for _ in sparkline_months]
    teacher_exam_sparkline = (
        _build_cumulative_monthly_counts(
            db,
            Exam,
            Exam.created_at,
            sparkline_months,
            Exam.created_by_user_id.in_(teacher_ids),
        )
        if teacher_ids
        else [0 for _ in sparkline_months]
    )
    teacher_class_sparkline = (
        _build_cumulative_monthly_counts(
            db,
            Classroom,
            Classroom.created_at,
            sparkline_months,
            Classroom.created_by_user_id.in_(teacher_ids),
        )
        if teacher_ids
        else [0 for _ in sparkline_months]
    )

    active_session_user_ids = _recent_activity_user_ids(db, teacher_ids)
    active_teachers = len(active_session_user_ids)
    active_teacher_sparkline = [active_teachers for _ in sparkline_months]

    return {
        "metrics": [
            _metric("total_teachers", "Tổng giáo viên", len(teachers), trend=_format_percent_trend(current_month_teachers, previous_month_teachers), is_up=current_month_teachers >= previous_month_teachers, subtext="so với tháng trước", sparkline=total_teacher_sparkline),
            _metric("active_teachers", "Đang hoạt động", active_teachers, subtext="có tương tác trong 1 giờ qua", sparkline=active_teacher_sparkline),
            _metric("total_exams", "Đề thi đã tạo", sum(exam_counts.values()), subtext="từ tài khoản giáo viên", sparkline=teacher_exam_sparkline),
            _metric("total_classes", "Lớp đang quản lý", sum(class_counts.values()), subtext="lớp do giáo viên tạo", sparkline=teacher_class_sparkline),
        ],
        "items": [
            {
                "id": teacher.id,
                "code": f"TCH-{teacher.id:04d}",
                "full_name": teacher.full_name,
                "username": teacher.username,
                "email": teacher.email,
                "phone": teacher.phone,
                "avatar_url": teacher.avatar_url,
                "status": teacher.status,
                "is_online": teacher.id in active_session_user_ids,
                "school_name": teacher.profile.school_name if teacher.profile else None,
                "date_of_birth": teacher.profile.date_of_birth if teacher.profile else None,
                "gender": teacher.profile.gender if teacher.profile else None,
                "class_count": class_counts.get(teacher.id, 0),
                "exam_count": exam_counts.get(teacher.id, 0),
                "document_count": document_counts.get(teacher.id, 0),
                "last_login_at": teacher.last_login_at,
                "created_at": teacher.created_at,
            }
            for teacher in teachers
        ],
    }


def get_admin_students_overview(db: Session) -> dict:
    now = utc_now()
    month_start = _start_of_month(now)
    previous_month_start = _add_months(month_start, -1)
    sparkline_months = _recent_month_starts(now)

    students = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.role))
        .filter(
            User.role.has(Role.name == STUDENT_ROLE_NAME),
            User.status != "deleted",
        )
        .order_by(User.created_at.desc(), User.id.desc())
        .all()
    )
    student_ids = [student.id for student in students]

    class_counts: dict[int, int] = {}
    attempt_counts: dict[int, int] = {}
    average_scores: dict[int, float | None] = {}
    if student_ids:
        class_counts = _count_by(
            db.query(ClassroomMembership.user_id, func.count(ClassroomMembership.id))
            .filter(ClassroomMembership.user_id.in_(student_ids))
            .group_by(ClassroomMembership.user_id)
            .all()
        )
        attempt_counts = _count_by(
            db.query(ExamAttempt.user_id, func.count(ExamAttempt.id))
            .filter(ExamAttempt.user_id.in_(student_ids))
            .group_by(ExamAttempt.user_id)
            .all()
        )
        average_scores = {
            user_id: round(float(value), 1) if value is not None else None
            for user_id, value in (
                db.query(
                    ExamAttempt.user_id,
                    func.avg((ExamAttempt.score * 100.0) / func.nullif(ExamAttempt.total_points, 0)),
                )
                .filter(
                    ExamAttempt.user_id.in_(student_ids),
                    ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED,
                    ExamAttempt.total_points > 0,
                )
                .group_by(ExamAttempt.user_id)
                .all()
            )
        }

    current_month_students = int(
        db.query(func.count(User.id))
        .filter(
            User.role.has(Role.name == STUDENT_ROLE_NAME),
            User.status != "deleted",
            User.created_at >= month_start,
        )
        .scalar()
        or 0
    )
    previous_month_students = int(
        db.query(func.count(User.id))
        .filter(
            User.role.has(Role.name == STUDENT_ROLE_NAME),
            User.status != "deleted",
            User.created_at >= previous_month_start,
            User.created_at < month_start,
        )
        .scalar()
        or 0
    )
    active_students = 0
    disabled_students = sum(1 for student in students if student.status == "disabled")
    total_student_sparkline = _build_cumulative_monthly_counts(
        db,
        User,
        User.created_at,
        sparkline_months,
        User.role.has(Role.name == STUDENT_ROLE_NAME),
        User.status != "deleted",
    )
    new_student_sparkline = _build_monthly_counts(
        db,
        User,
        User.created_at,
        sparkline_months,
        User.role.has(Role.name == STUDENT_ROLE_NAME),
        User.status != "deleted",
    )
    active_student_sparkline = [0 for _ in sparkline_months]
    disabled_student_sparkline = _build_cumulative_monthly_counts(
        db,
        User,
        User.created_at,
        sparkline_months,
        User.role.has(Role.name == STUDENT_ROLE_NAME),
        User.status == "disabled",
    )

    active_session_user_ids = _recent_activity_user_ids(db, student_ids)
    active_students = len(active_session_user_ids)
    active_student_sparkline = [active_students for _ in sparkline_months]

    return {
        "metrics": [
            _metric("total_students", "Tổng học sinh", len(students), trend=_format_percent_trend(current_month_students, previous_month_students), is_up=current_month_students >= previous_month_students, subtext="so với tháng trước", sparkline=total_student_sparkline),
            _metric("new_students", "Học sinh mới", current_month_students, subtext="trong tháng này", sparkline=new_student_sparkline),
            _metric("active_students", "Đang hoạt động", active_students, subtext="có tương tác trong 1 giờ qua", sparkline=active_student_sparkline),
            _metric("disabled_students", "Bị khóa", disabled_students, trend=_format_number_trend(disabled_students, 0), is_up=False, subtext="không thể đăng nhập", sparkline=disabled_student_sparkline),
        ],
        "items": [
            {
                "id": student.id,
                "code": f"STU-{student.id:05d}",
                "full_name": student.full_name,
                "username": student.username,
                "email": student.email,
                "phone": student.phone,
                "avatar_url": student.avatar_url,
                "status": student.status,
                "is_online": student.id in active_session_user_ids,
                "school_name": student.profile.school_name if student.profile else None,
                "date_of_birth": student.profile.date_of_birth if student.profile else None,
                "gender": student.profile.gender if student.profile else None,
                "class_count": class_counts.get(student.id, 0),
                "attempt_count": attempt_counts.get(student.id, 0),
                "average_score": average_scores.get(student.id),
                "last_login_at": student.last_login_at,
                "created_at": student.created_at,
            }
            for student in students
        ],
    }


def get_admin_classes_overview(db: Session) -> dict:
    classrooms = (
        db.query(Classroom)
        .order_by(Classroom.created_at.desc(), Classroom.id.desc())
        .all()
    )
    classroom_ids = [classroom.id for classroom in classrooms]
    teacher_ids = [classroom.created_by_user_id for classroom in classrooms if classroom.created_by_user_id]

    teachers = {}
    if teacher_ids:
        teachers = {
            teacher.id: teacher
            for teacher in db.query(User).filter(User.id.in_(teacher_ids)).all()
        }

    student_counts: dict[int, int] = {}
    exam_counts: dict[int, int] = {}
    document_counts: dict[int, int] = {}
    if classroom_ids:
        student_counts = _count_by(
            db.query(ClassroomMembership.classroom_id, func.count(ClassroomMembership.id))
            .join(User, User.id == ClassroomMembership.user_id)
            .filter(
                ClassroomMembership.classroom_id.in_(classroom_ids),
                User.role.has(Role.name == STUDENT_ROLE_NAME),
            )
            .group_by(ClassroomMembership.classroom_id)
            .all()
        )
        exam_counts = _count_by(
            db.query(Exam.classroom_id, func.count(Exam.id))
            .filter(Exam.classroom_id.in_(classroom_ids))
            .group_by(Exam.classroom_id)
            .all()
        )
        document_counts = _count_by(
            db.query(LearningDocument.classroom_id, func.count(LearningDocument.id))
            .filter(LearningDocument.classroom_id.in_(classroom_ids))
            .group_by(LearningDocument.classroom_id)
            .all()
        )

    return {
        "metrics": [
            _metric("total_classes", "Tổng lớp học", len(classrooms), subtext="tất cả lớp trên hệ thống"),
            _metric("active_classes", "Đang hoạt động", len(classrooms), subtext="lớp có thể tham gia"),
            _metric("total_students", "Lượt học sinh", sum(student_counts.values()), subtext="theo thành viên lớp"),
            _metric("class_exams", "Bài thi trong lớp", sum(exam_counts.values()), subtext="bài thi thuộc lớp"),
        ],
        "items": [
            {
                "id": classroom.id,
                "name": classroom.name,
                "description": classroom.description,
                "join_code": classroom.join_code,
                "teacher_id": classroom.created_by_user_id,
                "teacher_name": teachers[classroom.created_by_user_id].full_name if classroom.created_by_user_id in teachers else None,
                "teacher_avatar_url": teachers[classroom.created_by_user_id].avatar_url if classroom.created_by_user_id in teachers else None,
                "student_count": student_counts.get(classroom.id, 0),
                "exam_count": exam_counts.get(classroom.id, 0),
                "document_count": document_counts.get(classroom.id, 0),
                "status": "active",
                "created_at": classroom.created_at,
                "updated_at": classroom.updated_at,
            }
            for classroom in classrooms
        ],
    }


def get_admin_exams_overview(db: Session, limit: int = 50, offset: int = 0) -> dict:
    total = int(db.query(func.count(Exam.id)).scalar() or 0)
    active_exam_count = int(
        db.query(func.count(Exam.id))
        .filter(Exam.is_published.is_(True), Exam.is_active.is_(True))
        .scalar()
        or 0
    )

    rows = (
        db.query(
            Exam.id,
            Exam.created_by_user_id,
            Exam.title,
            Exam.description,
            Exam.grade,
            Exam.scope,
            Exam.classroom_id,
            Exam.duration_minutes,
            Exam.start_time,
            Exam.end_time,
            Exam.total_points,
            Exam.is_published,
            Exam.is_active,
            Exam.created_at,
            Exam.updated_at,
            User.full_name.label("teacher_name"),
            Role.name.label("creator_role_name"),
            Classroom.name.label("classroom_name"),
        )
        .outerjoin(User, User.id == Exam.created_by_user_id)
        .outerjoin(Role, Role.id == User.role_id)
        .outerjoin(Classroom, Classroom.id == Exam.classroom_id)
        .order_by(Exam.created_at.desc(), Exam.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    row_ids = [row.id for row in rows]
    ai_generated_exam_ids = get_ai_generated_exam_ids(db, row_ids)
    question_counts = (
        _count_by(
            db.query(ExamQuestion.exam_id, func.count(ExamQuestion.id))
            .filter(ExamQuestion.exam_id.in_(row_ids))
            .group_by(ExamQuestion.exam_id)
            .all()
        )
        if row_ids
        else {}
    )
    attempt_counts = (
        _count_by(
            db.query(ExamAttempt.exam_id, func.count(ExamAttempt.id))
            .filter(ExamAttempt.exam_id.in_(row_ids))
            .group_by(ExamAttempt.exam_id)
            .all()
        )
        if row_ids
        else {}
    )
    average_scores = {
        exam_id: round(float(value), 1) if value is not None else None
        for exam_id, value in (
            db.query(
                ExamAttempt.exam_id,
                func.avg((ExamAttempt.score * 100.0) / func.nullif(ExamAttempt.total_points, 0)),
            )
            .filter(
                ExamAttempt.exam_id.in_(row_ids),
                ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED,
                ExamAttempt.total_points > 0,
            )
            .group_by(ExamAttempt.exam_id)
            .all()
            if row_ids
            else []
        )
    }

    total_submitted = int(
        db.query(func.count(ExamAttempt.id))
        .filter(ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED)
        .scalar()
        or 0
    )
    completed_average = (
        db.query(func.avg((ExamAttempt.score * 100.0) / func.nullif(ExamAttempt.total_points, 0)))
        .filter(ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED, ExamAttempt.total_points > 0)
        .scalar()
    )
    completed_average_value = round(float(completed_average), 1) if completed_average is not None else 0.0

    return {
        "metrics": [
            _metric("average_score", "Điểm trung bình", completed_average_value, suffix="%", subtext="trên bài đã nộp"),
            _metric("submitted_attempts", "Lượt hoàn thành", total_submitted, subtext="bài làm đã nộp"),
            _metric("active_exams", "Bài thi đang mở", active_exam_count, subtext="đã xuất bản và đang mở"),
        ],
        "items": [
            {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "grade": _serialize_exam_grade(row.grade),
                "scope": row.scope,
                "classroom_id": row.classroom_id,
                "classroom_name": row.classroom_name,
                "teacher_id": row.created_by_user_id,
                "teacher_name": row.teacher_name,
                **build_exam_creator_metadata(
                    creator_id=row.created_by_user_id,
                    creator_name=row.teacher_name,
                    creator_role_name=row.creator_role_name,
                    is_ai_generated=row.id in ai_generated_exam_ids,
                ),
                "duration_minutes": row.duration_minutes,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "total_points": row.total_points,
                "question_count": question_counts.get(row.id, 0),
                "attempt_count": attempt_counts.get(row.id, 0),
                "average_score": average_scores.get(row.id),
                "is_published": row.is_published,
                "is_active": row.is_active,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def create_admin_exam(
    db: Session,
    current_admin: User,
    title: str,
    description: str | None,
    grade: str | None,
    image_url: str | None,
    scope: str,
    classroom_id: int | None,
    duration_minutes: int,
    start_time: datetime | None,
    end_time: datetime | None,
    is_published: bool,
    is_active: bool,
    questions: list[dict],
) -> dict:
    normalized_title = title.strip()
    if not normalized_title:
        raise HTTPException(status_code=400, detail="title is required")

    normalized_scope = (scope or SCOPE_SYSTEM).strip().lower()
    if normalized_scope not in {SCOPE_SYSTEM, SCOPE_CLASS}:
        raise HTTPException(status_code=400, detail="scope must be system or class")

    classroom = None
    if normalized_scope == SCOPE_CLASS:
        if classroom_id is None:
            raise HTTPException(status_code=400, detail="classroom_id is required for class exam")
        classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")

    normalized_start_time, normalized_end_time = _validate_exam_schedule(start_time, end_time)
    normalized_questions = _validate_exam_questions(questions)

    exam = Exam(
        created_by_user_id=current_admin.id,
        title=normalized_title,
        description=description.strip() if description else None,
        grade=_normalize_exam_grade(grade),
        image_url=image_url.strip() if image_url else None,
        scope=normalized_scope,
        classroom_id=classroom.id if classroom else None,
        duration_minutes=duration_minutes,
        start_time=normalized_start_time,
        end_time=normalized_end_time,
        total_points=0.0,
        is_published=is_published,
        is_active=is_active,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(exam)
    exam.total_points = _replace_exam_questions(exam, normalized_questions)
    db.commit()

    created_exam = (
        db.query(Exam)
        .options(joinedload(Exam.classroom))
        .options(joinedload(Exam.created_by).joinedload(User.role))
        .options(joinedload(Exam.questions).joinedload(ExamQuestion.options))
        .options(joinedload(Exam.attempts))
        .filter(Exam.id == exam.id)
        .first()
    )
    return {
        "message": "Exam created successfully",
        "exam": _serialize_exam_detail(created_exam or exam, is_ai_generated=False),
    }


def delete_admin_exam(
    db: Session,
    current_administrator: User,
    exam_id: int,
) -> dict:
    _ = current_administrator
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    _delete_exams_where(db, "id = :exam_id", {"exam_id": exam_id})
    db.commit()
    return {"message": "Exam deleted successfully"}


def get_admin_documents_overview(db: Session) -> dict:
    rows = (
        db.query(
            LearningDocument.id,
            LearningDocument.title,
            LearningDocument.summary,
            LearningDocument.content,
            LearningDocument.file_url,
            LearningDocument.file_name,
            LearningDocument.file_content_type,
            LearningDocument.file_size_bytes,
            LearningDocument.scope,
            LearningDocument.classroom_id,
            LearningDocument.created_by_user_id,
            LearningDocument.is_published,
            LearningDocument.created_at,
            LearningDocument.updated_at,
            User.full_name.label("teacher_name"),
            Classroom.name.label("classroom_name"),
        )
        .outerjoin(User, User.id == LearningDocument.created_by_user_id)
        .outerjoin(Classroom, Classroom.id == LearningDocument.classroom_id)
        .order_by(LearningDocument.created_at.desc(), LearningDocument.id.desc())
        .all()
    )

    published_count = sum(1 for row in rows if row.is_published)
    class_count = sum(1 for row in rows if row.scope == "class")
    system_count = sum(1 for row in rows if row.scope == "system")

    return {
        "metrics": [
            _metric("total_documents", "Tổng tài liệu", len(rows), subtext="tất cả tài liệu"),
            _metric("published_documents", "Đã xuất bản", published_count, subtext="học sinh có thể xem"),
            _metric("class_documents", "Tài liệu lớp", class_count, subtext="gắn với lớp học"),
            _metric("system_documents", "Tài liệu hệ thống", system_count, subtext="phạm vi hệ thống"),
        ],
        "items": [
            {
                "id": row.id,
                "title": row.title,
                "summary": row.summary,
                "content_preview": (row.summary or row.content or row.file_name or "")[:160],
                "file_url": row.file_url,
                "file_name": row.file_name,
                "file_content_type": row.file_content_type,
                "file_size_bytes": row.file_size_bytes,
                "scope": row.scope,
                "classroom_id": row.classroom_id,
                "classroom_name": row.classroom_name,
                "teacher_id": row.created_by_user_id,
                "teacher_name": row.teacher_name,
                "is_published": row.is_published,
                "content_length": len(row.content or ""),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }


def _admin_uploaded_document_title(title: str | None, filename: str | None) -> str:
    normalized_title = (title or "").strip()
    if normalized_title:
        return normalized_title

    filename_stem = Path(filename or "").stem.strip()
    if filename_stem:
        return filename_stem

    return "Untitled document"


def _validate_admin_document_scope(
    db: Session,
    scope: str,
    classroom_id: int | None,
) -> tuple[str, Classroom | None]:
    normalized_scope = scope.strip().lower()
    if normalized_scope not in {"system", "class"}:
        raise HTTPException(status_code=400, detail="scope must be system or class")

    if normalized_scope == "system":
        if classroom_id is not None:
            raise HTTPException(status_code=400, detail="classroom_id is not allowed for system scope")
        return normalized_scope, None

    if classroom_id is None:
        raise HTTPException(status_code=400, detail="classroom_id is required for class scope")

    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Classroom not found")

    return normalized_scope, classroom


def create_admin_uploaded_document(
    db: Session,
    current_admin: User,
    title: str | None,
    summary: str | None,
    upload: UploadFile,
    scope: str,
    classroom_id: int | None,
    is_published: bool,
) -> dict:
    normalized_scope, classroom = _validate_admin_document_scope(db, scope, classroom_id)
    file_data = upload_document_file(upload)
    normalized_title = _admin_uploaded_document_title(title, file_data["filename"])
    now = utc_now()

    document = LearningDocument(
        title=normalized_title,
        summary=summary.strip() if summary and summary.strip() else None,
        content="",
        file_url=file_data["url"],
        file_name=file_data["filename"],
        file_content_type=file_data["content_type"],
        file_size_bytes=file_data["size_bytes"],
        file_public_id=file_data["public_id"],
        scope=normalized_scope,
        classroom_id=classroom.id if classroom else None,
        created_by_user_id=current_admin.id,
        is_published=is_published,
        created_at=now,
        updated_at=now,
    )

    try:
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        delete_document_file(file_data.get("public_id"))
        raise

    db.refresh(document)
    return {
        "message": "Document uploaded successfully",
        "document": {
            "id": document.id,
            "title": document.title,
            "summary": document.summary,
            "content_preview": (document.summary or document.content or document.file_name or "")[:160],
            "file_url": document.file_url,
            "file_name": document.file_name,
            "file_content_type": document.file_content_type,
            "file_size_bytes": document.file_size_bytes,
            "scope": document.scope,
            "classroom_id": document.classroom_id,
            "classroom_name": classroom.name if classroom else None,
            "teacher_id": document.created_by_user_id,
            "teacher_name": current_admin.full_name,
            "is_published": document.is_published,
            "content_length": len(document.content or ""),
            "created_at": document.created_at,
            "updated_at": document.updated_at,
        },
    }


def _serialize_admin_account(user: User, active_user_ids: set[int] | None = None) -> dict:
    role_name = user.role.name if user.role else ADMIN_ROLE_NAME
    return {
        "id": user.id,
        "full_name": user.full_name,
        "username": user.username,
        "email": user.email,
        "role_name": role_name,
        "status": user.status,
        "is_online": user.status == "active" and bool(active_user_ids and user.id in active_user_ids),
        "admin_permissions": normalize_admin_permissions(user.admin_permissions),
        "email_verified": user.email_verified,
        "auth_type": user.auth_type,
        "avatar_url": user.avatar_url,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def _admin_role_name(user: User) -> str | None:
    return user.role.name if user.role else None


def _admin_permission_set(user: User) -> set[str]:
    role_name = _admin_role_name(user)
    if role_name == ADMINISTRATOR_ROLE_NAME:
        return set(ADMIN_PERMISSION_KEYS)
    if role_name != ADMIN_ROLE_NAME:
        return set()
    return set(normalize_admin_permissions(user.admin_permissions))


def _require_admin_scope(current_admin: User, permission: str) -> None:
    if _admin_role_name(current_admin) == ADMINISTRATOR_ROLE_NAME:
        return
    if permission not in _admin_permission_set(current_admin):
        raise HTTPException(status_code=403, detail="Administrator permission is required")


def _filter_visible_admin_accounts(users: list[User], current_admin: User) -> list[User]:
    if _admin_role_name(current_admin) == ADMINISTRATOR_ROLE_NAME:
        return users

    current_permissions = _admin_permission_set(current_admin)
    if not current_permissions:
        return []

    visible_users: list[User] = []
    for user in users:
        if user.id == current_admin.id:
            visible_users.append(user)
            continue

        if _admin_role_name(user) != ADMIN_ROLE_NAME:
            continue

        if current_permissions.intersection(_admin_permission_set(user)):
            visible_users.append(user)

    return visible_users


def _get_admin_account(db: Session, user_id: int) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_id, User.role.has(Role.name.in_(ADMIN_ACCESS_ROLE_NAMES)))
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Admin account not found")
    return user


def _require_editable_admin(target_user: User, current_administrator: User) -> None:
    if target_user.id == current_administrator.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own administrator account here")

    target_role_name = target_user.role.name if target_user.role else None
    if target_role_name == ADMINISTRATOR_ROLE_NAME:
        raise HTTPException(status_code=400, detail="Administrator account cannot be modified here")


def _table_exists(db: Session, table_name: str) -> bool:
    return bool(db.execute(text("select to_regclass(:table_name)"), {"table_name": table_name}).scalar())


def _column_exists(db: Session, table_name: str, column_name: str) -> bool:
    return bool(
        db.execute(
            text(
                """
                select 1
                from information_schema.columns
                where table_schema = 'public'
                  and table_name = :table_name
                  and column_name = :column_name
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).first()
    )


def _execute_if_table(db: Session, table_name: str, statement: str, params: dict) -> None:
    if _table_exists(db, table_name):
        db.execute(text(statement), params)


def _delete_exams_where(db: Session, where_sql: str, params: dict) -> None:
    if not _table_exists(db, "exams"):
        return

    exam_ids_sql = f"select id from exams where {where_sql}"
    if _table_exists(db, "ai_exam_generation_jobs") and _column_exists(
        db,
        "ai_exam_generation_jobs",
        "quiz_id",
    ):
        db.execute(
            text(
                f"""
                update ai_exam_generation_jobs
                set quiz_id = null,
                    status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                where quiz_id in ({exam_ids_sql})
                """
            ),
            params,
        )
    if _table_exists(db, "exam_attempt_answers") and _table_exists(db, "exam_attempts"):
        db.execute(
            text(
                f"""
                delete from exam_attempt_answers
                where attempt_id in (
                    select id from exam_attempts
                    where exam_id in ({exam_ids_sql})
                )
                """
            ),
            params,
        )
    if _table_exists(db, "exam_attempts"):
        db.execute(text(f"delete from exam_attempts where exam_id in ({exam_ids_sql})"), params)
    if _table_exists(db, "exam_question_options") and _table_exists(db, "exam_questions"):
        db.execute(
            text(
                f"""
                delete from exam_question_options
                where question_id in (
                    select id from exam_questions
                    where exam_id in ({exam_ids_sql})
                )
                """
            ),
            params,
        )
    if _table_exists(db, "exam_questions"):
        db.execute(text(f"delete from exam_questions where exam_id in ({exam_ids_sql})"), params)
    db.execute(text(f"delete from exams where {where_sql}"), params)


def _delete_chat_user_references(db: Session, user_id: int) -> None:
    if not _table_exists(db, "chat_conversations"):
        return

    params = {"user_id": user_id}
    if _table_exists(db, "chat_participants") and _table_exists(db, "chat_messages"):
        db.execute(
            text(
                """
                update chat_participants
                set last_read_message_id = null
                where last_read_message_id in (
                    select id from chat_messages where sender_id = :user_id
                )
                """
            ),
            params,
        )
        db.execute(
            text(
                """
                update chat_participants
                set last_read_message_id = null
                where conversation_id in (
                    select id from chat_conversations where created_by_user_id = :user_id
                )
                """
            ),
            params,
        )
        db.execute(
            text(
                """
                delete from chat_participants
                where conversation_id in (
                    select id from chat_conversations where created_by_user_id = :user_id
                )
                """
            ),
            params,
        )
        db.execute(text("delete from chat_participants where user_id = :user_id"), params)

    if _table_exists(db, "chat_messages"):
        db.execute(
            text(
                """
                delete from chat_messages
                where conversation_id in (
                    select id from chat_conversations where created_by_user_id = :user_id
                )
                """
            ),
            params,
        )
        db.execute(text("delete from chat_messages where sender_id = :user_id"), params)

    db.execute(text("delete from chat_conversations where created_by_user_id = :user_id"), params)


def _delete_user_auth_rows(db: Session, user_id: int) -> None:
    params = {"user_id": user_id}
    for table_name in (
        "user_sessions",
        "oauth_accounts",
        "email_verification_otps",
        "email_verification_tokens",
        "password_setup_tokens",
        "password_reset_tokens",
        "user_profiles",
    ):
        if _table_exists(db, table_name) and _column_exists(db, table_name, "user_id"):
            db.execute(text(f"delete from {table_name} where user_id = :user_id"), params)


def _delete_teacher_owned_rows(db: Session, teacher_id: int) -> None:
    params = {"user_id": teacher_id}
    if _table_exists(db, "contact_infos") and _column_exists(db, "contact_infos", "updated_by"):
        db.execute(text("update contact_infos set updated_by = null where updated_by = :user_id"), params)

    if _table_exists(db, "learning_documents"):
        if _column_exists(db, "learning_documents", "created_by_user_id"):
            db.execute(text("delete from learning_documents where created_by_user_id = :user_id"), params)
        if _table_exists(db, "classrooms") and _column_exists(db, "learning_documents", "classroom_id"):
            db.execute(
                text(
                    """
                    delete from learning_documents
                    where classroom_id in (
                        select id from classrooms where created_by_user_id = :user_id
                    )
                    """
                ),
                params,
            )

    if _table_exists(db, "documents"):
        if _column_exists(db, "documents", "created_by"):
            db.execute(text("delete from documents where created_by = :user_id"), params)
        if _table_exists(db, "classes") and _column_exists(db, "documents", "class_id"):
            db.execute(
                text(
                    """
                    delete from documents
                    where class_id in (
                        select id from classes where teacher_id = :user_id
                    )
                    """
                ),
                params,
            )

    if _column_exists(db, "exams", "created_by"):
        _delete_exams_where(db, "created_by = :user_id", params)
    if _column_exists(db, "exams", "classroom_id") and _table_exists(db, "classrooms"):
        _delete_exams_where(
            db,
            "classroom_id in (select id from classrooms where created_by_user_id = :user_id)",
            params,
        )
    if _column_exists(db, "exams", "class_id") and _table_exists(db, "classes"):
        _delete_exams_where(
            db,
            "class_id in (select id from classes where teacher_id = :user_id)",
            params,
        )

    if _table_exists(db, "classroom_memberships") and _table_exists(db, "classrooms"):
        db.execute(
            text(
                """
                delete from classroom_memberships
                where classroom_id in (
                    select id from classrooms where created_by_user_id = :user_id
                )
                """
            ),
            params,
        )
    if _table_exists(db, "class_members") and _table_exists(db, "classes"):
        db.execute(
            text(
                """
                delete from class_members
                where class_id in (
                    select id from classes where teacher_id = :user_id
                )
                """
            ),
            params,
        )
    if _table_exists(db, "classrooms"):
        db.execute(text("delete from classrooms where created_by_user_id = :user_id"), params)
    if _table_exists(db, "classes"):
        db.execute(text("delete from classes where teacher_id = :user_id"), params)


def _delete_student_owned_rows(db: Session, student_id: int) -> None:
    params = {"user_id": student_id}
    if _table_exists(db, "exam_attempts"):
        attempt_filters = []
        if _column_exists(db, "exam_attempts", "user_id"):
            attempt_filters.append("user_id = :user_id")
        if _column_exists(db, "exam_attempts", "student_id"):
            attempt_filters.append("student_id = :user_id")
        if attempt_filters:
            where_sql = " or ".join(attempt_filters)
            if _table_exists(db, "exam_attempt_answers"):
                db.execute(
                    text(
                        f"""
                        delete from exam_attempt_answers
                        where attempt_id in (
                            select id from exam_attempts where {where_sql}
                        )
                        """
                    ),
                    params,
                )
            db.execute(text(f"delete from exam_attempts where {where_sql}"), params)

    if _table_exists(db, "classroom_memberships") and _column_exists(db, "classroom_memberships", "user_id"):
        db.execute(text("delete from classroom_memberships where user_id = :user_id"), params)
    if _table_exists(db, "class_members") and _column_exists(db, "class_members", "student_id"):
        db.execute(text("delete from class_members where student_id = :user_id"), params)


def _hard_delete_user(db: Session, user_id: int, role_name: str | None = None) -> None:
    _delete_chat_user_references(db, user_id)
    if role_name == TEACHER_ROLE_NAME:
        _delete_teacher_owned_rows(db, user_id)
    elif role_name == STUDENT_ROLE_NAME:
        _delete_student_owned_rows(db, user_id)
    else:
        if _table_exists(db, "contact_infos") and _column_exists(db, "contact_infos", "updated_by"):
            db.execute(
                text("update contact_infos set updated_by = null where updated_by = :user_id"),
                {"user_id": user_id},
            )

    _delete_user_auth_rows(db, user_id)
    db.execute(text("delete from users where id = :user_id"), {"user_id": user_id})


def _normalize_invitation_email(email: str) -> str:
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    return normalized_email


def _parse_admin_invitation_date_of_birth(value: date | str | None) -> date | None:
    if isinstance(value, date):
        return value

    normalized_value = value.strip() if value else ""
    if not normalized_value:
        return None

    try:
        parsed_value = date.fromisoformat(normalized_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date_of_birth is invalid") from exc

    if parsed_value > utc_now().date():
        raise HTTPException(status_code=400, detail="date_of_birth cannot be in the future")

    return parsed_value


def _normalize_admin_invitation_gender(value: str | None) -> str:
    normalized_value = value.strip().lower() if value else ""
    if normalized_value not in {"male", "female", "other"}:
        raise HTTPException(status_code=400, detail="gender is required")
    return normalized_value


def _hash_admin_invitation_token(token: str) -> str:
    raw_value = f"{settings.EMAIL_VERIFICATION_SECRET}:admin-invitation:{token}"
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def _generate_admin_invitation_otp() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def _build_admin_invitation_url(token: str, email: str) -> str:
    query_string = urlencode({"token": token, "email": email})
    return f"{settings.ADMIN_INVITATION_BASE_URL}{settings.FRONTEND_ADMIN_INVITATION_PATH}?{query_string}"


def _is_admin_invitation_expired(invitation: AdminInvitation) -> bool:
    if invitation.otp_attempt_count < 0:
        return False
    expires_at = _normalize_datetime(invitation.otp_expires_at)
    return bool(expires_at and expires_at <= utc_now())


def _expire_admin_invitation_if_needed(invitation: AdminInvitation) -> bool:
    if invitation.status == "otp_pending" and _is_admin_invitation_expired(invitation):
        invitation.status = "expired"
        invitation.updated_at = utc_now()
        return True
    return False


def _serialize_admin_invitation(
    invitation: AdminInvitation,
    users_by_id: dict[int, User] | None = None,
) -> dict:
    status_value = invitation.status
    if status_value == "otp_pending" and _is_admin_invitation_expired(invitation):
        status_value = "expired"

    invited_by = (
        users_by_id.get(invitation.invited_by_user_id)
        if users_by_id and invitation.invited_by_user_id
        else None
    )

    return {
        "id": invitation.id,
        "email": invitation.email,
        "full_name": invitation.full_name,
        "phone": invitation.phone,
        "date_of_birth": invitation.date_of_birth,
        "gender": invitation.gender,
        "status": status_value,
        "otp_expires_at": invitation.otp_expires_at,
        "invited_by_user_id": invitation.invited_by_user_id,
        "invited_by_name": invited_by.full_name if invited_by else None,
        "invited_by_email": invited_by.email if invited_by else None,
        "submitted_at": invitation.submitted_at,
        "approved_by_user_id": invitation.approved_by_user_id,
        "approved_at": invitation.approved_at,
        "rejected_by_user_id": invitation.rejected_by_user_id,
        "rejected_at": invitation.rejected_at,
        "rejection_reason": invitation.rejection_reason,
        "generated_user_id": invitation.generated_user_id,
        "created_at": invitation.created_at,
        "updated_at": invitation.updated_at,
    }


def _send_admin_invitation_email(invitation: AdminInvitation, token: str) -> None:
    invitation_url = _build_admin_invitation_url(token, invitation.email)
    rendered = render_action_email(
        app_name=settings.EMAIL_FROM_NAME or settings.APP_NAME,
        recipient_name=invitation.full_name,
        recipient_email=invitation.email,
        subject=f"Mời xác thực tài khoản quản trị {settings.APP_NAME}",
        title="Mời xác thực tài khoản quản trị",
        intro_lines=[
            f"Bạn được mời gửi yêu cầu tài khoản quản trị cho {settings.APP_NAME}.",
            "Bấm nút bên dưới để điền thông tin và xác thực OTP.",
        ],
        button_label="Mở form xác thực",
        button_url=invitation_url,
        brand_logo_url=settings.EMAIL_BRAND_LOGO_URL,
    )
    send_email(invitation.email, rendered.subject, rendered.text_body, rendered.html_body)


def _send_admin_invitation_otp_email(invitation: AdminInvitation, otp_code: str) -> None:
    rendered = render_otp_email(
        app_name=settings.EMAIL_FROM_NAME or settings.APP_NAME,
        recipient_name=invitation.full_name,
        recipient_email=invitation.email,
        subject=f"Mã OTP quản trị {settings.APP_NAME}",
        title="Mã OTP quản trị",
        intro="Sử dụng mã OTP bên dưới để xác thực yêu cầu tài khoản quản trị.",
        otp_code=otp_code,
        expires_minutes=settings.ADMIN_INVITATION_OTP_EXPIRE_MINUTES,
        brand_logo_url=settings.EMAIL_BRAND_LOGO_URL,
    )
    send_email(invitation.email, rendered.subject, rendered.text_body, rendered.html_body)


def _send_admin_pending_review_email(db: Session, invitation: AdminInvitation) -> None:
    inviter = None
    if invitation.invited_by_user_id:
        inviter = db.query(User).filter(User.id == invitation.invited_by_user_id).first()

    if not inviter or not inviter.email:
        return

    rendered = render_notice_email(
        app_name=settings.EMAIL_FROM_NAME or settings.APP_NAME,
        recipient_name=inviter.full_name,
        recipient_email=inviter.email,
        subject=f"Yêu cầu quản trị chờ duyệt - {settings.APP_NAME}",
        title="Yêu cầu quản trị chờ duyệt",
        intro_lines=[
            f"{invitation.full_name or invitation.email} đã xác thực OTP và gửi yêu cầu tài khoản quản trị.",
            "Vui lòng mở dashboard Administrator để duyệt hoặc từ chối yêu cầu này.",
        ],
        details=[("Email", invitation.email)],
        brand_logo_url=settings.EMAIL_BRAND_LOGO_URL,
    )
    send_email(inviter.email, rendered.subject, rendered.text_body, rendered.html_body)


def _send_admin_password_setup_email(user: User, setup_url: str) -> None:
    rendered = render_action_email(
        app_name=settings.EMAIL_FROM_NAME or settings.APP_NAME,
        recipient_name=user.full_name,
        recipient_email=user.email,
        subject=f"Tài khoản quản trị {settings.APP_NAME} đã được duyệt",
        title="Tài khoản quản trị đã được duyệt",
        intro_lines=[
            f"Tài khoản quản trị của bạn trên {settings.APP_NAME} đã được Administrator phê duyệt.",
            "Bấm nút bên dưới để tạo mật khẩu đăng nhập. Liên kết chỉ sử dụng một lần.",
        ],
        button_label="Tạo mật khẩu quản trị",
        button_url=setup_url,
        expires_minutes=settings.ADMIN_PASSWORD_SETUP_EXPIRE_MINUTES,
        details=[("Email đăng nhập", user.email)],
        brand_logo_url=settings.EMAIL_BRAND_LOGO_URL,
    )
    send_email(user.email, rendered.subject, rendered.text_body, rendered.html_body)


def _admin_invitation_users_by_id(db: Session, invitations: list[AdminInvitation]) -> dict[int, User]:
    user_ids = {
        invitation.invited_by_user_id
        for invitation in invitations
        if invitation.invited_by_user_id
    }
    if not user_ids:
        return {}

    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return {user.id: user for user in users}


def _apply_admin_invitation_profile(db: Session, user: User, invitation: AdminInvitation) -> None:
    user.full_name = invitation.full_name or user.full_name or invitation.email
    user.phone = invitation.phone or user.phone

    if not invitation.date_of_birth or not invitation.gender:
        return

    profile = user.profile or db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile:
        profile.date_of_birth = invitation.date_of_birth
        profile.gender = invitation.gender
        profile.updated_at = utc_now()
        if not profile.onboarding_completed_at:
            profile.onboarding_completed_at = utc_now()
        return

    db.add(
        UserProfile(
            user_id=user.id,
            date_of_birth=invitation.date_of_birth,
            gender=invitation.gender,
            school_name=None,
            onboarding_completed_at=utc_now(),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
    )


def list_admin_invitations(
    db: Session,
    current_admin: User,
    status_filter: str | None = None,
) -> dict:
    _require_admin_scope(current_admin, "admins")

    if status_filter and status_filter not in ADMIN_INVITATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid invitation status")

    invitations = db.query(AdminInvitation).order_by(AdminInvitation.created_at.desc(), AdminInvitation.id.desc()).all()
    did_expire = False
    for invitation in invitations:
        did_expire = _expire_admin_invitation_if_needed(invitation) or did_expire

    if did_expire:
        db.commit()
        invitations = db.query(AdminInvitation).order_by(AdminInvitation.created_at.desc(), AdminInvitation.id.desc()).all()

    users_by_id = _admin_invitation_users_by_id(db, invitations)
    serialized_items = [
        _serialize_admin_invitation(invitation, users_by_id)
        for invitation in invitations
    ]
    if status_filter:
        serialized_items = [item for item in serialized_items if item["status"] == status_filter]

    return {"items": serialized_items}


def create_admin_invitation(
    db: Session,
    current_administrator: User,
    email: str,
) -> dict:
    _require_admin_scope(current_administrator, "admins")
    normalized_email = _normalize_invitation_email(email)

    existing_user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.email == normalized_email)
        .first()
    )
    if existing_user and _admin_role_name(existing_user) in ADMIN_ACCESS_ROLE_NAMES:
        raise HTTPException(status_code=409, detail="Email already has admin access")

    token = secrets.token_urlsafe(32)
    placeholder_otp_hash = hash_password(secrets.token_urlsafe(16))
    expires_at = utc_now() + timedelta(hours=settings.ADMIN_INVITATION_LINK_EXPIRE_HOURS)

    invitation = (
        db.query(AdminInvitation)
        .filter(
            AdminInvitation.email == normalized_email,
            AdminInvitation.status.in_(tuple(ADMIN_INVITATION_PENDING_STATUSES)),
        )
        .order_by(AdminInvitation.created_at.desc(), AdminInvitation.id.desc())
        .first()
    )
    if invitation:
        invitation.status = "otp_pending"
        invitation.full_name = existing_user.full_name if existing_user else None
        invitation.phone = existing_user.phone if existing_user else None
        invitation.date_of_birth = existing_user.profile.date_of_birth if existing_user and existing_user.profile else None
        invitation.gender = existing_user.profile.gender if existing_user and existing_user.profile else None
        invitation.invite_token_hash = _hash_admin_invitation_token(token)
        invitation.otp_hash = placeholder_otp_hash
        invitation.otp_expires_at = expires_at
        invitation.otp_attempt_count = -1
        invitation.invited_by_user_id = current_administrator.id
        invitation.submitted_at = None
        invitation.rejected_by_user_id = None
        invitation.rejected_at = None
        invitation.rejection_reason = None
        invitation.updated_at = utc_now()
    else:
        invitation = AdminInvitation(
            email=normalized_email,
            full_name=existing_user.full_name if existing_user else None,
            phone=existing_user.phone if existing_user else None,
            date_of_birth=existing_user.profile.date_of_birth if existing_user and existing_user.profile else None,
            gender=existing_user.profile.gender if existing_user and existing_user.profile else None,
            status="otp_pending",
            invite_token_hash=_hash_admin_invitation_token(token),
            otp_hash=placeholder_otp_hash,
            otp_expires_at=expires_at,
            otp_attempt_count=-1,
            invited_by_user_id=current_administrator.id,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(invitation)

    db.commit()
    db.refresh(invitation)

    try:
        _send_admin_invitation_email(invitation, token)
    except Exception as exc:
        logger.exception("Failed to send admin invitation email to %s", invitation.email)
        raise HTTPException(status_code=502, detail="Failed to send admin invitation email") from exc

    return {
        "message": "Admin invitation sent successfully",
        "invitation": _serialize_admin_invitation(
            invitation,
            {current_administrator.id: current_administrator},
        ),
    }


def send_admin_invitation_otp(
    db: Session,
    token: str,
    email: str,
    full_name: str | None,
    phone: str | None = None,
    date_of_birth: date | str | None = None,
    gender: str | None = None,
) -> dict:
    normalized_email = _normalize_invitation_email(email)
    normalized_full_name = full_name.strip() if full_name else ""
    normalized_phone = phone.strip() if phone else ""
    normalized_date_of_birth = _parse_admin_invitation_date_of_birth(date_of_birth)
    normalized_gender = _normalize_admin_invitation_gender(gender)

    if not normalized_phone:
        raise HTTPException(status_code=400, detail="phone is required")
    if not normalized_date_of_birth:
        raise HTTPException(status_code=400, detail="date_of_birth is required")

    invitation = (
        db.query(AdminInvitation)
        .filter(
            AdminInvitation.email == normalized_email,
            AdminInvitation.invite_token_hash == _hash_admin_invitation_token(token),
        )
        .first()
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="Admin invitation not found")

    if invitation.status != "otp_pending":
        raise HTTPException(status_code=400, detail="Admin invitation is not waiting for OTP verification")

    if invitation.otp_attempt_count >= 0:
        otp_expires_at = _normalize_datetime(invitation.otp_expires_at)
        if otp_expires_at:
            last_sent_at = otp_expires_at - timedelta(minutes=settings.ADMIN_INVITATION_OTP_EXPIRE_MINUTES)
            resend_available_at = last_sent_at + ADMIN_INVITATION_OTP_RESEND_COOLDOWN
            remaining_seconds = int((resend_available_at - utc_now()).total_seconds())
            if remaining_seconds > 0:
                raise HTTPException(
                    status_code=429,
                    detail=f"Vui lòng chờ {remaining_seconds} giây trước khi gửi lại mã OTP.",
                )

    existing_user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.email == normalized_email)
        .first()
    )
    if existing_user and _admin_role_name(existing_user) in ADMIN_ACCESS_ROLE_NAMES:
        raise HTTPException(status_code=409, detail="Email already has admin access")

    if existing_user:
        normalized_full_name = normalized_full_name or existing_user.full_name
    elif not normalized_full_name:
        raise HTTPException(status_code=400, detail="full_name is required")

    otp_code = _generate_admin_invitation_otp()
    invitation.full_name = normalized_full_name
    invitation.phone = normalized_phone
    invitation.date_of_birth = normalized_date_of_birth
    invitation.gender = normalized_gender
    invitation.otp_hash = hash_password(otp_code)
    invitation.otp_expires_at = utc_now() + timedelta(minutes=settings.ADMIN_INVITATION_OTP_EXPIRE_MINUTES)
    invitation.otp_attempt_count = 0
    invitation.updated_at = utc_now()
    db.commit()
    db.refresh(invitation)

    try:
        _send_admin_invitation_otp_email(invitation, otp_code)
    except Exception as exc:
        logger.exception("Failed to send admin invitation OTP email to %s", invitation.email)
        raise HTTPException(status_code=502, detail="Failed to send admin invitation OTP email") from exc

    return {
        "message": "Admin invitation OTP sent successfully",
        "invitation": _serialize_admin_invitation(invitation),
    }


def submit_admin_invitation_otp(
    db: Session,
    token: str,
    email: str,
    otp_code: str,
    full_name: str | None,
    phone: str | None = None,
    date_of_birth: date | str | None = None,
    gender: str | None = None,
) -> dict:
    normalized_email = _normalize_invitation_email(email)
    normalized_full_name = full_name.strip() if full_name else ""
    normalized_phone = phone.strip() if phone else ""
    normalized_date_of_birth = _parse_admin_invitation_date_of_birth(date_of_birth)
    normalized_gender = _normalize_admin_invitation_gender(gender)
    normalized_otp_code = otp_code.strip()

    if not normalized_phone:
        raise HTTPException(status_code=400, detail="phone is required")
    if not normalized_date_of_birth:
        raise HTTPException(status_code=400, detail="date_of_birth is required")

    invitation = (
        db.query(AdminInvitation)
        .filter(
            AdminInvitation.email == normalized_email,
            AdminInvitation.invite_token_hash == _hash_admin_invitation_token(token),
        )
        .first()
    )
    if not invitation:
        raise HTTPException(status_code=404, detail="Admin invitation not found")

    if invitation.status != "otp_pending":
        raise HTTPException(status_code=400, detail="Admin invitation is not waiting for OTP verification")

    if invitation.otp_attempt_count < 0:
        raise HTTPException(status_code=400, detail="OTP code has not been sent yet")

    if _is_admin_invitation_expired(invitation):
        invitation.status = "expired"
        invitation.updated_at = utc_now()
        db.commit()
        raise HTTPException(status_code=400, detail="Admin invitation OTP expired")

    if invitation.otp_attempt_count >= settings.ADMIN_INVITATION_OTP_MAX_ATTEMPTS:
        invitation.status = "expired"
        invitation.updated_at = utc_now()
        db.commit()
        raise HTTPException(status_code=400, detail="Admin invitation OTP attempt limit exceeded")

    if not verify_password(normalized_otp_code, invitation.otp_hash):
        invitation.otp_attempt_count += 1
        if invitation.otp_attempt_count >= settings.ADMIN_INVITATION_OTP_MAX_ATTEMPTS:
            invitation.status = "expired"
        invitation.updated_at = utc_now()
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    existing_user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.email == normalized_email)
        .first()
    )
    if existing_user and _admin_role_name(existing_user) in ADMIN_ACCESS_ROLE_NAMES:
        raise HTTPException(status_code=409, detail="Email already has admin access")

    if existing_user:
        normalized_full_name = normalized_full_name or existing_user.full_name
    elif not normalized_full_name:
        raise HTTPException(status_code=400, detail="full_name is required")

    invitation.full_name = normalized_full_name
    invitation.phone = normalized_phone
    invitation.date_of_birth = normalized_date_of_birth
    invitation.gender = normalized_gender
    invitation.status = "pending_approval"
    invitation.submitted_at = utc_now()
    invitation.updated_at = utc_now()
    db.commit()
    db.refresh(invitation)

    try:
        _send_admin_pending_review_email(db, invitation)
    except Exception:
        logger.exception("Failed to send admin invitation pending review email for invitation_id=%s", invitation.id)

    return {
        "message": "Admin request submitted and waiting for approval",
        "invitation": _serialize_admin_invitation(invitation),
    }


def approve_admin_invitation(
    db: Session,
    current_administrator: User,
    invitation_id: int,
    permissions: list[str],
) -> dict:
    _require_admin_scope(current_administrator, "admins")
    invitation = db.query(AdminInvitation).filter(AdminInvitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Admin invitation not found")
    if invitation.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Admin invitation is not waiting for approval")

    admin_role = get_or_create_role(db, ADMIN_ROLE_NAME)
    existing_user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.email == invitation.email)
        .first()
    )
    if existing_user and _admin_role_name(existing_user) in ADMIN_ACCESS_ROLE_NAMES:
        raise HTTPException(status_code=409, detail="Email already has admin access")

    if existing_user:
        user = existing_user
        user.role_id = admin_role.id
        if user.auth_type == "oauth" and user.password_hash:
            user.auth_type = "mixed"
        elif not user.auth_type:
            user.auth_type = "local"
        user.email_verified = True
        user.status = "active"
        user.is_first_login = True
        user.max_exam_create = max(user.max_exam_create or 0, 50)
        user.max_document_create = max(user.max_document_create or 0, 50)
        user.admin_permissions = encode_admin_permissions(permissions)
        user.updated_at = utc_now()
        _apply_admin_invitation_profile(db, user, invitation)
    else:
        user = User(
            role_id=admin_role.id,
            full_name=invitation.full_name or invitation.email,
            username=build_username_from_email(db, invitation.email),
            email=invitation.email,
            phone=invitation.phone,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            auth_type="local",
            email_verified=True,
            status="active",
            is_first_login=True,
            max_exam_create=50,
            max_document_create=50,
            admin_permissions=encode_admin_permissions(permissions),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(user)
    db.flush()
    if not existing_user:
        _apply_admin_invitation_profile(db, user, invitation)
    _, password_setup_url = create_admin_password_setup_token(db, user)

    invitation.status = "approved"
    invitation.approved_by_user_id = current_administrator.id
    invitation.approved_at = utc_now()
    invitation.generated_user_id = user.id
    invitation.updated_at = utc_now()
    db.commit()
    db.refresh(user)
    db.refresh(invitation)
    user = _get_admin_account(db, user.id)

    message = "Admin invitation approved and password setup email sent successfully"
    try:
        _send_admin_password_setup_email(user, password_setup_url)
    except Exception:
        logger.exception("Failed to send admin password setup email for user_id=%s", user.id)
        message = "Admin invitation approved, but failed to send password setup email"

    return {
        "message": message,
        "invitation": _serialize_admin_invitation(invitation),
        "admin": _serialize_admin_account(user),
    }


def reject_admin_invitation(
    db: Session,
    current_administrator: User,
    invitation_id: int,
    reason: str | None,
) -> dict:
    _require_admin_scope(current_administrator, "admins")
    invitation = db.query(AdminInvitation).filter(AdminInvitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Admin invitation not found")
    if invitation.status not in {"otp_pending", "pending_approval", "expired"}:
        raise HTTPException(status_code=400, detail="Admin invitation cannot be rejected")

    invitation.status = "rejected"
    invitation.rejected_by_user_id = current_administrator.id
    invitation.rejected_at = utc_now()
    invitation.rejection_reason = reason.strip() if reason else None
    invitation.updated_at = utc_now()
    db.commit()
    db.refresh(invitation)
    return {
        "message": "Admin invitation rejected successfully",
        "invitation": _serialize_admin_invitation(invitation),
    }


def clear_admin_invitations(
    db: Session,
    current_administrator: User,
) -> dict:
    _require_admin_scope(current_administrator, "admins")
    deleted_count = (
        db.query(AdminInvitation)
        .filter(AdminInvitation.status != "pending_approval")
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"message": f"Cleared {deleted_count} admin invitation(s)"}


def list_admin_accounts(db: Session, current_admin: User) -> dict:
    _require_admin_scope(current_admin, "admins")

    users = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.role.has(Role.name.in_(ADMIN_ACCESS_ROLE_NAMES)))
        .order_by(User.role_id.asc(), User.created_at.desc(), User.id.desc())
        .all()
    )
    users = _filter_visible_admin_accounts(users, current_admin)
    admin_ids = [user.id for user in users]
    active_user_ids = _recent_activity_user_ids(db, admin_ids)
    return {"items": [_serialize_admin_account(user, active_user_ids) for user in users]}


def create_admin_account(
    db: Session,
    full_name: str,
    email: str,
    password: str,
) -> dict:
    normalized_full_name = full_name.strip()
    normalized_email = email.strip().lower()

    if not normalized_full_name:
        raise HTTPException(status_code=400, detail="full_name is required")
    if not normalized_email:
        raise HTTPException(status_code=400, detail="email is required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already exists")

    admin_role = get_or_create_role(db, ADMIN_ROLE_NAME)
    user = User(
        role_id=admin_role.id,
        full_name=normalized_full_name,
        username=build_username_from_email(db, normalized_email),
        email=normalized_email,
        password_hash=hash_password(password),
        auth_type="local",
        email_verified=True,
        status="active",
        is_first_login=False,
        max_exam_create=50,
        max_document_create=50,
        admin_permissions="[]",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user = _get_admin_account(db, user.id)
    return {
        "message": "Admin account created successfully",
        "admin": _serialize_admin_account(user),
    }


def delete_admin_account(
    db: Session,
    current_administrator: User,
    user_id: int,
) -> dict:
    user = _get_admin_account(db, user_id)
    _require_editable_admin(user, current_administrator)
    role_name = user.role.name if user.role else None
    _hard_delete_user(db, user.id, role_name)
    db.commit()
    return {"message": "Admin account deleted successfully"}


def send_admin_password_setup_link(
    db: Session,
    current_administrator: User,
    user_id: int,
) -> dict:
    _require_admin_scope(current_administrator, "admins")
    user = _get_admin_account(db, user_id)
    _require_editable_admin(user, current_administrator)
    if user.status != "active":
        raise HTTPException(status_code=400, detail="Admin account is disabled")

    _, password_setup_url = create_admin_password_setup_token(db, user)
    db.commit()

    try:
        _send_admin_password_setup_email(user, password_setup_url)
    except Exception as exc:
        logger.exception("Failed to resend admin password setup email for user_id=%s", user.id)
        raise HTTPException(
            status_code=502,
            detail="Failed to send admin password setup email",
        ) from exc

    return {"message": "Admin password setup email sent successfully"}


def update_admin_permissions(
    db: Session,
    current_administrator: User,
    user_id: int,
    permissions: list[str],
) -> dict:
    user = _get_admin_account(db, user_id)
    _require_editable_admin(user, current_administrator)
    user.admin_permissions = encode_admin_permissions(permissions)
    user.updated_at = utc_now()
    db.commit()
    db.refresh(user)
    user = _get_admin_account(db, user.id)
    return {
        "message": "Admin permissions updated successfully",
        "admin": _serialize_admin_account(user),
    }


def delete_admin_teacher(
    db: Session,
    current_administrator: User,
    teacher_id: int,
) -> dict:
    _ = current_administrator
    teacher = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(
            User.id == teacher_id,
            User.role.has(Role.name == TEACHER_ROLE_NAME),
        )
        .first()
    )
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    _hard_delete_user(db, teacher.id, TEACHER_ROLE_NAME)
    db.commit()
    return {"message": "Teacher deleted successfully"}


def delete_admin_student(
    db: Session,
    current_administrator: User,
    student_id: int,
) -> dict:
    _ = current_administrator
    student = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(
            User.id == student_id,
            User.role.has(Role.name == STUDENT_ROLE_NAME),
        )
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    _hard_delete_user(db, student.id, STUDENT_ROLE_NAME)
    db.commit()
    return {"message": "Student deleted successfully"}


def _get_managed_user(db: Session, user_id: int, role_name: str, label: str) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.role))
        .filter(
            User.id == user_id,
            User.role.has(Role.name == role_name),
            User.status != "deleted",
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return user


def _serialize_teacher_user(
    teacher: User,
    class_count: int,
    exam_count: int,
    document_count: int,
    is_online: bool,
) -> dict:
    return {
        "id": teacher.id,
        "code": f"TCH-{teacher.id:04d}",
        "full_name": teacher.full_name,
        "username": teacher.username,
        "email": teacher.email,
        "phone": teacher.phone,
        "avatar_url": teacher.avatar_url,
        "status": teacher.status,
        "is_online": is_online,
        "school_name": teacher.profile.school_name if teacher.profile else None,
        "date_of_birth": teacher.profile.date_of_birth if teacher.profile else None,
        "gender": teacher.profile.gender if teacher.profile else None,
        "class_count": class_count,
        "exam_count": exam_count,
        "document_count": document_count,
        "last_login_at": teacher.last_login_at,
        "created_at": teacher.created_at,
    }


def _serialize_student_user(
    student: User,
    class_count: int,
    attempt_count: int,
    average_score: float | None,
    is_online: bool,
) -> dict:
    return {
        "id": student.id,
        "code": f"STU-{student.id:05d}",
        "full_name": student.full_name,
        "username": student.username,
        "email": student.email,
        "phone": student.phone,
        "avatar_url": student.avatar_url,
        "status": student.status,
        "is_online": is_online,
        "school_name": student.profile.school_name if student.profile else None,
        "date_of_birth": student.profile.date_of_birth if student.profile else None,
        "gender": student.profile.gender if student.profile else None,
        "class_count": class_count,
        "attempt_count": attempt_count,
        "average_score": average_score,
        "last_login_at": student.last_login_at,
        "created_at": student.created_at,
    }


def _average_attempt_score(db: Session, student_id: int) -> float | None:
    value = (
        db.query(func.avg((ExamAttempt.score * 100.0) / func.nullif(ExamAttempt.total_points, 0)))
        .filter(
            ExamAttempt.user_id == student_id,
            ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED,
            ExamAttempt.total_points > 0,
        )
        .scalar()
    )
    return round(float(value), 1) if value is not None else None


def _exam_average_scores(db: Session, exam_ids: list[int]) -> dict[int, float | None]:
    if not exam_ids:
        return {}
    return {
        exam_id: round(float(value), 1) if value is not None else None
        for exam_id, value in (
            db.query(
                ExamAttempt.exam_id,
                func.avg((ExamAttempt.score * 100.0) / func.nullif(ExamAttempt.total_points, 0)),
            )
            .filter(
                ExamAttempt.exam_id.in_(exam_ids),
                ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED,
                ExamAttempt.total_points > 0,
            )
            .group_by(ExamAttempt.exam_id)
            .all()
        )
    }


def _apply_admin_user_profile_update(
    db: Session,
    user: User,
    full_name: str | None,
    email: str | None,
    phone: str | None,
    avatar_url: str | None,
    date_of_birth: date | None,
    gender: str | None,
    school_name: str | None,
    status: str | None,
) -> None:
    if full_name is not None:
        normalized_full_name = full_name.strip()
        if not normalized_full_name:
            raise HTTPException(status_code=400, detail="full_name is required")
        user.full_name = normalized_full_name

    if email is not None:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise HTTPException(status_code=400, detail="email is required")
        existing_user = (
            db.query(User.id)
            .filter(User.email == normalized_email, User.id != user.id)
            .first()
        )
        if existing_user:
            raise HTTPException(status_code=409, detail="Email already exists")
        user.email = normalized_email

    if phone is not None:
        user.phone = phone.strip() or None
    if avatar_url is not None:
        user.avatar_url = avatar_url.strip() or None
    if status is not None:
        if status not in ADMIN_MUTABLE_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        user.status = status

    should_update_profile = any(
        value is not None for value in (date_of_birth, gender, school_name)
    )
    if should_update_profile:
        if user.profile is None:
            user.profile = UserProfile(
                user_id=user.id,
                date_of_birth=date_of_birth or date(1970, 1, 1),
                gender=(gender or "other").strip() or "other",
                school_name=school_name.strip() if school_name else None,
                onboarding_completed_at=utc_now(),
            )
            db.add(user.profile)
        else:
            if date_of_birth is not None:
                user.profile.date_of_birth = date_of_birth
            if gender is not None:
                user.profile.gender = gender.strip() or "other"
            if school_name is not None:
                user.profile.school_name = school_name.strip() or None
            user.profile.updated_at = utc_now()

    user.updated_at = utc_now()


def _reset_managed_user_password(user: User, password: str) -> None:
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user.password_hash = hash_password(password)
    if user.auth_type == "oauth":
        user.auth_type = "mixed"
    user.updated_at = utc_now()


def get_admin_teacher_detail(db: Session, teacher_id: int) -> dict:
    teacher = _get_managed_user(db, teacher_id, TEACHER_ROLE_NAME, "Teacher")

    classrooms = (
        db.query(Classroom)
        .filter(Classroom.created_by_user_id == teacher.id)
        .order_by(Classroom.created_at.desc(), Classroom.id.desc())
        .all()
    )
    classroom_ids = [classroom.id for classroom in classrooms]
    classroom_map = {classroom.id: classroom for classroom in classrooms}

    student_counts: dict[int, int] = {}
    class_exam_counts: dict[int, int] = {}
    class_document_counts: dict[int, int] = {}
    if classroom_ids:
        student_counts = _count_by(
            db.query(ClassroomMembership.classroom_id, func.count(ClassroomMembership.id))
            .join(User, User.id == ClassroomMembership.user_id)
            .filter(
                ClassroomMembership.classroom_id.in_(classroom_ids),
                User.role.has(Role.name == STUDENT_ROLE_NAME),
                User.status != "deleted",
            )
            .group_by(ClassroomMembership.classroom_id)
            .all()
        )
        class_exam_counts = _count_by(
            db.query(Exam.classroom_id, func.count(Exam.id))
            .filter(Exam.classroom_id.in_(classroom_ids))
            .group_by(Exam.classroom_id)
            .all()
        )
        class_document_counts = _count_by(
            db.query(LearningDocument.classroom_id, func.count(LearningDocument.id))
            .filter(LearningDocument.classroom_id.in_(classroom_ids))
            .group_by(LearningDocument.classroom_id)
            .all()
        )

    exams = (
        db.query(
            Exam.id,
            Exam.created_by_user_id,
            Exam.title,
            Exam.description,
            Exam.grade,
            Exam.scope,
            Exam.classroom_id,
            Exam.duration_minutes,
            Exam.start_time,
            Exam.end_time,
            Exam.total_points,
            Exam.is_published,
            Exam.is_active,
            Exam.created_at,
            Exam.updated_at,
        )
        .filter(Exam.created_by_user_id == teacher.id)
        .order_by(Exam.created_at.desc(), Exam.id.desc())
        .all()
    )
    exam_ids = [exam.id for exam in exams]
    ai_generated_exam_ids = get_ai_generated_exam_ids(db, exam_ids)
    exam_question_counts = (
        _count_by(
            db.query(ExamQuestion.exam_id, func.count(ExamQuestion.id))
            .filter(ExamQuestion.exam_id.in_(exam_ids))
            .group_by(ExamQuestion.exam_id)
            .all()
        )
        if exam_ids
        else {}
    )
    exam_attempt_counts = (
        _count_by(
            db.query(ExamAttempt.exam_id, func.count(ExamAttempt.id))
            .filter(ExamAttempt.exam_id.in_(exam_ids))
            .group_by(ExamAttempt.exam_id)
            .all()
        )
        if exam_ids
        else {}
    )
    exam_average_scores = _exam_average_scores(db, exam_ids)

    documents = (
        db.query(LearningDocument)
        .filter(LearningDocument.created_by_user_id == teacher.id)
        .order_by(LearningDocument.created_at.desc(), LearningDocument.id.desc())
        .all()
    )

    total_students = sum(student_counts.values())
    is_online = teacher.id in _recent_activity_user_ids(db, [teacher.id])

    return {
        "teacher": _serialize_teacher_user(
            teacher,
            len(classrooms),
            len(exams),
            len(documents),
            is_online,
        ),
        "metrics": [
            _metric("total_classes", "Tổng số lớp học", len(classrooms), subtext="lớp do giáo viên tạo"),
            _metric("total_students", "Tổng số học sinh", total_students, subtext="trong tất cả lớp"),
            _metric("total_exams", "Đề thi đã tạo", len(exams), subtext="từ tài khoản giáo viên"),
            _metric("total_documents", "Tài liệu", len(documents), subtext="tài liệu đã tạo"),
        ],
        "classes": [
            {
                "id": classroom.id,
                "name": classroom.name,
                "description": classroom.description,
                "join_code": classroom.join_code,
                "student_count": student_counts.get(classroom.id, 0),
                "exam_count": class_exam_counts.get(classroom.id, 0),
                "document_count": class_document_counts.get(classroom.id, 0),
                "status": "active",
                "created_at": classroom.created_at,
                "updated_at": classroom.updated_at,
            }
            for classroom in classrooms
        ],
        "exams": [
            {
                "id": exam.id,
                "title": exam.title,
                "description": exam.description,
                "grade": _serialize_exam_grade(exam.grade),
                "scope": exam.scope,
                "classroom_id": exam.classroom_id,
                "classroom_name": classroom_map[exam.classroom_id].name if exam.classroom_id in classroom_map else None,
                "teacher_id": teacher.id,
                "teacher_name": teacher.full_name,
                **build_exam_creator_metadata(
                    creator_id=teacher.id,
                    creator_name=teacher.full_name,
                    creator_role_name=TEACHER_ROLE_NAME,
                    is_ai_generated=exam.id in ai_generated_exam_ids,
                ),
                "duration_minutes": exam.duration_minutes,
                "start_time": exam.start_time,
                "end_time": exam.end_time,
                "total_points": exam.total_points,
                "question_count": exam_question_counts.get(exam.id, 0),
                "attempt_count": exam_attempt_counts.get(exam.id, 0),
                "average_score": exam_average_scores.get(exam.id),
                "is_published": exam.is_published,
                "is_active": exam.is_active,
                "created_at": exam.created_at,
                "updated_at": exam.updated_at,
            }
            for exam in exams
        ],
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "summary": document.summary,
                "content_preview": (document.summary or document.content or document.file_name or "")[:160],
                "file_url": document.file_url,
                "file_name": document.file_name,
                "file_content_type": document.file_content_type,
                "file_size_bytes": document.file_size_bytes,
                "scope": document.scope,
                "classroom_id": document.classroom_id,
                "classroom_name": classroom_map[document.classroom_id].name if document.classroom_id in classroom_map else None,
                "teacher_id": teacher.id,
                "teacher_name": teacher.full_name,
                "is_published": document.is_published,
                "content_length": len(document.content or ""),
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            }
            for document in documents
        ],
    }


def get_admin_student_detail(db: Session, student_id: int) -> dict:
    student = _get_managed_user(db, student_id, STUDENT_ROLE_NAME, "Student")

    memberships = (
        db.query(ClassroomMembership)
        .join(Classroom, Classroom.id == ClassroomMembership.classroom_id)
        .filter(ClassroomMembership.user_id == student.id)
        .order_by(ClassroomMembership.joined_at.desc(), ClassroomMembership.id.desc())
        .all()
    )
    classrooms = [membership.classroom for membership in memberships]
    classroom_ids = [classroom.id for classroom in classrooms]
    classroom_map = {classroom.id: classroom for classroom in classrooms}
    joined_at_map = {
        membership.classroom_id: membership.joined_at for membership in memberships
    }

    teacher_ids = [
        classroom.created_by_user_id
        for classroom in classrooms
        if classroom.created_by_user_id is not None
    ]
    teachers = (
        {teacher.id: teacher for teacher in db.query(User).filter(User.id.in_(teacher_ids)).all()}
        if teacher_ids
        else {}
    )

    student_counts: dict[int, int] = {}
    class_exam_counts: dict[int, int] = {}
    class_document_counts: dict[int, int] = {}
    if classroom_ids:
        student_counts = _count_by(
            db.query(ClassroomMembership.classroom_id, func.count(ClassroomMembership.id))
            .join(User, User.id == ClassroomMembership.user_id)
            .filter(
                ClassroomMembership.classroom_id.in_(classroom_ids),
                User.role.has(Role.name == STUDENT_ROLE_NAME),
                User.status != "deleted",
            )
            .group_by(ClassroomMembership.classroom_id)
            .all()
        )
        class_exam_counts = _count_by(
            db.query(Exam.classroom_id, func.count(Exam.id))
            .filter(Exam.classroom_id.in_(classroom_ids))
            .group_by(Exam.classroom_id)
            .all()
        )
        class_document_counts = _count_by(
            db.query(LearningDocument.classroom_id, func.count(LearningDocument.id))
            .filter(LearningDocument.classroom_id.in_(classroom_ids))
            .group_by(LearningDocument.classroom_id)
            .all()
        )

    exams = (
        db.query(
            Exam.id,
            Exam.created_by_user_id,
            Exam.title,
            Exam.description,
            Exam.grade,
            Exam.scope,
            Exam.classroom_id,
            Exam.duration_minutes,
            Exam.start_time,
            Exam.end_time,
            Exam.total_points,
            Exam.is_published,
            Exam.is_active,
            Exam.created_at,
            Exam.updated_at,
        )
        .filter(Exam.classroom_id.in_(classroom_ids))
        .order_by(Exam.created_at.desc(), Exam.id.desc())
        .all()
        if classroom_ids
        else []
    )
    exam_ids = [exam.id for exam in exams]
    ai_generated_exam_ids = get_ai_generated_exam_ids(db, exam_ids)
    exam_question_counts = (
        _count_by(
            db.query(ExamQuestion.exam_id, func.count(ExamQuestion.id))
            .filter(ExamQuestion.exam_id.in_(exam_ids))
            .group_by(ExamQuestion.exam_id)
            .all()
        )
        if exam_ids
        else {}
    )
    exam_attempt_counts = (
        _count_by(
            db.query(ExamAttempt.exam_id, func.count(ExamAttempt.id))
            .filter(ExamAttempt.exam_id.in_(exam_ids))
            .group_by(ExamAttempt.exam_id)
            .all()
        )
        if exam_ids
        else {}
    )
    exam_average_scores = _exam_average_scores(db, exam_ids)

    attempts = (
        db.query(
            ExamAttempt.id.label("attempt_id"),
            ExamAttempt.exam_id,
            ExamAttempt.score,
            ExamAttempt.total_points,
            ExamAttempt.status,
            ExamAttempt.started_at,
            ExamAttempt.submitted_at,
            ExamAttempt.created_at,
            Exam.title.label("exam_title"),
            Exam.classroom_id.label("exam_classroom_id"),
            Classroom.name.label("classroom_name"),
        )
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .outerjoin(Classroom, Classroom.id == Exam.classroom_id)
        .filter(ExamAttempt.user_id == student.id)
        .order_by(ExamAttempt.created_at.desc(), ExamAttempt.id.desc())
        .all()
    )

    document_filters = [LearningDocument.scope == "system"]
    if classroom_ids:
        document_filters.append(LearningDocument.classroom_id.in_(classroom_ids))
    documents = (
        db.query(LearningDocument)
        .filter(or_(*document_filters))
        .order_by(LearningDocument.created_at.desc(), LearningDocument.id.desc())
        .all()
    )

    attempt_count = len(attempts)
    average_score = _average_attempt_score(db, student.id)
    is_online = student.id in _recent_activity_user_ids(db, [student.id])

    return {
        "student": _serialize_student_user(
            student,
            len(classrooms),
            attempt_count,
            average_score,
            is_online,
        ),
        "metrics": [
            _metric("total_classes", "Tổng lớp học", len(classrooms), subtext="lớp đang tham gia"),
            _metric("submitted_attempts", "Bài làm", attempt_count, subtext="lượt làm bài"),
            _metric("average_score", "Điểm trung bình", average_score or 0, suffix="%", subtext="trên bài đã nộp"),
            _metric("available_documents", "Tài liệu", len(documents), subtext="có thể xem"),
        ],
        "classes": [
            {
                "id": classroom.id,
                "name": classroom.name,
                "description": classroom.description,
                "join_code": classroom.join_code,
                "teacher_id": classroom.created_by_user_id,
                "teacher_name": teachers[classroom.created_by_user_id].full_name if classroom.created_by_user_id in teachers else None,
                "student_count": student_counts.get(classroom.id, 0),
                "exam_count": class_exam_counts.get(classroom.id, 0),
                "document_count": class_document_counts.get(classroom.id, 0),
                "joined_at": joined_at_map.get(classroom.id),
                "status": "active",
                "created_at": classroom.created_at,
                "updated_at": classroom.updated_at,
            }
            for classroom in classrooms
        ],
        "attempts": [
            {
                "id": row.attempt_id,
                "exam_id": row.exam_id,
                "exam_title": row.exam_title,
                "classroom_id": row.exam_classroom_id,
                "classroom_name": row.classroom_name,
                "score": row.score,
                "total_points": row.total_points,
                "score_percent": _score_percent(row.score, row.total_points),
                "status": row.status,
                "started_at": row.started_at,
                "submitted_at": row.submitted_at,
                "created_at": row.created_at,
            }
            for row in attempts
        ],
        "exams": [
            {
                "id": exam.id,
                "title": exam.title,
                "description": exam.description,
                "grade": _serialize_exam_grade(exam.grade),
                "scope": exam.scope,
                "classroom_id": exam.classroom_id,
                "classroom_name": classroom_map[exam.classroom_id].name if exam.classroom_id in classroom_map else None,
                "teacher_id": exam.created_by_user_id,
                "teacher_name": teachers[exam.created_by_user_id].full_name if exam.created_by_user_id in teachers else None,
                **build_exam_creator_metadata(
                    creator_id=exam.created_by_user_id,
                    creator_name=teachers[exam.created_by_user_id].full_name
                    if exam.created_by_user_id in teachers
                    else None,
                    creator_role_name=TEACHER_ROLE_NAME if exam.created_by_user_id in teachers else None,
                    is_ai_generated=exam.id in ai_generated_exam_ids,
                ),
                "duration_minutes": exam.duration_minutes,
                "start_time": exam.start_time,
                "end_time": exam.end_time,
                "total_points": exam.total_points,
                "question_count": exam_question_counts.get(exam.id, 0),
                "attempt_count": exam_attempt_counts.get(exam.id, 0),
                "average_score": exam_average_scores.get(exam.id),
                "is_published": exam.is_published,
                "is_active": exam.is_active,
                "created_at": exam.created_at,
                "updated_at": exam.updated_at,
            }
            for exam in exams
        ],
        "documents": [
            {
                "id": document.id,
                "title": document.title,
                "summary": document.summary,
                "content_preview": (document.summary or document.content or document.file_name or "")[:160],
                "file_url": document.file_url,
                "file_name": document.file_name,
                "file_content_type": document.file_content_type,
                "file_size_bytes": document.file_size_bytes,
                "scope": document.scope,
                "classroom_id": document.classroom_id,
                "classroom_name": classroom_map[document.classroom_id].name if document.classroom_id in classroom_map else None,
                "teacher_id": document.created_by_user_id,
                "teacher_name": teachers[document.created_by_user_id].full_name if document.created_by_user_id in teachers else None,
                "is_published": document.is_published,
                "content_length": len(document.content or ""),
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            }
            for document in documents
        ],
    }


def update_admin_teacher_profile(
    db: Session,
    current_administrator: User,
    teacher_id: int,
    full_name: str | None,
    email: str | None,
    phone: str | None,
    avatar_url: str | None,
    date_of_birth: date | None,
    gender: str | None,
    school_name: str | None,
    status: str | None,
) -> dict:
    _ = current_administrator
    teacher = _get_managed_user(db, teacher_id, TEACHER_ROLE_NAME, "Teacher")
    _apply_admin_user_profile_update(
        db,
        teacher,
        full_name,
        email,
        phone,
        avatar_url,
        date_of_birth,
        gender,
        school_name,
        status,
    )
    db.commit()
    return get_admin_teacher_detail(db, teacher_id)


def update_admin_student_profile(
    db: Session,
    current_administrator: User,
    student_id: int,
    full_name: str | None,
    email: str | None,
    phone: str | None,
    avatar_url: str | None,
    date_of_birth: date | None,
    gender: str | None,
    school_name: str | None,
    status: str | None,
) -> dict:
    _ = current_administrator
    student = _get_managed_user(db, student_id, STUDENT_ROLE_NAME, "Student")
    _apply_admin_user_profile_update(
        db,
        student,
        full_name,
        email,
        phone,
        avatar_url,
        date_of_birth,
        gender,
        school_name,
        status,
    )
    db.commit()
    return get_admin_student_detail(db, student_id)


def reset_admin_teacher_password(
    db: Session,
    current_administrator: User,
    teacher_id: int,
    password: str,
) -> dict:
    _ = current_administrator
    teacher = _get_managed_user(db, teacher_id, TEACHER_ROLE_NAME, "Teacher")
    _reset_managed_user_password(teacher, password)
    db.commit()
    return {"message": "Teacher password reset successfully"}


def reset_admin_student_password(
    db: Session,
    current_administrator: User,
    student_id: int,
    password: str,
) -> dict:
    _ = current_administrator
    student = _get_managed_user(db, student_id, STUDENT_ROLE_NAME, "Student")
    _reset_managed_user_password(student, password)
    db.commit()
    return {"message": "Student password reset successfully"}
