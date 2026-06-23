import secrets
import string
import unicodedata
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.security import utc_now
from app.models.classroom import Classroom
from app.models.classroom_membership import ClassroomMembership
from app.models.ai_exam import AIExamGenerationJob
from app.models.exam import Exam
from app.models.exam_attempt import ExamAttempt
from app.models.exam_question import ExamQuestion
from app.models.exam_question_option import ExamQuestionOption
from app.models.learning_document import LearningDocument
from app.models.user import User
from app.services.media_service import delete_document_file, upload_document_file

TEACHER_ROLE_NAME = "teacher"
STUDENT_ROLE_NAME = "student"
SCOPE_SYSTEM = "system"
SCOPE_CLASS = "class"
QUESTION_TYPE_SINGLE_CHOICE = "single_choice"
QUESTION_TYPE_TRUE_FALSE = "true_false"
QUESTION_TYPE_SHORT_ANSWER = "short_answer"
QUESTION_TYPE_TEXT = "text"
SELECTION_QUESTION_TYPES = {QUESTION_TYPE_SINGLE_CHOICE, QUESTION_TYPE_TRUE_FALSE}
TEXT_ANSWER_QUESTION_TYPES = {QUESTION_TYPE_SHORT_ANSWER, QUESTION_TYPE_TEXT}


def require_teacher_user(db: Session, user_id: int) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not user.role or user.role.name != TEACHER_ROLE_NAME:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher role is required",
        )

    return user


def _generate_join_code(db: Session, length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        exists = db.query(Classroom).filter(Classroom.join_code == candidate).first()
        if not exists:
            return candidate


def _serialize_classroom(db: Session, classroom: Classroom) -> dict:
    student_count = int(
        db.query(func.count(ClassroomMembership.id))
        .join(User, User.id == ClassroomMembership.user_id)
        .filter(
            ClassroomMembership.classroom_id == classroom.id,
            User.role.has(name=STUDENT_ROLE_NAME),
        )
        .scalar()
        or 0
    )
    exam_count = int(
        db.query(func.count(Exam.id))
        .filter(Exam.classroom_id == classroom.id)
        .scalar()
        or 0
    )
    document_count = int(
        db.query(func.count(LearningDocument.id))
        .filter(LearningDocument.classroom_id == classroom.id)
        .scalar()
        or 0
    )
    return {
        "id": classroom.id,
        "name": classroom.name,
        "description": classroom.description,
        "join_code": classroom.join_code,
        "student_count": student_count,
        "exam_count": exam_count,
        "document_count": document_count,
        "created_at": classroom.created_at,
    }


def _require_teacher_classroom(db: Session, teacher_id: int, class_id: int) -> Classroom:
    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.id == class_id,
            Classroom.created_by_user_id == teacher_id,
        )
        .first()
    )
    if not classroom:
        raise HTTPException(status_code=404, detail="Class not found")
    return classroom


def list_teacher_classes(db: Session, teacher: User) -> dict:
    classrooms = (
        db.query(Classroom)
        .options(joinedload(Classroom.memberships))
        .options(joinedload(Classroom.exams))
        .options(joinedload(Classroom.documents))
        .filter(Classroom.created_by_user_id == teacher.id)
        .order_by(Classroom.created_at.desc())
        .all()
    )
    return {"items": [_serialize_classroom(db, classroom) for classroom in classrooms]}


