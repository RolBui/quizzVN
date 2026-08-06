from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_teacher
from app.schemas.common import MessageResponse
from app.schemas.teacher import (
    AddTeacherStudentRequest,
    AssignTeacherExamRequest,
    CreateTeacherClassRequest,
    CreateTeacherExamRequest,
    TeacherAssignmentType,
    TeacherClassListResponse,
    TeacherClassResponse,
    TeacherDocumentListResponse,
    TeacherDocumentResponse,
    TeacherExamAttemptResultResponse,
    TeacherExamDetailSchema,
    TeacherExamListResponse,
    TeacherExamResultListResponse,
    TeacherExamResponse,
    TeacherImageListResponse,
    TeacherImageUploadResponse,
    TeacherStudentListResponse,
    TeacherStudentResponse,
    UpdateTeacherClassRequest,
    UpdateTeacherClassExamRequest,
    UpdateTeacherExamRequest,
    TeacherExploreSort,
)
from app.services.media_service import delete_uploaded_image, list_uploaded_images, save_exam_image
from app.services.teacher_service import (
    add_student_to_teacher_class,
    assign_teacher_exam,
    create_teacher_class,
    create_teacher_exam,
    create_teacher_uploaded_document,
    delete_teacher_class,
    delete_teacher_class_document,
    delete_teacher_document,
    delete_teacher_exam,
    get_teacher_class_exam_detail,
    get_teacher_class_exam_attempt_result,
    list_teacher_class_exam_results,
    get_teacher_exam_detail,
    list_teacher_all_documents,
    list_teacher_class_students,
    list_teacher_classes,
    list_teacher_documents,
    list_teacher_exams,
    list_teacher_students,
    remove_student_from_teacher_class,
    set_teacher_exam_visibility,
    update_teacher_class,
    update_teacher_class_exam,
    update_teacher_exam,
    explore_teacher_exams,
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


@router.put("/classes/{class_id}", response_model=TeacherClassResponse)
def put_teacher_class(
    class_id: int,
    payload: UpdateTeacherClassRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherClassResponse:
    return update_teacher_class(
        db,
        current_teacher,
        class_id,
        payload.name,
        payload.description,
        payload.join_code,
    )


@router.delete("/classes/{class_id}", response_model=MessageResponse)
def delete_teacher_class_route(
    class_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> MessageResponse:
    return delete_teacher_class(db, current_teacher, class_id)


@router.get("/image", response_model=TeacherImageListResponse)
def get_teacher_images(
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherImageListResponse:
    items = list_uploaded_images(db, current_teacher.id, category="exam")
    return {"items": items}


@router.post("/image", response_model=TeacherImageUploadResponse)
def post_teacher_image(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherImageUploadResponse:
    return {
        "message": "Image uploaded successfully",
        "image": save_exam_image(db, current_teacher.id, image),
    }


@router.delete("/image/{image_id}", response_model=MessageResponse)
def delete_teacher_image_route(
    image_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> MessageResponse:
    delete_uploaded_image(db, current_teacher.id, image_id)
    return {"message": "Image deleted successfully"}


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


@router.delete("/classes/{class_id}/students/{student_id}", response_model=MessageResponse)
def delete_teacher_class_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> MessageResponse:
    return remove_student_from_teacher_class(db, current_teacher, class_id, student_id)


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


@router.post("/classes/{class_id}/documents", response_model=TeacherDocumentResponse)
def post_teacher_class_document(
    class_id: int,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    summary: str | None = Form(None),
    is_published: bool = Form(False),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherDocumentResponse:
    return create_teacher_uploaded_document(
        db,
        current_teacher,
        title,
        summary,
        file,
        "class",
        class_id,
        is_published,
    )


@router.delete("/classes/{class_id}/documents/{document_id}", response_model=MessageResponse)
def delete_teacher_class_document_route(
    class_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> MessageResponse:
    return delete_teacher_class_document(db, current_teacher, class_id, document_id)


@router.get("/documents", response_model=TeacherDocumentListResponse)
def get_teacher_documents(
    scope: str = Query("all"),
    classroom_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherDocumentListResponse:
    normalized_scope = scope.strip().lower()
    if normalized_scope == "all":
        if classroom_id is not None:
            raise HTTPException(status_code=400, detail="classroom_id is only allowed when scope=class")
        return list_teacher_all_documents(db, current_teacher)

    return list_teacher_documents(db, current_teacher, normalized_scope, classroom_id)


@router.post("/documents", response_model=TeacherDocumentResponse)
def post_teacher_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    summary: str | None = Form(None),
    scope: str = Form("system"),
    classroom_id: int | None = Form(None),
    is_published: bool = Form(False),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherDocumentResponse:
    return create_teacher_uploaded_document(
        db,
        current_teacher,
        title,
        summary,
        file,
        scope,
        classroom_id,
        is_published,
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
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    assignment_type: TeacherAssignmentType | None = Query(default=None),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamListResponse:
    return list_teacher_exams(db, current_teacher, "system", None, limit, offset, assignment_type)


@router.get("/exams/explore", response_model=TeacherExamListResponse)
def get_explore_teacher_exams(
    search: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    assignment_type: TeacherAssignmentType | None = Query(default=None),
    sort: TeacherExploreSort = Query(default="newest"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamListResponse:
    return explore_teacher_exams(
        db=db,
        teacher=current_teacher,
        search=search,
        grade=grade,
        assignment_type=assignment_type,
        sort=sort,
        limit=limit,
        offset=offset,
    )



@router.get("/classes/{class_id}/exams", response_model=TeacherExamListResponse)
def get_teacher_class_exams(
    class_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    assignment_type: TeacherAssignmentType | None = Query(default=None),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamListResponse:
    return list_teacher_exams(db, current_teacher, "class", class_id, limit, offset, assignment_type)


@router.get("/classes/{class_id}/exams/{exam_id}", response_model=TeacherExamDetailSchema)
def get_teacher_class_exam(
    class_id: int,
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamDetailSchema:
    return get_teacher_class_exam_detail(db, current_teacher, class_id, exam_id)


@router.get("/classes/{class_id}/exams/{exam_id}/results", response_model=TeacherExamResultListResponse)
def get_teacher_class_exam_results(
    class_id: int,
    exam_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamResultListResponse:
    return list_teacher_class_exam_results(db, current_teacher, class_id, exam_id)


@router.get(
    "/classes/{class_id}/exams/{exam_id}/attempts/{attempt_id}",
    response_model=TeacherExamAttemptResultResponse,
)
def get_teacher_class_exam_attempt(
    class_id: int,
    exam_id: int,
    attempt_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamAttemptResultResponse:
    return get_teacher_class_exam_attempt_result(
        db,
        current_teacher,
        class_id,
        exam_id,
        attempt_id,
    )


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
        payload.grade,
        payload.image_url,
        "system",
        None,
        payload.duration_minutes,
        payload.start_time,
        payload.end_time,
        payload.is_published,
        payload.is_active,
        [question.model_dump() for question in payload.questions],
        payload.total_points,
        payload.point_mode,
        payload.assignment_type,
        payload.max_attempts,
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
        payload.grade,
        payload.image_url,
        "class",
        class_id,
        payload.duration_minutes,
        payload.start_time,
        payload.end_time,
        payload.is_published,
        payload.is_active,
        [question.model_dump() for question in payload.questions],
        payload.total_points,
        payload.point_mode,
        payload.assignment_type,
        payload.max_attempts,
    )


@router.put("/classes/{class_id}/exams/{exam_id}", response_model=TeacherExamResponse)
def put_teacher_class_exam(
    class_id: int,
    exam_id: int,
    payload: UpdateTeacherClassExamRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamResponse:
    questions = [question.model_dump() for question in payload.questions] if payload.questions is not None else None
    return update_teacher_class_exam(
        db,
        current_teacher,
        class_id,
        exam_id,
        payload.title,
        payload.description,
        payload.grade,
        payload.image_url,
        payload.duration_minutes,
        payload.start_time,
        payload.end_time,
        "start_time" in payload.model_fields_set,
        "end_time" in payload.model_fields_set,
        payload.is_published,
        payload.is_active,
        questions,
        payload.total_points,
        payload.point_mode,
        payload.assignment_type,
        payload.max_attempts,
        "assignment_type" in payload.model_fields_set,
        "max_attempts" in payload.model_fields_set,
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
        payload.grade,
        payload.image_url,
        payload.scope,
        payload.classroom_id,
        payload.duration_minutes,
        payload.start_time,
        payload.end_time,
        "start_time" in payload.model_fields_set,
        "end_time" in payload.model_fields_set,
        payload.is_published,
        payload.is_active,
        questions,
        payload.total_points,
        payload.point_mode,
        payload.assignment_type,
        payload.max_attempts,
        "assignment_type" in payload.model_fields_set,
        "max_attempts" in payload.model_fields_set,
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


@router.post("/exams/{exam_id}/assign", response_model=TeacherExamResponse)
def assign_teacher_exam_route(
    exam_id: int,
    payload: AssignTeacherExamRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> TeacherExamResponse:
    return assign_teacher_exam(
        db,
        current_teacher,
        exam_id,
        payload.classroom_id,
        payload.assignment_type,
        payload.start_time,
        payload.end_time,
        payload.duration_minutes,
        payload.max_attempts,
        payload.is_published,
        payload.duplicate,
    )

