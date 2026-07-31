from fastapi import APIRouter, Depends, Query
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
    StudentActivityChartResponse,
    StudentClassListResponse,
    StudentDashboardClassSchema,
    StudentDashboardMetricsResponse,
    StudentDocumentListResponse,
    StudentExamDetailSchema,
    StudentExamListResponse,
    StudentExamResultListResponse,
    StudentInProgressResponse,
    StudentRecentActivitySchema,
    StudentRecommendedExamSchema,
    StudentSubjectProgressSchema,
    SubmitAttemptResponse,
)
from app.services.student_service import (
    get_student_activity_chart,
    get_student_attempt_result,
    get_student_dashboard_classes,
    get_student_dashboard_metrics,
    get_student_exam_detail,
    get_student_in_progress,
    get_student_recent_activities,
    get_student_recommended_exams,
    get_student_subject_progress,
    join_student_class,
    list_student_classes,
    list_student_documents,
    list_student_exams,
    list_student_exam_results,
    save_student_attempt_answers,
    start_student_exam_attempt,
    submit_student_attempt,
)

router = APIRouter(prefix="/student", tags=["Student"])


@router.get("/dashboard/in-progress", response_model=StudentInProgressResponse | None)
def get_dashboard_in_progress(
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
):
    return get_student_in_progress(db, current_student)


@router.get("/dashboard/metrics", response_model=StudentDashboardMetricsResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentDashboardMetricsResponse:
    return get_student_dashboard_metrics(db, current_student)


@router.get("/dashboard/activity-chart", response_model=StudentActivityChartResponse)
def get_dashboard_activity_chart(
    start_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentActivityChartResponse:
    return get_student_activity_chart(db, current_student, start_date)


@router.get("/dashboard/subject-progress", response_model=list[StudentSubjectProgressSchema])
def get_dashboard_subject_progress(
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
):
    return get_student_subject_progress(db, current_student)


@router.get("/dashboard/classes", response_model=list[StudentDashboardClassSchema])
def get_dashboard_classes(
    limit: int = Query(default=6, ge=1, le=50),
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
):
    return get_student_dashboard_classes(db, current_student, limit)


@router.get("/dashboard/recommended-exams", response_model=list[StudentRecommendedExamSchema])
def get_dashboard_recommended_exams(
    limit: int = Query(default=3, ge=1, le=50),
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
):
    return get_student_recommended_exams(db, current_student, limit)


@router.get("/dashboard/recent-activities", response_model=list[StudentRecentActivitySchema])
def get_dashboard_recent_activities(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
):
    return get_student_recent_activities(db, current_student, limit)



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
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentExamListResponse:
    return list_student_exams(db, current_student, "system", None, limit, offset)


@router.get("/classes/{class_id}/exams", response_model=StudentExamListResponse)
def get_class_exams(
    class_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentExamListResponse:
    return list_student_exams(db, current_student, "class", class_id, limit, offset)


@router.get("/results", response_model=StudentExamResultListResponse)
def get_exam_results(
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentExamResultListResponse:
    return list_student_exam_results(db, current_student)


@router.get("/system/results", response_model=StudentExamResultListResponse)
def get_system_exam_results(
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentExamResultListResponse:
    return list_student_exam_results(db, current_student, "system", None)


@router.get("/classes/{class_id}/results", response_model=StudentExamResultListResponse)
def get_class_exam_results(
    class_id: int,
    db: Session = Depends(get_db),
    current_student=Depends(get_current_student),
) -> StudentExamResultListResponse:
    return list_student_exam_results(db, current_student, "class", class_id)


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