def create_teacher_class(
    db: Session,
    teacher: User,
    name: str,
    description: str | None,
    join_code: str | None,
) -> dict:
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="name is required")

    normalized_join_code = join_code.strip().upper() if join_code else _generate_join_code(db)
    if not normalized_join_code:
        raise HTTPException(status_code=400, detail="join_code is required")

    existing = db.query(Classroom).filter(Classroom.join_code == normalized_join_code).first()
    if existing:
        raise HTTPException(status_code=409, detail="join_code already exists")

    classroom = Classroom(
        name=normalized_name,
        description=description.strip() if description else None,
        join_code=normalized_join_code,
        created_by_user_id=teacher.id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(classroom)
    db.commit()
    db.refresh(classroom)
    classroom = _require_teacher_classroom(db, teacher.id, classroom.id)
    return {
        "message": "Class created successfully",
        "classroom": _serialize_classroom(db, classroom),
    }


def update_teacher_class(
    db: Session,
    teacher: User,
    class_id: int,
    name: str | None,
    description: str | None,
    join_code: str | None,
) -> dict:
    classroom = _require_teacher_classroom(db, teacher.id, class_id)

    if name is not None:
        normalized_name = name.strip()
        if not normalized_name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        classroom.name = normalized_name

    if description is not None:
        classroom.description = description.strip() if description else None

    if join_code is not None:
        normalized_join_code = join_code.strip().upper()
        if not normalized_join_code:
            raise HTTPException(status_code=400, detail="join_code cannot be empty")

        existing = (
            db.query(Classroom)
            .filter(
                Classroom.join_code == normalized_join_code,
                Classroom.id != classroom.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="join_code already exists")

        classroom.join_code = normalized_join_code

    classroom.updated_at = utc_now()
    db.commit()
    db.refresh(classroom)
    classroom = _require_teacher_classroom(db, teacher.id, classroom.id)
    return {
        "message": "Class updated successfully",
        "classroom": _serialize_classroom(db, classroom),
    }


def delete_teacher_class(db: Session, teacher: User, class_id: int) -> dict:
    classroom = _require_teacher_classroom(db, teacher.id, class_id)
    attempt_count = (
        db.query(ExamAttempt)
        .join(Exam, Exam.id == ExamAttempt.exam_id)
        .filter(Exam.classroom_id == classroom.id)
        .count()
    )
    if attempt_count:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete class after students have started exam attempts",
        )

    exam_ids = select(Exam.id).where(Exam.classroom_id == classroom.id)
    question_ids = select(ExamQuestion.id).where(ExamQuestion.exam_id.in_(exam_ids))
    db.query(ExamQuestionOption).filter(ExamQuestionOption.question_id.in_(question_ids)).delete(
        synchronize_session=False
    )
    db.query(ExamQuestion).filter(ExamQuestion.exam_id.in_(exam_ids)).delete(
        synchronize_session=False
    )
    db.query(Exam).filter(Exam.classroom_id == classroom.id).delete(synchronize_session=False)
    db.query(LearningDocument).filter(LearningDocument.classroom_id == classroom.id).delete(
        synchronize_session=False
    )
    db.query(ClassroomMembership).filter(ClassroomMembership.classroom_id == classroom.id).delete(
        synchronize_session=False
    )
    db.query(Classroom).filter(Classroom.id == classroom.id).delete(synchronize_session=False)
    db.commit()
    return {"message": "Class deleted successfully"}


def _is_student_membership(membership: ClassroomMembership) -> bool:
    user = membership.user
    return bool(user and user.role and user.role.name == STUDENT_ROLE_NAME)


def _serialize_teacher_student(membership: ClassroomMembership) -> dict:
    user = membership.user
    profile = user.profile if user else None
    return {
        "id": user.id,
        "full_name": user.full_name,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "gender": profile.gender if profile else None,
        "school_name": profile.school_name if profile else None,
        "joined_at": membership.joined_at,
    }


def _get_student_user(db: Session, student_id: int) -> User:
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.id == student_id)
        .first()
    )
    if not user or not user.role or user.role.name != STUDENT_ROLE_NAME:
        raise HTTPException(status_code=404, detail="Student not found")

    return user


def _serialize_teacher_student_user(user: User) -> dict:
    profile = user.profile
    return {
        "id": user.id,
        "full_name": user.full_name,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "gender": profile.gender if profile else None,
        "school_name": profile.school_name if profile else None,
        "joined_at": None,
    }


