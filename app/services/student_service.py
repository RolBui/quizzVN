from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
import json
import unicodedata

from app.core.security import utc_now
from app.database import engine
from app.models.classroom import Classroom
from app.models.classroom_membership import ClassroomMembership
from app.models.exam import Exam
from app.models.exam_attempt import ExamAttempt
from app.models.exam_attempt_answer import ExamAttemptAnswer
from app.models.exam_question import ExamQuestion
from app.models.exam_question_option import ExamQuestionOption
from app.models.learning_document import LearningDocument
from app.models.user import User
from app.services.exam_creator_metadata import build_exam_creator_metadata, get_ai_generated_exam_ids

STUDENT_ROLE_NAME = "student"
SCOPE_SYSTEM = "system"
SCOPE_CLASS = "class"
ATTEMPT_STATUS_IN_PROGRESS = "in_progress"
ATTEMPT_STATUS_SUBMITTED = "submitted"
QUESTION_TYPE_SINGLE_CHOICE = "single_choice"
QUESTION_TYPE_MULTIPLE_CHOICE = "multiple_choice"
QUESTION_TYPE_TRUE_FALSE = "true_false"
QUESTION_TYPE_FILL_IN_BLANK = "fill_in_blank"
QUESTION_TYPE_SHORT_ANSWER = "short_answer"
QUESTION_TYPE_TEXT = "text"
SELECTION_QUESTION_TYPES = {QUESTION_TYPE_SINGLE_CHOICE, QUESTION_TYPE_MULTIPLE_CHOICE, QUESTION_TYPE_TRUE_FALSE}
TEXT_ANSWER_QUESTION_TYPES = {QUESTION_TYPE_FILL_IN_BLANK, QUESTION_TYPE_SHORT_ANSWER, QUESTION_TYPE_TEXT}
PASSING_SCORE_PERCENT = 50.0
DEFAULT_EXAM_GRADE = "Chưa phân loại"


def _normalize_exam_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_question_type(question_type: str | None) -> str:
    if question_type in {
        QUESTION_TYPE_SINGLE_CHOICE,
        QUESTION_TYPE_MULTIPLE_CHOICE,
        QUESTION_TYPE_TRUE_FALSE,
        QUESTION_TYPE_FILL_IN_BLANK,
        QUESTION_TYPE_SHORT_ANSWER,
        QUESTION_TYPE_TEXT,
    }:
        return question_type
    return QUESTION_TYPE_SINGLE_CHOICE


def bootstrap_student_learning_storage() -> None:
    Classroom.__table__.create(bind=engine, checkfirst=True)
    ClassroomMembership.__table__.create(bind=engine, checkfirst=True)
    LearningDocument.__table__.create(bind=engine, checkfirst=True)
    Exam.__table__.create(bind=engine, checkfirst=True)
    ExamQuestion.__table__.create(bind=engine, checkfirst=True)
    ExamQuestionOption.__table__.create(bind=engine, checkfirst=True)
    ExamAttempt.__table__.create(bind=engine, checkfirst=True)
    ExamAttemptAnswer.__table__.create(bind=engine, checkfirst=True)
    _ensure_student_learning_columns()


