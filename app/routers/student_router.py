from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_student
from app.schemas.student import (
    AttemptResultResponse,
    JoinClassRequest,
    JoinClassResponse,
    SaveAttemptAnswersRequest,
    SaveAttemptAnswersResponse,
    StartAttemptResponse,
    StudentClassListResponse,
    StudentDocumentListResponse,
    StudentExamDetailSchema,
    StudentExamListResponse,
    SubmitAttemptResponse,
)
from app.services.student_service import (
    get_student_attempt_result,
    get_student_exam_detail,
    join_student_class,
    list_student_classes,
    list_student_documents,
    list_student_exams,
    save_student_attempt_answers,
    start_student_exam_attempt,
    submit_student_attempt,
)

router = APIRouter(prefix="/student", tags=["Student"])


@router.get("/classes", response_model=StudentClassListResponse)
def get_student_classes(
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentClassListResponse:
    return list_student_classes(db, current_student)


@router.post("/classes/join", response_model=JoinClassResponse)
def post_join_class(
    payload: JoinClassRequest,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> JoinClassResponse:
    return join_student_class(db, current_student, payload.join_code)


@router.get("/system/documents", response_model=StudentDocumentListResponse)
def get_system_documents(
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentDocumentListResponse:
    return list_student_documents(db, current_student, "system", None)


@router.get("/classes/{class_id}/documents", response_model=StudentDocumentListResponse)
def get_class_documents(
    class_id: int,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentDocumentListResponse:
    return list_student_documents(db, current_student, "class", class_id)


@router.get("/system/exams", response_model=StudentExamListResponse)
def get_system_exams(
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentExamListResponse:
    return list_student_exams(db, current_student, "system", None)


@router.get("/classes/{class_id}/exams", response_model=StudentExamListResponse)
def get_class_exams(
    class_id: int,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentExamListResponse:
    return list_student_exams(db, current_student, "class", class_id)


@router.get("/exams/{exam_id}", response_model=StudentExamDetailSchema)
def get_exam_detail(
    exam_id: int,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentExamDetailSchema:
    return get_student_exam_detail(db, current_student, exam_id)


@router.post("/exams/{exam_id}/attempts", response_model=StartAttemptResponse)
def post_start_attempt(
    exam_id: int,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StartAttemptResponse:
    return start_student_exam_attempt(db, current_student, exam_id)


@router.put("/attempts/{attempt_id}/answers", response_model=SaveAttemptAnswersResponse)
def put_attempt_answers(
    attempt_id: int,
    payload: SaveAttemptAnswersRequest,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> SaveAttemptAnswersResponse:
    serialized_answers = [answer.model_dump() for answer in payload.answers]
    return save_student_attempt_answers(db, current_student, attempt_id, serialized_answers)


@router.post("/attempts/{attempt_id}/submit", response_model=SubmitAttemptResponse)
def post_submit_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> SubmitAttemptResponse:
    return submit_student_attempt(db, current_student, attempt_id)


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResultResponse)
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> AttemptResultResponse:
    return get_student_attempt_result(db, current_student, attempt_id)