def list_teacher_students(db: Session, teacher: User) -> dict:
    require_teacher_user(db, teacher.id)
    students = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.role.has(name=STUDENT_ROLE_NAME))
        .order_by(User.created_at.desc())
        .all()
    )
    return {"items": [_serialize_teacher_student_user(student) for student in students]}


def add_student_to_teacher_class(
    db: Session,
    teacher: User,
    class_id: int,
    student_id: int,
) -> dict:
    _require_teacher_classroom(db, teacher.id, class_id)
    student = _get_student_user(db, student_id)

    membership = (
        db.query(ClassroomMembership)
        .options(joinedload(ClassroomMembership.user).joinedload(User.profile))
        .options(joinedload(ClassroomMembership.user).joinedload(User.role))
        .filter(
            ClassroomMembership.classroom_id == class_id,
            ClassroomMembership.user_id == student.id,
        )
        .first()
    )
    if membership:
        return {
            "message": "Student already added to class",
            "student": _serialize_teacher_student(membership),
        }

    membership = ClassroomMembership(
        classroom_id=class_id,
        user_id=student.id,
        joined_at=utc_now(),
        created_at=utc_now(),
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    membership = (
        db.query(ClassroomMembership)
        .options(joinedload(ClassroomMembership.user).joinedload(User.profile))
        .options(joinedload(ClassroomMembership.user).joinedload(User.role))
        .filter(ClassroomMembership.id == membership.id)
        .first()
    )
    return {
        "message": "Student added to class successfully",
        "student": _serialize_teacher_student(membership),
    }


def list_teacher_class_students(db: Session, teacher: User, class_id: int) -> dict:
    _require_teacher_classroom(db, teacher.id, class_id)
    memberships = (
        db.query(ClassroomMembership)
        .options(joinedload(ClassroomMembership.user).joinedload(User.profile))
        .options(joinedload(ClassroomMembership.user).joinedload(User.role))
        .filter(ClassroomMembership.classroom_id == class_id)
        .order_by(ClassroomMembership.joined_at.asc())
        .all()
    )

    items = []
    for membership in memberships:
        if not _is_student_membership(membership):
            continue
        items.append(_serialize_teacher_student(membership))

    return {"items": items}


def remove_student_from_teacher_class(
    db: Session,
    teacher: User,
    class_id: int,
    student_id: int,
) -> dict:
    _require_teacher_classroom(db, teacher.id, class_id)
    membership = (
        db.query(ClassroomMembership)
        .options(joinedload(ClassroomMembership.user).joinedload(User.role))
        .filter(
            ClassroomMembership.classroom_id == class_id,
            ClassroomMembership.user_id == student_id,
        )
        .first()
    )
    if not membership or not _is_student_membership(membership):
        raise HTTPException(status_code=404, detail="Student membership not found")

    db.delete(membership)
    db.commit()
    return {"message": "Student removed from class successfully"}


def _validate_scope_for_teacher(
    db: Session,
    teacher: User,
    scope: str,
    classroom_id: int | None,
) -> Classroom | None:
    if scope not in {SCOPE_SYSTEM, SCOPE_CLASS}:
        raise HTTPException(status_code=400, detail="Invalid scope")

    if scope == SCOPE_SYSTEM:
        if classroom_id is not None:
            raise HTTPException(status_code=400, detail="classroom_id is not allowed for system scope")
        return None

    if classroom_id is None:
        raise HTTPException(status_code=400, detail="classroom_id is required for class scope")

    return _require_teacher_classroom(db, teacher.id, classroom_id)


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
        "is_published": document.is_published,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def _uploaded_document_title(title: str | None, filename: str | None) -> str:
    normalized_title = (title or "").strip()
    if normalized_title:
        return normalized_title

    filename_stem = Path(filename or "").stem.strip()
    if filename_stem:
        return filename_stem

    return "Untitled document"


def list_teacher_documents(
    db: Session,
    teacher: User,
    scope: str,
    classroom_id: int | None,
) -> dict:
    classroom = _validate_scope_for_teacher(db, teacher, scope, classroom_id)

    query = db.query(LearningDocument).options(joinedload(LearningDocument.classroom)).filter(
        LearningDocument.scope == scope
    )

    if scope == SCOPE_SYSTEM:
        query = query.filter(
            LearningDocument.classroom_id.is_(None),
            LearningDocument.created_by_user_id == teacher.id,
        )
    else:
        query = query.filter(LearningDocument.classroom_id == classroom.id)

    documents = query.order_by(LearningDocument.created_at.desc()).all()
    return {"items": [_serialize_document(document) for document in documents]}


def list_teacher_all_documents(db: Session, teacher: User) -> dict:
    classroom_ids = [
        classroom_id
        for (classroom_id,) in db.query(Classroom.id)
        .filter(Classroom.created_by_user_id == teacher.id)
        .all()
    ]

    filters = [
        and_(
            LearningDocument.scope == SCOPE_SYSTEM,
            LearningDocument.classroom_id.is_(None),
            LearningDocument.created_by_user_id == teacher.id,
        )
    ]
    if classroom_ids:
        filters.append(
            and_(
                LearningDocument.scope == SCOPE_CLASS,
                LearningDocument.classroom_id.in_(classroom_ids),
            )
        )

    documents = (
        db.query(LearningDocument)
        .options(joinedload(LearningDocument.classroom))
        .filter(or_(*filters))
        .order_by(LearningDocument.created_at.desc(), LearningDocument.id.desc())
        .all()
    )
    return {"items": [_serialize_document(document) for document in documents]}


def _get_teacher_document(db: Session, teacher: User, document_id: int) -> LearningDocument:
    document = (
        db.query(LearningDocument)
        .options(joinedload(LearningDocument.classroom))
        .filter(LearningDocument.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.scope == SCOPE_SYSTEM:
        if document.created_by_user_id != teacher.id:
            raise HTTPException(status_code=404, detail="Document not found")
        return document

    if document.classroom_id is None:
        raise HTTPException(status_code=400, detail="Class document is misconfigured")

    _require_teacher_classroom(db, teacher.id, document.classroom_id)
    return document


def _get_teacher_class_document(
    db: Session,
    teacher: User,
    class_id: int,
    document_id: int,
) -> LearningDocument:
    _require_teacher_classroom(db, teacher.id, class_id)
    document = _get_teacher_document(db, teacher, document_id)
    if document.scope != SCOPE_CLASS or document.classroom_id != class_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def create_teacher_uploaded_document(
    db: Session,
    teacher: User,
    title: str | None,
    summary: str | None,
    upload: UploadFile,
    scope: str,
    classroom_id: int | None,
    is_published: bool,
) -> dict:
    classroom = _validate_scope_for_teacher(db, teacher, scope, classroom_id)
    file_data = upload_document_file(upload)
    normalized_title = _uploaded_document_title(title, file_data["filename"])

    document = LearningDocument(
        title=normalized_title,
        summary=summary.strip() if summary else None,
        content="",
        file_url=file_data["url"],
        file_name=file_data["filename"],
        file_content_type=file_data["content_type"],
        file_size_bytes=file_data["size_bytes"],
        file_public_id=file_data["public_id"],
        scope=scope,
        classroom_id=classroom.id if classroom else None,
        created_by_user_id=teacher.id,
        is_published=is_published,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    try:
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        delete_document_file(file_data.get("public_id"))
        raise

    db.refresh(document)
    document = _get_teacher_document(db, teacher, document.id)
    return {
        "message": "Document uploaded successfully",
        "document": _serialize_document(document),
    }


def delete_teacher_document(db: Session, teacher: User, document_id: int) -> dict:
    document = _get_teacher_document(db, teacher, document_id)
    file_public_id = document.file_public_id
    db.delete(document)
    db.commit()
    delete_document_file(file_public_id)
    return {"message": "Document deleted successfully"}


def delete_teacher_class_document(
    db: Session,
    teacher: User,
    class_id: int,
    document_id: int,
) -> dict:
    _get_teacher_class_document(db, teacher, class_id, document_id)
    return delete_teacher_document(db, teacher, document_id)


def _get_exam_total_points(exam: Exam) -> float:
    computed_total = sum((question.points or 0) for question in exam.questions)
    return computed_total if computed_total > 0 else exam.total_points


def _get_exam_preview_image_url(exam: Exam) -> str | None:
    if exam.image_url:
        return exam.image_url
    for question in sorted(exam.questions, key=lambda item: item.order_index):
        if question.image_url:
            return question.image_url
    return None


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
        "attempt_count": len(exam.attempts),
        "is_published": exam.is_published,
        "is_active": exam.is_active,
        "created_at": exam.created_at,
        "updated_at": exam.updated_at,
    }


def _serialize_exam_detail(exam: Exam) -> dict:
    detail = _serialize_exam_summary(exam)
    detail["questions"] = [
        {
            "id": question.id,
            "question_type": _normalize_question_type(question.question_type),
            "order_index": question.order_index,
            "prompt": question.prompt,
            "explanation": question.explanation or "",
            "image_url": question.image_url,
            "points": question.points,
            "options": [
                {
                    "id": option.id,
                    "option_key": option.option_key,
                    "option_text": option.option_text,
                    "image_url": option.image_url,
                    "is_correct": option.is_correct,
                }
                for option in sorted(question.options, key=lambda item: item.id)
                if _is_selection_question_type(_normalize_question_type(question.question_type))
            ],
            "accepted_answers": [
                option.option_text
                for option in sorted(question.options, key=lambda item: item.id)
                if option.is_correct
            ]
            if _is_text_answer_question_type(_normalize_question_type(question.question_type))
            else [],
        }
        for question in sorted(exam.questions, key=lambda item: item.order_index)
    ]
    return detail


def _get_teacher_exam(db: Session, teacher: User, exam_id: int) -> Exam:
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.classroom))
        .options(joinedload(Exam.questions).joinedload(ExamQuestion.options))
        .options(joinedload(Exam.attempts))
        .filter(Exam.id == exam_id)
        .first()
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if exam.scope == SCOPE_SYSTEM:
        if exam.created_by_user_id != teacher.id:
            raise HTTPException(status_code=404, detail="Exam not found")
        return exam

    if exam.classroom_id is None:
        raise HTTPException(status_code=400, detail="Class exam is misconfigured")

    _require_teacher_classroom(db, teacher.id, exam.classroom_id)
    return exam


def _get_teacher_class_exam(db: Session, teacher: User, class_id: int, exam_id: int) -> Exam:
    _require_teacher_classroom(db, teacher.id, class_id)
    exam = _get_teacher_exam(db, teacher, exam_id)
    if exam.scope != SCOPE_CLASS or exam.classroom_id != class_id:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


def list_teacher_exams(
    db: Session,
    teacher: User,
    scope: str,
    classroom_id: int | None,
) -> dict:
    classroom = _validate_scope_for_teacher(db, teacher, scope, classroom_id)

    query = (
        db.query(Exam)
        .options(joinedload(Exam.classroom))
        .options(joinedload(Exam.questions))
        .options(joinedload(Exam.attempts))
        .filter(Exam.scope == scope)
    )

    if scope == SCOPE_SYSTEM:
        query = query.filter(Exam.classroom_id.is_(None), Exam.created_by_user_id == teacher.id)
    else:
        query = query.filter(Exam.classroom_id == classroom.id)

    exams = query.order_by(Exam.created_at.desc()).all()
    return {"items": [_serialize_exam_summary(exam) for exam in exams]}


def get_teacher_exam_detail(db: Session, teacher: User, exam_id: int) -> dict:
    exam = _get_teacher_exam(db, teacher, exam_id)
    return _serialize_exam_detail(exam)


def get_teacher_class_exam_detail(
    db: Session,
    teacher: User,
    class_id: int,
    exam_id: int,
) -> dict:
    exam = _get_teacher_class_exam(db, teacher, class_id, exam_id)
    return _serialize_exam_detail(exam)


def _validate_exam_questions(questions: list[dict]) -> list[dict]:
    if not questions:
        raise HTTPException(status_code=400, detail="At least one question is required")

    normalized_questions: list[dict] = []
    for index, question in enumerate(questions, start=1):
        question_type = _normalize_question_type(question.get("question_type"))
        prompt = (question.get("prompt") or "").strip()
        explanation = (question.get("explanation") or "").strip()
        question_image_url = (question.get("image_url") or "").strip() or None
        if not prompt and not question_image_url:
            raise HTTPException(
                status_code=400,
                detail=f"Question {index} must include prompt or image_url",
            )

        points = float(question["points"])
        normalized_options = []
        if question_type == QUESTION_TYPE_SINGLE_CHOICE:
            normalized_options = _normalize_single_choice_options(question, index)
        elif question_type == QUESTION_TYPE_TRUE_FALSE:
            normalized_options = _normalize_true_false_options(question, index)
        elif _is_text_answer_question_type(question_type):
            accepted_answers = question.get("accepted_answers") or []
            if not accepted_answers:
                raise HTTPException(
                    status_code=400,
                    detail=f"Question {index} must have at least 1 accepted answer",
                )

            seen_answers: set[str] = set()
            for answer_index, answer in enumerate(accepted_answers, start=1):
                normalized_answer = _normalize_text_answer(answer)
                if not normalized_answer:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Question {index} accepted answer {answer_index} cannot be empty",
                    )
                if normalized_answer in seen_answers:
                    continue
                seen_answers.add(normalized_answer)
                normalized_options.append(
                    {
                        "option_key": f"TEXT_{len(normalized_options) + 1}",
                        "option_text": answer.strip(),
                        "is_correct": True,
                    }
                )
        else:
            raise HTTPException(status_code=400, detail=f"Question {index}: unsupported question type")

        normalized_questions.append(
            {
                "question_type": question_type,
                "prompt": prompt,
                "explanation": explanation,
                "image_url": question_image_url,
                "order_index": question.get("order_index") or index,
                "points": points,
                "options": normalized_options,
            }
        )

    return normalized_questions