def _ensure_student_learning_columns() -> None:
    statements = [
        "ALTER TABLE learning_documents ADD COLUMN IF NOT EXISTS content TEXT DEFAULT ''",
        "ALTER TABLE learning_documents ADD COLUMN IF NOT EXISTS file_url TEXT",
        "ALTER TABLE learning_documents ADD COLUMN IF NOT EXISTS file_name VARCHAR(255)",
        "ALTER TABLE learning_documents ADD COLUMN IF NOT EXISTS file_content_type VARCHAR(255)",
        "ALTER TABLE learning_documents ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER",
        "ALTER TABLE learning_documents ADD COLUMN IF NOT EXISTS file_public_id VARCHAR(255)",
        "UPDATE learning_documents SET content = COALESCE(content, '')",
        "ALTER TABLE learning_documents ALTER COLUMN content SET DEFAULT ''",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS image_url TEXT",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS grade VARCHAR(50) DEFAULT 'Chưa phân loại'",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS scope VARCHAR(20) DEFAULT 'system'",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS classroom_id INTEGER",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 30",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS start_time TIMESTAMPTZ",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS end_time TIMESTAMPTZ",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS total_points NUMERIC(10, 4) DEFAULT 0",
        "ALTER TABLE exams ALTER COLUMN total_points TYPE NUMERIC(10, 4) USING total_points::numeric",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT FALSE",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        "UPDATE exams SET scope = COALESCE(scope, 'system')",
        "UPDATE exams SET grade = COALESCE(NULLIF(BTRIM(grade), ''), 'Chưa phân loại')",
        "UPDATE exams SET duration_minutes = COALESCE(duration_minutes, 30)",
        "UPDATE exams SET total_points = COALESCE(total_points, 0)",
        "UPDATE exams SET is_published = COALESCE(is_published, FALSE)",
        "UPDATE exams SET is_active = COALESCE(is_active, TRUE)",
        "UPDATE exams SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)",
        "UPDATE exams SET updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS question_type VARCHAR(30) DEFAULT 'single_choice'",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS prompt TEXT",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS explanation TEXT DEFAULT ''",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS image_url TEXT",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS points NUMERIC(10, 4) DEFAULT 1",
        "ALTER TABLE exam_questions ALTER COLUMN points TYPE NUMERIC(10, 4) USING points::numeric",
        "UPDATE exam_questions SET question_type = COALESCE(question_type, 'single_choice')",
        "UPDATE exam_questions SET explanation = COALESCE(explanation, '')",
        "UPDATE exam_questions SET order_index = COALESCE(order_index, 0)",
        "UPDATE exam_questions SET points = COALESCE(points, 1)",
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'exam_questions' AND column_name = 'content'
            ) THEN
                EXECUTE '
                    UPDATE exam_questions
                    SET prompt = COALESCE(prompt, content)
                    WHERE prompt IS NULL
                ';
            END IF;
        END $$
        """,
        "UPDATE exam_questions SET prompt = COALESCE(prompt, '')",
        """
        UPDATE exams AS e
        SET image_url = q.image_url
        FROM (
            SELECT DISTINCT ON (exam_id)
                exam_id,
                image_url
            FROM exam_questions
            WHERE image_url IS NOT NULL
              AND BTRIM(image_url) <> ''
            ORDER BY exam_id, order_index NULLS LAST, id
        ) AS q
        WHERE e.id = q.exam_id
          AND (e.image_url IS NULL OR BTRIM(e.image_url) = '')
        """,
        "ALTER TABLE exam_question_options ADD COLUMN IF NOT EXISTS image_url TEXT",
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS user_id INTEGER",
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS score NUMERIC(10, 4)",
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS total_points NUMERIC(10, 4) DEFAULT 0",
        "ALTER TABLE exam_attempts ALTER COLUMN score TYPE NUMERIC(10, 4) USING score::numeric",
        "ALTER TABLE exam_attempts ALTER COLUMN total_points TYPE NUMERIC(10, 4) USING total_points::numeric",
        "ALTER TABLE exam_attempts ALTER COLUMN score DROP NOT NULL",
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS correct_answers_count INTEGER",
        "ALTER TABLE exam_attempts ALTER COLUMN correct_answers_count DROP NOT NULL",
        "ALTER TABLE exam_attempts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
        "UPDATE exam_attempts SET total_points = COALESCE(total_points, 0)",
        "UPDATE exam_attempts SET updated_at = COALESCE(updated_at, submitted_at, started_at, created_at, CURRENT_TIMESTAMP)",
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'exam_attempts' AND column_name = 'student_id'
            ) THEN
                EXECUTE '
                    UPDATE exam_attempts
                    SET user_id = COALESCE(user_id, student_id)
                    WHERE user_id IS NULL
                ';
            END IF;
        END $$
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'exam_attempts' AND column_name = 'student_id'
            ) THEN
                EXECUTE 'ALTER TABLE exam_attempts ALTER COLUMN student_id DROP NOT NULL';
            END IF;
        END $$
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'exam_attempts' AND column_name = 'submitted_at'
            ) THEN
                EXECUTE 'ALTER TABLE exam_attempts ALTER COLUMN submitted_at DROP NOT NULL';
            END IF;
        END $$
        """,
        "ALTER TABLE exam_attempt_answers ADD COLUMN IF NOT EXISTS selected_option_id INTEGER",
        "ALTER TABLE exam_attempt_answers ADD COLUMN IF NOT EXISTS answer_text TEXT",
        "ALTER TABLE exam_attempt_answers ADD COLUMN IF NOT EXISTS answered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'exam_attempt_answers' AND column_name = 'created_at'
            ) THEN
                EXECUTE '
                    UPDATE exam_attempt_answers
                    SET answered_at = COALESCE(answered_at, created_at, CURRENT_TIMESTAMP)
                    WHERE answered_at IS NULL
                ';
            ELSE
                EXECUTE '
                    UPDATE exam_attempt_answers
                    SET answered_at = COALESCE(answered_at, CURRENT_TIMESTAMP)
                    WHERE answered_at IS NULL
                ';
            END IF;
        END $$
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def require_student_user(db: Session, user_id: int) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.role or user.role.name != STUDENT_ROLE_NAME:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student role is required",
        )

    return user


def _validate_scope(scope: str, classroom_id: int | None) -> None:
    if scope not in {SCOPE_SYSTEM, SCOPE_CLASS}:
        raise HTTPException(status_code=400, detail="Invalid scope")

    if scope == SCOPE_CLASS and classroom_id is None:
        raise HTTPException(status_code=400, detail="class_id is required for class scope")

    if scope == SCOPE_SYSTEM and classroom_id is not None:
        raise HTTPException(status_code=400, detail="class_id is not allowed for system scope")


def _get_membership(db: Session, student_id: int, classroom_id: int) -> ClassroomMembership | None:
    return (
        db.query(ClassroomMembership)
        .options(joinedload(ClassroomMembership.classroom).joinedload(Classroom.exams))
        .options(joinedload(ClassroomMembership.classroom).joinedload(Classroom.documents))
        .filter(
            ClassroomMembership.user_id == student_id,
            ClassroomMembership.classroom_id == classroom_id,
        )
        .first()
    )


def _require_class_membership(db: Session, student_id: int, classroom_id: int) -> ClassroomMembership:
    membership = _get_membership(db, student_id, classroom_id)
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this class")
    return membership


def _serialize_classroom(membership: ClassroomMembership) -> dict:
    classroom = membership.classroom
    return {
        "id": classroom.id,
        "name": classroom.name,
        "description": classroom.description,
        "join_code": classroom.join_code,
        "joined_at": membership.joined_at,
        "exam_count": len([exam for exam in classroom.exams if exam.is_published]),
        "document_count": len([document for document in classroom.documents if document.is_published]),
    }


