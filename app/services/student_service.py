from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
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

STUDENT_ROLE_NAME = "student"
SCOPE_SYSTEM = "system"
SCOPE_CLASS = "class"
ATTEMPT_STATUS_IN_PROGRESS = "in_progress"
ATTEMPT_STATUS_SUBMITTED = "submitted"
QUESTION_TYPE_SINGLE_CHOICE = "single_choice"
QUESTION_TYPE_TEXT = "text"
PASSING_SCORE_PERCENT = 50.0


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
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS scope VARCHAR(20) DEFAULT 'system'",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS classroom_id INTEGER",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 30",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS total_points NUMERIC(10, 4) DEFAULT 0",
        "ALTER TABLE exams ALTER COLUMN total_points TYPE NUMERIC(10, 4) USING total_points::numeric",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS is_published BOOLEAN DEFAULT FALSE",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE exams ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP",
        "UPDATE exams SET scope = COALESCE(scope, 'system')",
        "UPDATE exams SET duration_minutes = COALESCE(duration_minutes, 30)",
        "UPDATE exams SET total_points = COALESCE(total_points, 0)",
        "UPDATE exams SET is_published = COALESCE(is_published, FALSE)",
        "UPDATE exams SET is_active = COALESCE(is_active, TRUE)",
        "UPDATE exams SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)",
        "UPDATE exams SET updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS question_type VARCHAR(30) DEFAULT 'single_choice'",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS prompt TEXT",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS image_url TEXT",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0",
        "ALTER TABLE exam_questions ADD COLUMN IF NOT EXISTS points NUMERIC(10, 4) DEFAULT 1",
        "ALTER TABLE exam_questions ALTER COLUMN points TYPE NUMERIC(10, 4) USING points::numeric",
        "UPDATE exam_questions SET question_type = COALESCE(question_type, 'single_choice')",
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
        return {
            "message": "Already joined this class",
            "classroom": _serialize_classroom(existing_membership),
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

    return {
        "message": "Joined class successfully",
        "classroom": _serialize_classroom(membership),
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


def _serialize_exam_summary(exam: Exam) -> dict:
    classroom = exam.classroom
    return {
        "id": exam.id,
        "title": exam.title,
        "description": exam.description,
        "image_url": exam.image_url or _get_exam_preview_image_url(exam),
        "scope": exam.scope,
        "classroom_id": exam.classroom_id,
        "classroom_name": classroom.name if classroom else None,
        "duration_minutes": exam.duration_minutes,
        "total_points": _get_exam_total_points(exam),
        "question_count": len(exam.questions),
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
    if question_type == QUESTION_TYPE_TEXT:
        return QUESTION_TYPE_TEXT
    return QUESTION_TYPE_SINGLE_CHOICE


def _normalize_text_answer(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = " ".join(normalized.strip().lower().split())
    return normalized


def list_student_exams(db: Session, student: User, scope: str, classroom_id: int | None) -> dict:
    _validate_scope(scope, classroom_id)

    query = (
        db.query(Exam)
        .options(joinedload(Exam.classroom))
        .options(joinedload(Exam.questions))
        .filter(Exam.scope == scope, Exam.is_published.is_(True))
    )

    if scope == SCOPE_CLASS:
        _require_class_membership(db, student.id, classroom_id)
        query = query.filter(Exam.classroom_id == classroom_id)

    if scope == SCOPE_SYSTEM:
        query = query.filter(Exam.classroom_id.is_(None))

    exams = query.order_by(Exam.created_at.desc()).all()
    return {"items": [_serialize_exam_summary(exam) for exam in exams]}


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

    detail = _serialize_exam_summary(exam)
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
                if _normalize_question_type(question.question_type) == QUESTION_TYPE_SINGLE_CHOICE
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
        answer_text = answer_input.get("answer_text")
        question = question_map.get(question_id)
        if not question:
            raise HTTPException(status_code=400, detail=f"Question {question_id} does not belong to this exam")

        question_type = _normalize_question_type(question.question_type)
        normalized_answer_text = answer_text.strip() if isinstance(answer_text, str) else None

        if question_type == QUESTION_TYPE_SINGLE_CHOICE:
            if selected_option_id is not None and not any(
                option.id == selected_option_id for option in question.options
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Option {selected_option_id} does not belong to question {question_id}",
                )
            normalized_answer_text = None
        else:
            if selected_option_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Question {question_id} only accepts text answers",
                )
            if normalized_answer_text == "":
                normalized_answer_text = None

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
        normalized_submitted_text = _normalize_text_answer(selected_answer.answer_text if selected_answer else None)
        if question_type == QUESTION_TYPE_SINGLE_CHOICE:
            is_correct = bool(
                selected_option
                and correct_option
                and selected_option.id == correct_option.id
            )
        else:
            accepted_answers = {_normalize_text_answer(option.option_text) for option in correct_options}
            is_correct = bool(normalized_submitted_text and normalized_submitted_text in accepted_answers)
        result_answers.append(
            {
                "question_id": question.id,
                "question_type": question_type,
                "prompt": question.prompt,
                "question_image_url": question.image_url,
                "selected_option_id": selected_option.id if selected_option else None,
                "selected_option_text": selected_option.option_text if selected_option else None,
                "selected_option_image_url": selected_option.image_url if selected_option else None,
                "submitted_answer_text": selected_answer.answer_text if selected_answer else None,
                "correct_option_id": correct_option.id if correct_option else None,
                "correct_option_text": correct_option.option_text if correct_option else None,
                "correct_option_image_url": correct_option.image_url if correct_option else None,
                "accepted_answers": [option.option_text for option in correct_options]
                if question_type == QUESTION_TYPE_TEXT
                else [],
                "is_correct": is_correct,
                "points_earned": question.points if is_correct else 0.0,
                "max_points": question.points,
            }
        )

    return {
        "attempt_id": attempt.id,
        "exam_id": attempt.exam.id,
        "exam_title": attempt.exam.title,
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
        question_type = _normalize_question_type(question.question_type)
        correct_options = [option for option in question.options if option.is_correct]
        correct_option = correct_options[0] if correct_options else None
        selected_answer = answer_map.get(question.id)
        selected_option = selected_answer.selected_option if selected_answer else None
        if question_type == QUESTION_TYPE_SINGLE_CHOICE:
            is_correct = bool(
                selected_option
                and correct_option
                and selected_option.id == correct_option.id
            )
        else:
            accepted_answers = {_normalize_text_answer(option.option_text) for option in correct_options}
            is_correct = bool(
                selected_answer
                and _normalize_text_answer(selected_answer.answer_text) in accepted_answers
            )
        if is_correct:
            score += question.points
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