def _replace_exam_questions(exam: Exam, questions: list[dict]) -> float:
    total_points = 0.0
    exam.questions.clear()
    for question in questions:
        exam_question = ExamQuestion(
            question_type=question["question_type"],
            prompt=question["prompt"],
            explanation=question.get("explanation") or "",
            image_url=question.get("image_url"),
            order_index=question["order_index"],
            points=question["points"],
        )
        for option in question["options"]:
            exam_question.options.append(
                ExamQuestionOption(
                    option_key=option["option_key"],
                    option_text=option["option_text"],
                    image_url=option.get("image_url"),
                    is_correct=option["is_correct"],
                )
            )
        exam.questions.append(exam_question)
        total_points += question["points"]
    return total_points


def _normalize_question_type(question_type: str | None) -> str:
    if question_type in {
        QUESTION_TYPE_SINGLE_CHOICE,
        QUESTION_TYPE_TRUE_FALSE,
        QUESTION_TYPE_SHORT_ANSWER,
        QUESTION_TYPE_TEXT,
    }:
        return question_type
    return QUESTION_TYPE_SINGLE_CHOICE


def _is_selection_question_type(question_type: str) -> bool:
    return question_type in SELECTION_QUESTION_TYPES


def _is_text_answer_question_type(question_type: str) -> bool:
    return question_type in TEXT_ANSWER_QUESTION_TYPES