def list_student_classes(db: Session, student: User) -> dict:
    memberships = (
        db.query(ClassroomMembership)
        .options(joinedload(ClassroomMembership.classroom).joinedload(Classroom.exams))
        .options(joinedload(ClassroomMembership.classroom).joinedload(Classroom.documents))
        .filter(ClassroomMembership.user_id == student.id)
        .order_by(ClassroomMembership.joined_at.desc())
        .all()
    )
    return {"items": [_serialize_classroom(membership) for membership in memberships]}


def join_student_class(db: Session, student: User, join_code: str) -> dict:
    normalized_code = join_code.strip()
    if not normalized_code:
        raise HTTPException(status_code=400, detail="join_code is required")

    classroom = db.query(Classroom).filter(Classroom.join_code == normalized_code).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Class not found")

    existing_membership = _get_membership(db, student.id, classroom.id)
    if existing_membership:
        member_count = db.query(ClassroomMembership).filter(ClassroomMembership.classroom_id == classroom.id).count()
        class_info = {
            "id": f"cls-{classroom.id}",
            "name": classroom.name,
            "academic_year": "Năm học 2024 - 2025",
            "member_count": member_count,
            "status": "Đang học",
        }
        return {
            "message": "Đã tham gia lớp học này",
            "classroom": _serialize_classroom(existing_membership),
            "class_info": class_info,
        }

    membership = ClassroomMembership(
        classroom_id=classroom.id,
        user_id=student.id,
        joined_at=utc_now(),
        created_at=utc_now(),
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    membership = _require_class_membership(db, student.id, classroom.id)

    member_count = db.query(ClassroomMembership).filter(ClassroomMembership.classroom_id == classroom.id).count()
    class_info = {
        "id": f"cls-{classroom.id}",
        "name": classroom.name,
        "academic_year": "Năm học 2024 - 2025",
        "member_count": member_count,
        "status": "Đang học",
    }

    return {
        "message": "Tham gia lớp học thành công",
        "classroom": _serialize_classroom(membership),
        "class_info": class_info,
    }


def _serialize_document(document: LearningDocument) -> dict:
    classroom = document.classroom
    return {
        "id": document.id,
        "title": document.title,
        "summary": document.summary,
        "content": document.content,
        "file_url": document.file_url,
        "file_name": document.file_name,
        "file_content_type": document.file_content_type,
        "file_size_bytes": document.file_size_bytes,
        "scope": document.scope,
        "classroom_id": document.classroom_id,
        "classroom_name": classroom.name if classroom else None,
        "created_at": document.created_at,
    }


def _get_exam_total_points(exam: Exam) -> float:
    computed_total = sum((question.points or 0) for question in exam.questions)
    if computed_total > 0:
        return computed_total
    return exam.total_points


def _serialize_exam_grade(value: str | None) -> str:
    normalized = (value or "").strip()
    return normalized or DEFAULT_EXAM_GRADE


def list_student_documents(db: Session, student: User, scope: str, classroom_id: int | None) -> dict:
    _validate_scope(scope, classroom_id)

    query = (
        db.query(LearningDocument)
        .options(joinedload(LearningDocument.classroom))
        .filter(
            LearningDocument.scope == scope,
            LearningDocument.is_published.is_(True),
        )
    )

    if scope == SCOPE_CLASS:
        _require_class_membership(db, student.id, classroom_id)
        query = query.filter(LearningDocument.classroom_id == classroom_id)

    if scope == SCOPE_SYSTEM:
        query = query.filter(LearningDocument.classroom_id.is_(None))

    documents = query.order_by(LearningDocument.created_at.desc()).all()
    return {"items": [_serialize_document(document) for document in documents]}


def _is_ai_generated_exam(db: Session, exam_id: int | None) -> bool:
    return bool(exam_id and exam_id in get_ai_generated_exam_ids(db, [exam_id]))


def _serialize_exam_summary(exam: Exam, is_ai_generated: bool = False) -> dict:
    classroom = exam.classroom
    return {
        "id": exam.id,
        "title": exam.title,
        "description": exam.description,
        "grade": _serialize_exam_grade(exam.grade),
        "image_url": exam.image_url or _get_exam_preview_image_url(exam),
        "scope": exam.scope,
        "classroom_id": exam.classroom_id,
        "classroom_name": classroom.name if classroom else None,
        "duration_minutes": exam.duration_minutes,
        "start_time": exam.start_time,
        "end_time": exam.end_time,
        "total_points": _get_exam_total_points(exam),
        "question_count": len(exam.questions),
        **build_exam_creator_metadata(exam.created_by, is_ai_generated=is_ai_generated),
        "is_active": exam.is_active,
    }


def _get_exam_preview_image_url(exam: Exam) -> str | None:
    if exam.image_url:
        return exam.image_url
    for question in sorted(exam.questions, key=lambda item: item.order_index):
        if question.image_url:
            return question.image_url
    return None


def _calculate_score_percent(score: float | None, total_points: float | None) -> float:
    normalized_total_points = float(total_points or 0)
    if normalized_total_points <= 0:
        return 0.0
    normalized_score = float(score or 0)
    return round((normalized_score / normalized_total_points) * 100, 2)


def _serialize_attempt_history_item(attempt: ExamAttempt) -> dict:
    score = attempt.score or 0.0
    total_points = attempt.total_points or _get_exam_total_points(attempt.exam)
    score_percent = _calculate_score_percent(score, total_points)
    correct_answers_count = attempt.correct_answers_count or 0
    classroom = attempt.exam.classroom
    return {
        "attempt_id": attempt.id,
        "exam_id": attempt.exam.id,
        "exam_title": attempt.exam.title,
        "exam_description": attempt.exam.description,
        "exam_grade": _serialize_exam_grade(attempt.exam.grade),
        "exam_image_url": attempt.exam.image_url or _get_exam_preview_image_url(attempt.exam),
        "scope": attempt.exam.scope,
        "classroom_id": attempt.exam.classroom_id,
        "classroom_name": classroom.name if classroom else None,
        "score": score,
        "total_points": total_points,
        "score_percent": score_percent,
        "correct_answers_count": correct_answers_count,
        "total_questions": len(attempt.exam.questions),
        "is_passed": score_percent >= PASSING_SCORE_PERCENT,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
    }


def _normalize_question_type(question_type: str | None) -> str:
    if question_type in {
        QUESTION_TYPE_SINGLE_CHOICE,
        QUESTION_TYPE_MULTIPLE_CHOICE,
        QUESTION_TYPE_TRUE_FALSE,
        QUESTION_TYPE_FILL_IN_BLANK,
        QUESTION_TYPE_SHORT_ANSWER,
        QUESTION_TYPE_TEXT,
    }:
        return question_type
    return QUESTION_TYPE_SINGLE_CHOICE


def _is_selection_question_type(question_type: str) -> bool:
    return question_type in SELECTION_QUESTION_TYPES


def _is_text_answer_question_type(question_type: str) -> bool:
    return question_type in TEXT_ANSWER_QUESTION_TYPES


def _normalize_text_answer(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = " ".join(normalized.strip().lower().split())
    return normalized


def list_student_exams(
    db: Session,
    student: User,
    scope: str,
    classroom_id: int | None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    _validate_scope(scope, classroom_id)

    query = (
        db.query(Exam)
        .options(joinedload(Exam.classroom))
        .options(joinedload(Exam.created_by).joinedload(User.role))
        .options(joinedload(Exam.questions))
        .filter(Exam.scope == scope, Exam.is_published.is_(True))
    )

    if scope == SCOPE_CLASS:
        _require_class_membership(db, student.id, classroom_id)
        query = query.filter(Exam.classroom_id == classroom_id)

    if scope == SCOPE_SYSTEM:
        query = query.filter(Exam.classroom_id.is_(None))

    total = int(query.count())
    exams = query.order_by(Exam.created_at.desc()).offset(offset).limit(limit).all()
    ai_generated_exam_ids = get_ai_generated_exam_ids(db, [exam.id for exam in exams])
    return {
        "items": [
            _serialize_exam_summary(exam, is_ai_generated=exam.id in ai_generated_exam_ids)
            for exam in exams
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def list_student_exam_results(
    db: Session,
    student: User,
    scope: str | None = None,
    classroom_id: int | None = None,
) -> dict:
    if scope is not None:
        _validate_scope(scope, classroom_id)

    query = (
        db.query(ExamAttempt)
        .join(ExamAttempt.exam)
        .options(joinedload(ExamAttempt.exam).joinedload(Exam.classroom))
        .options(joinedload(ExamAttempt.exam).joinedload(Exam.questions))
        .filter(
            ExamAttempt.user_id == student.id,
            ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED,
        )
    )

    if scope == SCOPE_CLASS:
        _require_class_membership(db, student.id, classroom_id)
        query = query.filter(
            Exam.scope == SCOPE_CLASS,
            Exam.classroom_id == classroom_id,
        )
    elif scope == SCOPE_SYSTEM:
        query = query.filter(
            Exam.scope == SCOPE_SYSTEM,
            Exam.classroom_id.is_(None),
        )

    attempts = query.order_by(ExamAttempt.submitted_at.desc(), ExamAttempt.id.desc()).all()

    items = [_serialize_attempt_history_item(attempt) for attempt in attempts]
    total_completed_exams = len(items)
    passed_exams = len([item for item in items if item["is_passed"]])
    average_score_percent = round(
        sum(item["score_percent"] for item in items) / total_completed_exams,
        2,
    ) if total_completed_exams else 0.0

    return {
        "summary": {
            "total_completed_exams": total_completed_exams,
            "passed_exams": passed_exams,
            "average_score_percent": average_score_percent,
        },
        "items": items,
    }


def _get_visible_exam(db: Session, student: User, exam_id: int) -> Exam:
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.classroom))
        .options(joinedload(Exam.created_by).joinedload(User.role))
        .options(joinedload(Exam.questions).joinedload(ExamQuestion.options))
        .filter(Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if not exam.is_published:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.scope == SCOPE_CLASS:
        if exam.classroom_id is None:
            raise HTTPException(status_code=400, detail="Class exam is misconfigured")
        _require_class_membership(db, student.id, exam.classroom_id)

    return exam


def get_student_exam_detail(db: Session, student: User, exam_id: int) -> dict:
    exam = _get_visible_exam(db, student, exam_id)
    existing_attempt = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam.id,
            ExamAttempt.user_id == student.id,
            ExamAttempt.status == ATTEMPT_STATUS_IN_PROGRESS,
        )
        .order_by(ExamAttempt.started_at.desc())
        .first()
    )

    detail = _serialize_exam_summary(exam, is_ai_generated=_is_ai_generated_exam(db, exam.id))
    detail["questions"] = [
        {
            "id": question.id,
            "question_type": _normalize_question_type(question.question_type),
            "order_index": question.order_index,
            "prompt": question.prompt,
            "image_url": question.image_url,
            "points": question.points,
            "options": [
                {
                    "id": option.id,
                    "option_key": option.option_key,
                    "option_text": option.option_text,
                    "image_url": option.image_url,
                }
                for option in sorted(question.options, key=lambda item: item.id)
                if _is_selection_question_type(_normalize_question_type(question.question_type))
            ],
        }
        for question in sorted(exam.questions, key=lambda item: item.order_index)
    ]
    detail["in_progress_attempt_id"] = existing_attempt.id if existing_attempt else None
    return detail


def _get_attempt_for_student(db: Session, student: User, attempt_id: int) -> ExamAttempt:
    attempt = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam).joinedload(Exam.questions).joinedload(ExamQuestion.options))
        .options(joinedload(ExamAttempt.answers).joinedload(ExamAttemptAnswer.selected_option))
        .filter(ExamAttempt.id == attempt_id, ExamAttempt.user_id == student.id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt


def _serialize_attempt_summary(attempt: ExamAttempt) -> dict:
    answered_count = len(
        [
            answer
            for answer in attempt.answers
            if answer.selected_option_id is not None or _normalize_text_answer(answer.answer_text)
        ]
    )
    return {
        "id": attempt.id,
        "exam_id": attempt.exam_id,
        "status": attempt.status,
        "score": attempt.score,
        "total_points": attempt.total_points,
        "correct_answers_count": attempt.correct_answers_count,
        "total_questions": len(attempt.exam.questions),
        "answered_count": answered_count,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
    }


def start_student_exam_attempt(db: Session, student: User, exam_id: int) -> dict:
    exam = _get_visible_exam(db, student, exam_id)
    if not exam.is_active:
        raise HTTPException(status_code=400, detail="Exam is not active")

    now = utc_now()
    start_time = _normalize_exam_datetime(exam.start_time)
    end_time = _normalize_exam_datetime(exam.end_time)
    if start_time and now < start_time:
        raise HTTPException(status_code=400, detail="Bài thi chưa đến thời gian làm.")
    if end_time and now >= end_time:
        raise HTTPException(status_code=400, detail="Bài thi đã hết thời gian làm.")

    existing_attempt = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam).joinedload(Exam.questions))
        .options(joinedload(ExamAttempt.answers))
        .filter(
            ExamAttempt.exam_id == exam.id,
            ExamAttempt.user_id == student.id,
            ExamAttempt.status == ATTEMPT_STATUS_IN_PROGRESS,
        )
        .order_by(ExamAttempt.started_at.desc())
        .first()
    )
    if existing_attempt:
        return {
            "message": "Existing in-progress attempt returned",
            "attempt": _serialize_attempt_summary(existing_attempt),
        }

    attempt = ExamAttempt(
        exam_id=exam.id,
        user_id=student.id,
        status=ATTEMPT_STATUS_IN_PROGRESS,
        score=None,
        total_points=_get_exam_total_points(exam),
        correct_answers_count=None,
        started_at=utc_now(),
        submitted_at=None,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    attempt = _get_attempt_for_student(db, student, attempt.id)
    return {
        "message": "Attempt created successfully",
        "attempt": _serialize_attempt_summary(attempt),
    }


def _get_selected_option_ids_from_answer(selected_answer: ExamAttemptAnswer | None) -> set[int]:
    if not selected_answer:
        return set()
    if selected_answer.answer_text:
        try:
            parsed = json.loads(selected_answer.answer_text)
            if isinstance(parsed, list):
                return {int(x) for x in parsed if isinstance(x, (int, str)) and str(x).isdigit()}
        except Exception:
            pass
    if selected_answer.selected_option_id is not None:
        return {selected_answer.selected_option_id}
    return set()


def _eval_question_correctness(question: ExamQuestion, selected_answer: ExamAttemptAnswer | None) -> bool:
    question_type = _normalize_question_type(question.question_type)
    correct_options = [option for option in question.options if option.is_correct]

    if question_type == QUESTION_TYPE_MULTIPLE_CHOICE:
        correct_ids = {option.id for option in correct_options}
        user_ids = _get_selected_option_ids_from_answer(selected_answer)
        return bool(correct_ids and user_ids == correct_ids)

    if _is_selection_question_type(question_type):
        correct_option = correct_options[0] if correct_options else None
        selected_option = selected_answer.selected_option if selected_answer else None
        return bool(
            selected_option
            and correct_option
            and selected_option.id == correct_option.id
        )

    if _is_text_answer_question_type(question_type):
        accepted_answers = {_normalize_text_answer(option.option_text) for option in correct_options}
        submitted_text = _normalize_text_answer(selected_answer.answer_text if selected_answer else None)
        return bool(submitted_text and submitted_text in accepted_answers)

    return False


def save_student_attempt_answers(
    db: Session,
    student: User,
    attempt_id: int,
    answers: list[dict],
) -> dict:
    attempt = _get_attempt_for_student(db, student, attempt_id)
    if attempt.status != ATTEMPT_STATUS_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Attempt is no longer editable")

    question_map = {question.id: question for question in attempt.exam.questions}
    existing_answers = {answer.question_id: answer for answer in attempt.answers}

    for answer_input in answers:
        question_id = answer_input["question_id"]
        selected_option_id = answer_input.get("selected_option_id")
        selected_option_ids = answer_input.get("selected_option_ids")
        answer_text = answer_input.get("answer_text")
        question = question_map.get(question_id)
        if not question:
            raise HTTPException(status_code=400, detail=f"Question {question_id} does not belong to this exam")

        question_type = _normalize_question_type(question.question_type)
        normalized_answer_text = answer_text.strip() if isinstance(answer_text, str) else None

        if selected_option_ids is not None and not isinstance(selected_option_ids, list):
            selected_option_ids = None

        if question_type == QUESTION_TYPE_MULTIPLE_CHOICE:
            if selected_option_ids:
                for opt_id in selected_option_ids:
                    if not any(o.id == opt_id for o in question.options):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Option {opt_id} does not belong to question {question_id}",
                        )
                selected_option_id = selected_option_ids[0]
                normalized_answer_text = json.dumps(selected_option_ids)
            elif selected_option_id is not None:
                if not any(o.id == selected_option_id for o in question.options):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Option {selected_option_id} does not belong to question {question_id}",
                    )
                normalized_answer_text = json.dumps([selected_option_id])
            else:
                normalized_answer_text = None
        elif _is_selection_question_type(question_type):
            if selected_option_id is not None and not any(
                option.id == selected_option_id for option in question.options
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Option {selected_option_id} does not belong to question {question_id}",
                )
            normalized_answer_text = None
        elif _is_text_answer_question_type(question_type):
            if selected_option_id is not None or selected_option_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Question {question_id} only accepts text answers",
                )
            if normalized_answer_text == "":
                normalized_answer_text = None
        else:
            raise HTTPException(status_code=400, detail=f"Question {question_id}: unsupported question type")

        attempt_answer = existing_answers.get(question_id)
        if not attempt_answer:
            attempt_answer = ExamAttemptAnswer(
                attempt_id=attempt.id,
                question_id=question_id,
                selected_option_id=selected_option_id,
                answer_text=normalized_answer_text,
                answered_at=utc_now(),
            )
            db.add(attempt_answer)
            continue

        attempt_answer.selected_option_id = selected_option_id
        attempt_answer.answer_text = normalized_answer_text
        attempt_answer.answered_at = utc_now()

    attempt.updated_at = utc_now()
    db.commit()

    refreshed_attempt = _get_attempt_for_student(db, student, attempt.id)
    return {
        "message": "Answers saved successfully",
        "attempt": _serialize_attempt_summary(refreshed_attempt),
    }


