from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

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


def bootstrap_student_learning_storage() -> None:
    Classroom.__table__.create(bind=engine, checkfirst=True)
    ClassroomMembership.__table__.create(bind=engine, checkfirst=True)
    LearningDocument.__table__.create(bind=engine, checkfirst=True)
    Exam.__table__.create(bind=engine, checkfirst=True)
    ExamQuestion.__table__.create(bind=engine, checkfirst=True)
    ExamQuestionOption.__table__.create(bind=engine, checkfirst=True)
    ExamAttempt.__table__.create(bind=engine, checkfirst=True)
    ExamAttemptAnswer.__table__.create(bind=engine, checkfirst=True)


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
        "exam_count": len(classroom.exams),
        "document_count": len(classroom.documents),
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
        "scope": document.scope,
        "classroom_id": document.classroom_id,
        "classroom_name": classroom.name if classroom else None,
        "created_at": document.created_at,
    }


def _get_exam_total_points(exam: Exam) -> int:
    computed_total = sum(question.points for question in exam.questions)
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
        "scope": exam.scope,
        "classroom_id": exam.classroom_id,
        "classroom_name": classroom.name if classroom else None,
        "duration_minutes": exam.duration_minutes,
        "total_points": _get_exam_total_points(exam),
        "question_count": len(exam.questions),
        "is_active": exam.is_active,
    }


def list_student_exams(db: Session, student: User, scope: str, classroom_id: int | None) -> dict:
    _validate_scope(scope, classroom_id)

    query = (
        db.query(Exam)
        .options(joinedload(Exam.classroom))
        .options(joinedload(Exam.questions))
        .filter(Exam.scope == scope, Exam.is_active.is_(True))
    )

    if scope == SCOPE_CLASS:
        _require_class_membership(db, student.id, classroom_id)
        query = query.filter(Exam.classroom_id == classroom_id)

    if scope == SCOPE_SYSTEM:
        query = query.filter(Exam.classroom_id.is_(None))

    exams = query.order_by(Exam.created_at.desc()).all()
    return {"items": [_serialize_exam_summary(exam) for exam in exams]}


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
            "order_index": question.order_index,
            "prompt": question.prompt,
            "points": question.points,
            "options": [
                {
                    "id": option.id,
                    "option_key": option.option_key,
                    "option_text": option.option_text,
                }
                for option in sorted(question.options, key=lambda item: item.id)
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
    answered_count = len([answer for answer in attempt.answers if answer.selected_option_id is not None])
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
        question = question_map.get(question_id)
        if not question:
            raise HTTPException(status_code=400, detail=f"Question {question_id} does not belong to this exam")

        if selected_option_id is not None and not any(
            option.id == selected_option_id for option in question.options
        ):
            raise HTTPException(
                status_code=400,
                detail=f"Option {selected_option_id} does not belong to question {question_id}",
            )

        attempt_answer = existing_answers.get(question_id)
        if not attempt_answer:
            attempt_answer = ExamAttemptAnswer(
                attempt_id=attempt.id,
                question_id=question_id,
                selected_option_id=selected_option_id,
                answered_at=utc_now(),
            )
            db.add(attempt_answer)
            continue

        attempt_answer.selected_option_id = selected_option_id
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
        correct_option = next((option for option in question.options if option.is_correct), None)
        selected_answer = answer_map.get(question.id)
        selected_option = selected_answer.selected_option if selected_answer else None
        is_correct = bool(
            selected_option
            and correct_option
            and selected_option.id == correct_option.id
        )
        result_answers.append(
            {
                "question_id": question.id,
                "prompt": question.prompt,
                "selected_option_id": selected_option.id if selected_option else None,
                "selected_option_text": selected_option.option_text if selected_option else None,
                "correct_option_id": correct_option.id if correct_option else None,
                "correct_option_text": correct_option.option_text if correct_option else None,
                "is_correct": is_correct,
                "points_earned": question.points if is_correct else 0,
                "max_points": question.points,
            }
        )

    return {
        "attempt_id": attempt.id,
        "exam_id": attempt.exam.id,
        "exam_title": attempt.exam.title,
        "status": attempt.status,
        "score": attempt.score or 0,
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
    score = 0
    correct_answers_count = 0

    for question in attempt.exam.questions:
        correct_option = next((option for option in question.options if option.is_correct), None)
        selected_answer = answer_map.get(question.id)
        selected_option = selected_answer.selected_option if selected_answer else None
        is_correct = bool(
            selected_option
            and correct_option
            and selected_option.id == correct_option.id
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