def _normalize_single_choice_options(question: dict, index: int) -> list[dict]:
    options = question["options"]
    if len(options) < 2:
        raise HTTPException(status_code=400, detail=f"Question {index} must have at least 2 options")

    correct_options = [option for option in options if option["is_correct"]]
    if len(correct_options) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Question {index} must have exactly 1 correct option",
        )

    normalized_options = []
    for option_index, option in enumerate(options, start=1):
        option_key = option["option_key"].strip()
        option_text = (option.get("option_text") or "").strip()
        option_image_url = (option.get("image_url") or "").strip() or None
        if not option_key:
            raise HTTPException(
                status_code=400,
                detail=f"Question {index} option {option_index} key is required",
            )
        if not option_text and not option_image_url:
            raise HTTPException(
                status_code=400,
                detail=f"Question {index} option {option_index} must include option_text or image_url",
            )
        normalized_options.append(
            {
                "option_key": option_key,
                "option_text": option_text,
                "image_url": option_image_url,
                "is_correct": option["is_correct"],
            }
        )

    return normalized_options


def _normalize_true_false_options(question: dict, index: int) -> list[dict]:
    correct_answer = _extract_true_false_correct_answer(question)
    if correct_answer is None:
        raise HTTPException(
            status_code=400,
            detail=f"Question {index} must identify whether true or false is correct",
        )

    return [
        {
            "option_key": "A",
            "option_text": "Đúng",
            "image_url": None,
            "is_correct": correct_answer is True,
        },
        {
            "option_key": "B",
            "option_text": "Sai",
            "image_url": None,
            "is_correct": correct_answer is False,
        },
    ]