def _serialize_attempt_result(attempt: ExamAttempt) -> dict:
    answer_map = {answer.question_id: answer for answer in attempt.answers}
    result_answers = []

    for question in sorted(attempt.exam.questions, key=lambda item: item.order_index):
        question_type = _normalize_question_type(question.question_type)
        correct_options = [option for option in question.options if option.is_correct]
        correct_option = correct_options[0] if correct_options else None
        selected_answer = answer_map.get(question.id)
        selected_option = selected_answer.selected_option if selected_answer else None
        is_correct = _eval_question_correctness(question, selected_answer)

        user_option_ids = (
            sorted(list(_get_selected_option_ids_from_answer(selected_answer)))
            if question_type == QUESTION_TYPE_MULTIPLE_CHOICE
            else None
        )

        result_answers.append(
            {
                "question_id": question.id,
                "question_type": question_type,
                "prompt": question.prompt,
                "explanation": question.explanation or "",
                "question_image_url": question.image_url,
                "selected_option_id": selected_option.id if selected_option else None,
                "selected_option_ids": user_option_ids,
                "selected_option_text": selected_option.option_text if selected_option else None,
                "selected_option_image_url": selected_option.image_url if selected_option else None,
                "submitted_answer_text": selected_answer.answer_text if selected_answer else None,
                "correct_option_id": correct_option.id if correct_option else None,
                "correct_option_text": correct_option.option_text if correct_option else None,
                "correct_option_image_url": correct_option.image_url if correct_option else None,
                "accepted_answers": [option.option_text for option in correct_options]
                if _is_text_answer_question_type(question_type)
                else [],
                "is_correct": is_correct,
                "points_earned": float(question.points or 0) if is_correct else 0.0,
                "max_points": float(question.points or 0),
            }
        )

    return {
        "attempt_id": attempt.id,
        "exam_id": attempt.exam.id,
        "exam_title": attempt.exam.title,
        "exam_grade": _serialize_exam_grade(attempt.exam.grade),
        "exam_image_url": attempt.exam.image_url or _get_exam_preview_image_url(attempt.exam),
        "status": attempt.status,
        "score": attempt.score or 0.0,
        "total_points": attempt.total_points or _get_exam_total_points(attempt.exam),
        "correct_answers_count": attempt.correct_answers_count or 0,
        "total_questions": len(attempt.exam.questions),
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "answers": result_answers,
    }


