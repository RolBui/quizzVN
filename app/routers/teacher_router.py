from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_teacher
from app.schemas.common import MessageResponse
from app.schemas.teacher import (
    AddTeacherStudentRequest,
    CreateTeacherClassRequest,
    CreateTeacherDocumentRequest,
    CreateTeacherExamRequest,
    TeacherClassListResponse,
    TeacherClassResponse,
    TeacherDocumentListResponse,
    TeacherDocumentResponse,
    TeacherExamDetailSchema,
    TeacherExamListResponse,
    TeacherExamResponse,
    TeacherStudentListResponse,
    TeacherStudentResponse,
    UpdateTeacherDocumentRequest,
    UpdateTeacherExamRequest,
)
from app.services.teacher_service import (
    add_student_to_teacher_class,
    create_teacher_class,
    create_teacher_document,
    create_teacher_exam,
    delete_teacher_document,
    delete_teacher_exam,
    get_teacher_exam_detail,
    list_teacher_class_students,
    list_teacher_classes,
    list_teacher_documents,
    list_teacher_exams,
    list_teacher_students,
    set_teacher_exam_visibility,
    update_teacher_document,
    update_teacher_exam,
)

router = APIRouter(prefix="/teacher", tags=["Teacher"])


@router.get("/classes", response_model=TeacherClassListResponse)
def get_teacher_classes(
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherClassListResponse:
    return list_teacher_classes(db, current_teacher)


@router.post("/classes", response_model=TeacherClassResponse)
def post_teacher_class(
    payload: CreateTeacherClassRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherClassResponse:
    return create_teacher_class(
        db,
        current_teacher,
        payload.name,
        payload.description,
        payload.join_code,
    )


@router.get("/students", response_model=TeacherStudentListResponse)
def get_teacher_students(
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherStudentListResponse:
    return list_teacher_students(db, current_teacher)


@router.get("/classes/{class_id}/students", response_model=TeacherStudentListResponse)
def get_teacher_class_students(
    class_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherStudentListResponse:
    return list_teacher_class_students(db, current_teacher, class_id)


@router.post("/classes/{class_id}/students", response_model=TeacherStudentResponse)
def post_teacher_class_student(
    class_id: int,
    payload: AddTeacherStudentRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherStudentResponse:
    return add_student_to_teacher_class(db, current_teacher, class_id, payload.student_id)


@router.get("/system/documents", response_model=TeacherDocumentListResponse)
def get_teacher_system_documents(
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherDocumentListResponse:
    return list_teacher_documents(db, current_teacher, "system", None)


@router.get("/classes/{class_id}/documents", response_model=TeacherDocumentListResponse)
def get_teacher_class_documents(
    class_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherDocumentListResponse:
    return list_teacher_documents(db, current_teacher, "class", class_id)


@router.post("/documents", response_model=TeacherDocumentResponse)
def post_teacher_document(
    payload: CreateTeacherDocumentRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherDocumentResponse:
    return create_teacher_document(
        db,
        current_teacher,
        payload.title,
        payload.summary,
        payload.content,
        payload.scope,
        payload.classroom_id,
        payload.is_published,
    )


@router.put("/documents/{document_id}", response_model=TeacherDocumentResponse)
def put_teacher_document(
    document_id: int,
    payload: UpdateTeacherDocumentRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherDocumentResponse:
    return update_teacher_document(
        db,
        current_teacher,
        document_id,
        payload.title,
        payload.summary,
        payload.content,
        payload.scope,
        payload.classroom_id,
        payload.is_published,
    )


@router.delete("/documents/{document_id}", response_model=MessageResponse)
def delete_teacher_document_route(
    document_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> MessageResponse:
    return delete_teacher_document(db, current_teacher, document_id)


@router.get("/system/exams", response_model=TeacherExamListResponse)
def get_teacher_system_exams(
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamListResponse:
    return list_teacher_exams(db, current_teacher, "system", None)


@router.get("/classes/{class_id}/exams", response_model=TeacherExamListResponse)
def get_teacher_class_exams(
    class_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamListResponse:
    return list_teacher_exams(db, current_teacher, "class", class_id)


@router.get("/exams/{exam_id}", response_model=TeacherExamDetailSchema)
def get_teacher_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamDetailSchema:
    return get_teacher_exam_detail(db, current_teacher, exam_id)


@router.post("/system/exams", response_model=TeacherExamResponse)
def post_teacher_system_exam(
    payload: CreateTeacherExamRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamResponse:
    return create_teacher_exam(
        db,
        current_teacher,
        payload.title,
        payload.description,
        "system",
        None,
        payload.duration_minutes,
        payload.is_active,
        [question.model_dump() for question in payload.questions],
    )


@router.post("/classes/{class_id}/exams", response_model=TeacherExamResponse)
def post_teacher_class_exam(
    class_id: int,
    payload: CreateTeacherExamRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamResponse:
    return create_teacher_exam(
        db,
        current_teacher,
        payload.title,
        payload.description,
        "class",
        class_id,
        payload.duration_minutes,
        payload.is_active,
        [question.model_dump() for question in payload.questions],
    )


@router.put("/exams/{exam_id}", response_model=TeacherExamResponse)
def put_teacher_exam(
    exam_id: int,
    payload: UpdateTeacherExamRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamResponse:
    questions = [question.model_dump() for question in payload.questions] if payload.questions is not None else None
    return update_teacher_exam(
        db,
        current_teacher,
        exam_id,
        payload.title,
        payload.description,
        payload.scope,
        payload.classroom_id,
        payload.duration_minutes,
        payload.is_active,
        questions,
    )


@router.delete("/exams/{exam_id}", response_model=MessageResponse)
def delete_teacher_exam_route(
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> MessageResponse:
    return delete_teacher_exam(db, current_teacher, exam_id)


@router.post("/exams/{exam_id}/publish", response_model=TeacherExamResponse)
def publish_teacher_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamResponse:
    return set_teacher_exam_visibility(db, current_teacher, exam_id, True)


@router.post("/exams/{exam_id}/private", response_model=TeacherExamResponse)
def private_teacher_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamResponse:
    return set_teacher_exam_visibility(db, current_teacher, exam_id, False)