def _extract_true_false_correct_answer(question: dict) -> bool | None:
    options = question.get("options") or []
    correct_options = [option for option in options if option.get("is_correct")]
    if len(correct_options) == 1:
        correct_option = correct_options[0]
        normalized = _normalize_true_false_answer(correct_option.get("option_text"))
        if normalized is not None:
            return normalized

        try:
            option_index = options.index(correct_option)
        except ValueError:
            option_index = 0
        return option_index == 0

    accepted_answers = question.get("accepted_answers") or []
    for answer in accepted_answers:
        normalized = _normalize_true_false_answer(answer)
        if normalized is not None:
            return normalized

    return None


def _normalize_true_false_answer(value: str | None) -> bool | None:
    normalized = _normalize_text_answer(value)
    if normalized in {"true", "yes", "1", "dung", "đúng"}:
        return True
    if normalized in {"false", "no", "0", "sai"}:
        return False
    return None


def _normalize_text_answer(value: str | None) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = " ".join(normalized.strip().lower().split())
    return normalized


def create_teacher_exam(
    db: Session,
    teacher: User,
    title: str,
    description: str | None,
    image_url: str | None,
    scope: str,
    classroom_id: int | None,
    duration_minutes: int,
    is_published: bool,
    is_active: bool,
    questions: list[dict],
) -> dict:
    classroom = _validate_scope_for_teacher(db, teacher, scope, classroom_id)
    normalized_title = title.strip()
    normalized_image_url = image_url.strip() if image_url else None
    if not normalized_title:
        raise HTTPException(status_code=400, detail="title is required")

    normalized_questions = _validate_exam_questions(questions)

    exam = Exam(
        created_by_user_id=teacher.id,
        title=normalized_title,
        description=description.strip() if description else None,
        image_url=normalized_image_url or None,
        scope=scope,
        classroom_id=classroom.id if classroom else None,
        duration_minutes=duration_minutes,
        total_points=0.0,
        is_published=is_published,
        is_active=is_active,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(exam)
    exam.total_points = _replace_exam_questions(exam, normalized_questions)
    db.commit()
    db.refresh(exam)
    exam = _get_teacher_exam(db, teacher, exam.id)
    return {
        "message": "Exam created successfully",
        "exam": _serialize_exam_detail(exam),
    }


def update_teacher_exam(
    db: Session,
    teacher: User,
    exam_id: int,
    title: str | None,
    description: str | None,
    image_url: str | None,
    scope: str | None,
    classroom_id: int | None,
    duration_minutes: int | None,
    is_published: bool | None,
    is_active: bool | None,
    questions: list[dict] | None,
) -> dict:
    exam = _get_teacher_exam(db, teacher, exam_id)
    target_scope = scope or exam.scope
    if target_scope == SCOPE_SYSTEM:
        target_classroom_id = None
    elif classroom_id is not None:
        target_classroom_id = classroom_id
    else:
        target_classroom_id = exam.classroom_id
    classroom = _validate_scope_for_teacher(db, teacher, target_scope, target_classroom_id)

    if title is not None:
        normalized_title = title.strip()
        if not normalized_title:
            raise HTTPException(status_code=400, detail="title cannot be empty")
        exam.title = normalized_title

    if description is not None:
        exam.description = description.strip() if description else None

    if image_url is not None:
        exam.image_url = image_url.strip() or None

    if duration_minutes is not None:
        exam.duration_minutes = duration_minutes

    if is_published is not None:
        exam.is_published = is_published

    if is_active is not None:
        exam.is_active = is_active

    exam.scope = target_scope
    exam.classroom_id = classroom.id if classroom else None

    if questions is not None:
        if exam.attempts:
            raise HTTPException(
                status_code=400,
                detail="Cannot replace questions after students have started attempts",
            )
        normalized_questions = _validate_exam_questions(questions)
        exam.total_points = _replace_exam_questions(exam, normalized_questions)

    exam.updated_at = utc_now()
    db.commit()
    db.refresh(exam)
    exam = _get_teacher_exam(db, teacher, exam.id)
    return {
        "message": "Exam updated successfully",
        "exam": _serialize_exam_detail(exam),
    }


def update_teacher_class_exam(
    db: Session,
    teacher: User,
    class_id: int,
    exam_id: int,
    title: str | None,
    description: str | None,
    image_url: str | None,
    duration_minutes: int | None,
    is_published: bool | None,
    is_active: bool | None,
    questions: list[dict] | None,
) -> dict:
    _get_teacher_class_exam(db, teacher, class_id, exam_id)
    return update_teacher_exam(
        db,
        teacher,
        exam_id,
        title,
        description,
        image_url,
        SCOPE_CLASS,
        class_id,
        duration_minutes,
        is_published,
        is_active,
        questions,
    )


def delete_teacher_exam(db: Session, teacher: User, exam_id: int) -> dict:
    exam = _get_teacher_exam(db, teacher, exam_id)
    if exam.attempts:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete exam after students have started attempts",
        )
    _unlink_ai_exam_jobs_for_exam(db, exam.id)
    db.delete(exam)
    db.commit()
    return {"message": "Exam deleted successfully"}


def _unlink_ai_exam_jobs_for_exam(db: Session, exam_id: int) -> None:
    db.query(AIExamGenerationJob).filter(AIExamGenerationJob.quiz_id == exam_id).update(
        {
            AIExamGenerationJob.quiz_id: None,
            AIExamGenerationJob.status: "completed",
            AIExamGenerationJob.updated_at: utc_now(),
        },
        synchronize_session=False,
    )


def set_teacher_exam_visibility(
    db: Session,
    teacher: User,
    exam_id: int,
    is_published: bool,
) -> dict:
    exam = _get_teacher_exam(db, teacher, exam_id)
    exam.is_published = is_published
    exam.updated_at = utc_now()
    db.commit()
    db.refresh(exam)
    exam = _get_teacher_exam(db, teacher, exam.id)
    return {
        "message": "Exam published successfully" if is_published else "Exam set to private successfully",
        "exam": _serialize_exam_detail(exam),
    }