def submit_student_attempt(db: Session, student: User, attempt_id: int) -> dict:
    attempt = _get_attempt_for_student(db, student, attempt_id)

    if attempt.status == ATTEMPT_STATUS_SUBMITTED:
        return {
            "message": "Attempt already submitted",
            "result": _serialize_attempt_result(attempt),
        }

    answer_map = {answer.question_id: answer for answer in attempt.answers}
    score = 0.0
    correct_answers_count = 0

    for question in attempt.exam.questions:
        selected_answer = answer_map.get(question.id)
        is_correct = _eval_question_correctness(question, selected_answer)
        if is_correct:
            score += float(question.points or 0)
            correct_answers_count += 1

    attempt.status = ATTEMPT_STATUS_SUBMITTED
    attempt.score = score
    attempt.total_points = _get_exam_total_points(attempt.exam)
    attempt.correct_answers_count = correct_answers_count
    attempt.submitted_at = utc_now()
    attempt.updated_at = utc_now()
    db.commit()

    refreshed_attempt = _get_attempt_for_student(db, student, attempt.id)
    return {
        "message": "Attempt submitted successfully",
        "result": _serialize_attempt_result(refreshed_attempt),
    }


def get_student_attempt_result(db: Session, student: User, attempt_id: int) -> dict:
    attempt = _get_attempt_for_student(db, student, attempt_id)
    if attempt.status != ATTEMPT_STATUS_SUBMITTED:
        raise HTTPException(status_code=400, detail="Attempt has not been submitted yet")
    return {"result": _serialize_attempt_result(attempt)}


def get_student_in_progress(db: Session, student: User) -> dict | None:
    attempt = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam))
        .filter(
            ExamAttempt.user_id == student.id,
            ExamAttempt.status == ATTEMPT_STATUS_IN_PROGRESS,
        )
        .order_by(ExamAttempt.updated_at.desc(), ExamAttempt.started_at.desc())
        .first()
    )
    if not attempt or not attempt.exam:
        return None

    exam = attempt.exam
    total_questions = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).count()
    completed_questions = db.query(ExamAttemptAnswer).filter(ExamAttemptAnswer.attempt_id == attempt.id).count()
    progress_percentage = round((completed_questions / total_questions * 100), 1) if total_questions > 0 else 0.0

    return {
        "attempt_id": f"att-{attempt.id}",
        "exam_id": f"exam-{exam.id}",
        "title": exam.title,
        "subject_name": exam.grade or "Toán 9",
        "chapter_name": "Chương 3",
        "completed_questions": completed_questions,
        "total_questions": total_questions,
        "progress_percentage": progress_percentage,
    }


def get_student_dashboard_metrics(db: Session, student: User) -> dict:
    memberships = db.query(ClassroomMembership).filter(ClassroomMembership.user_id == student.id).all()
    class_ids = [m.classroom_id for m in memberships]

    query = db.query(Exam).filter(Exam.is_published == True, Exam.is_active == True)
    if class_ids:
        query = query.filter((Exam.scope == SCOPE_SYSTEM) | (Exam.classroom_id.in_(class_ids)))
    else:
        query = query.filter(Exam.scope == SCOPE_SYSTEM)
    available_exams = query.all()

    submitted_exam_ids = set(
        r[0]
        for r in db.query(ExamAttempt.exam_id)
        .filter(ExamAttempt.user_id == student.id, ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED)
        .all()
    )
    pending_count = sum(1 for e in available_exams if e.id not in submitted_exam_ids)

    completed_attempts = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.user_id == student.id, ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED)
        .all()
    )
    if completed_attempts:
        scores = []
        for att in completed_attempts:
            if att.total_points and float(att.total_points) > 0 and att.score is not None:
                pct = (float(att.score) / float(att.total_points)) * 10
                scores.append(pct)
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    else:
        avg_score = 0.0

    total_seconds = 0
    for att in completed_attempts:
        sub_at = _normalize_exam_datetime(att.submitted_at)
        st_at = _normalize_exam_datetime(att.started_at)
        if sub_at and st_at:
            delta = (sub_at - st_at).total_seconds()
            if delta > 0:
                total_seconds += int(delta)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        display_time = f"{hours}h {minutes}m"
    else:
        display_time = f"{minutes}m"

    now = utc_now()
    dates_active = set()
    all_attempts = db.query(ExamAttempt.started_at).filter(ExamAttempt.user_id == student.id).all()
    for (st,) in all_attempts:
        norm_st = _normalize_exam_datetime(st)
        if norm_st:
            dates_active.add(norm_st.date())

    streak = 0
    check_date = now.date()
    while check_date in dates_active:
        streak += 1
        check_date -= timedelta(days=1)

    pending_diff = f"+{pending_count} đề mới" if pending_count > 0 else "Không có đề cần làm"
    score_diff_text = f"Đã làm {len(completed_attempts)} bài thi" if completed_attempts else "Chưa có kết quả"
    time_diff_text = f"{display_time} tuần này" if total_seconds > 0 else "Chưa có phút học"
    streak_label = f"{streak} ngày liên tiếp" if streak > 0 else "0 ngày liên tiếp"

    return {
        "pending_exams_count": pending_count,
        "pending_exams_diff": pending_diff,
        "average_score": avg_score,
        "score_diff": score_diff_text,
        "study_time_seconds": total_seconds,
        "study_time_display": display_time,
        "study_time_diff": time_diff_text,
        "streak_days": streak,
        "streak_text": streak_label,
    }


def get_student_activity_chart(db: Session, student: User, start_date_str: str | None = None) -> dict:
    now = utc_now()
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = now.date() - timedelta(days=now.weekday())
    else:
        start_date = now.date() - timedelta(days=now.weekday())

    day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]
    activities = []

    attempts = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.user_id == student.id,
            ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED,
        )
        .all()
    )

    total_tests_week = 0
    for i in range(7):
        curr_date = start_date + timedelta(days=i)
        day_str = day_names[i]

        day_attempts = [
            a for a in attempts
            if a.submitted_at and (_normalize_exam_datetime(a.submitted_at).date() == curr_date)
        ]
        tests_completed = len(day_attempts)
        total_tests_week += tests_completed
        study_sec = 0
        for a in day_attempts:
            sub_at = _normalize_exam_datetime(a.submitted_at)
            st_at = _normalize_exam_datetime(a.started_at)
            if sub_at and st_at and (sub_at - st_at).total_seconds() > 0:
                study_sec += int((sub_at - st_at).total_seconds())

        study_minutes = study_sec // 60

        is_highlight = (curr_date == now.date())
        item = {
            "day": day_str,
            "date": curr_date.strftime("%Y-%m-%d"),
            "tests_completed": tests_completed,
            "study_minutes": study_minutes,
        }
        if is_highlight:
            item["is_highlight"] = True

        activities.append(item)

    comp_note = (
        f"Bạn đã hoàn thành {total_tests_week} bài thi tuần này."
        if total_tests_week > 0
        else "Bạn chưa có hoạt động làm bài nào tuần này. Hãy bắt đầu ngay!"
    )

    return {
        "daily_activities": activities,
        "comparison_note": comp_note,
    }


def get_student_subject_progress(db: Session, student: User) -> list:
    completed_attempts = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam))
        .filter(ExamAttempt.user_id == student.id, ExamAttempt.status == ATTEMPT_STATUS_SUBMITTED)
        .all()
    )

    if not completed_attempts:
        return []

    subject_scores: dict[str, list[float]] = {}
    for att in completed_attempts:
        if att.exam:
            subj_name = att.exam.grade or "Môn học"
            if att.total_points and float(att.total_points) > 0 and att.score is not None:
                pct = (float(att.score) / float(att.total_points)) * 100
                subject_scores.setdefault(subj_name, []).append(pct)

    colors = ["#8B5CF6", "#FF5E84", "#F59E0B", "#10B981", "#3B82F6"]
    result = []
    for idx, (s_name, s_pcts) in enumerate(subject_scores.items()):
        avg_pct = round(sum(s_pcts) / len(s_pcts), 1)
        result.append({
            "subject_id": f"sub-{idx+1}",
            "name": s_name,
            "progress": avg_pct,
            "color": colors[idx % len(colors)],
        })

    return result


def get_student_dashboard_classes(db: Session, student: User, limit: int = 6) -> list:
    memberships = (
        db.query(ClassroomMembership)
        .options(joinedload(ClassroomMembership.classroom))
        .filter(ClassroomMembership.user_id == student.id)
        .order_by(ClassroomMembership.joined_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for m in memberships:
        classroom = m.classroom
        member_count = db.query(ClassroomMembership).filter(ClassroomMembership.classroom_id == classroom.id).count()
        result.append({
            "id": f"cls-{classroom.id}",
            "name": classroom.name,
            "academic_year": "Năm học 2024 - 2025",
            "member_count": member_count,
            "status": "Đang học",
        })
    return result


def get_student_recommended_exams(db: Session, student: User, limit: int = 3) -> list:
    memberships = db.query(ClassroomMembership).filter(ClassroomMembership.user_id == student.id).all()
    class_ids = [m.classroom_id for m in memberships]

    query = db.query(Exam).filter(Exam.is_published == True, Exam.is_active == True)
    if class_ids:
        query = query.filter((Exam.scope == SCOPE_SYSTEM) | (Exam.classroom_id.in_(class_ids)))
    else:
        query = query.filter(Exam.scope == SCOPE_SYSTEM)

    exams = query.order_by(Exam.created_at.desc()).limit(limit).all()
    result = []
    for idx, exam in enumerate(exams):
        q_count = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).count()
        difficulty = "Dễ" if idx % 2 == 0 else "Trung bình"
        result.append({
            "id": f"exam-{exam.id}",
            "title": exam.title,
            "subject_name": exam.grade or "Toán 9",
            "question_count": q_count,
            "difficulty": difficulty,
        })
    return result


def get_student_recent_activities(db: Session, student: User, limit: int = 5) -> list:
    activities = []
    now = utc_now()

    def _format_time_ago(dt: datetime | None) -> str:
        norm_dt = _normalize_exam_datetime(dt)
        if not norm_dt:
            return "Vừa xong"
        diff_sec = int((now - norm_dt).total_seconds())
        if diff_sec < 60:
            return "Vừa xong"
        if diff_sec < 3600:
            return f"{diff_sec // 60} phút trước"
        if diff_sec < 86400:
            return f"{diff_sec // 3600} giờ trước"
        if diff_sec < 172800:
            return "Hôm qua"
        return f"{diff_sec // 86400} ngày trước"

    attempts = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam))
        .filter(ExamAttempt.user_id == student.id)
        .order_by(ExamAttempt.updated_at.desc(), ExamAttempt.started_at.desc())
        .limit(limit)
        .all()
    )

    for att in attempts:
        if not att.exam:
            continue
        if att.status == ATTEMPT_STATUS_SUBMITTED:
            raw_time = att.submitted_at or att.updated_at or att.started_at
            act_time = _normalize_exam_datetime(raw_time) or now
            score_val = float(att.score) if att.score is not None else 0.0
            activities.append({
                "id": f"act-att-{att.id}",
                "action_type": "exam_submit",
                "title": f'Bạn đã làm đề "{att.exam.title}"',
                "time_ago": _format_time_ago(act_time),
                "created_at": act_time.isoformat(),
                "_dt": act_time,
            })
            if score_val >= 8.0:
                activities.append({
                    "id": f"act-score-{att.id}",
                    "action_type": "score_achieved",
                    "title": f'Bạn đã đạt {score_val} điểm trong đề "{att.exam.title}"',
                    "time_ago": _format_time_ago(act_time),
                    "created_at": act_time.isoformat(),
                    "_dt": act_time,
                })

    memberships = (
        db.query(ClassroomMembership)
        .options(joinedload(ClassroomMembership.classroom))
        .filter(ClassroomMembership.user_id == student.id)
        .order_by(ClassroomMembership.joined_at.desc())
        .limit(limit)
        .all()
    )

    for m in memberships:
        if m.classroom:
            act_time = _normalize_exam_datetime(m.joined_at) or now
            activities.append({
                "id": f"act-cls-{m.id}",
                "action_type": "class_join",
                "title": f'Bạn đã tham gia lớp "{m.classroom.name}"',
                "time_ago": _format_time_ago(act_time),
                "created_at": act_time.isoformat(),
                "_dt": act_time,
            })

    activities.sort(key=lambda x: x["_dt"], reverse=True)

    result = []
    for act in activities[:limit]:
        clean_act = {k: v for k, v in act.items() if k != "_dt"}
        result.append(clean_act)

    return result

