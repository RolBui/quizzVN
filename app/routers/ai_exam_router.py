from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_teacher
from app.schemas.ai_exam import (
    AIExamGenerationJobResponse,
    AIQuestionDraftResponse,
    GenerateExamRequest,
    GenerateMoreQuestionsRequest,
    SaveAIExamToQuizRequest,
    SaveAIExamToQuizResponse,
    UpdateAIQuestionDraftRequest,
)
from app.services.ai_exam_service import (
    AIExamGenerationError,
    create_ai_exam_generation_job,
    get_teacher_ai_exam_job,
    run_ai_exam_generation_job,
    run_more_questions_job,
    save_ai_exam_job_to_quiz,
    serialize_ai_exam_job,
    serialize_question_draft,
    start_more_questions_for_teacher,
    update_teacher_question_draft,
)

router = APIRouter(prefix="/api/ai-exams", tags=["AI Exams"])


@router.post("/generate", response_model=AIExamGenerationJobResponse, include_in_schema=False)
@router.post("/generate/", response_model=AIExamGenerationJobResponse)
def post_generate_ai_exam(
    payload: GenerateExamRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> AIExamGenerationJobResponse:
    job = create_ai_exam_generation_job(
        db,
        current_teacher,
        payload.model_dump(),
    )
    background_tasks.add_task(run_ai_exam_generation_job, job.id)

    return serialize_ai_exam_job(job)


@router.post("/jobs/{job_id}/generate-more", response_model=AIExamGenerationJobResponse, include_in_schema=False)
@router.post("/jobs/{job_id}/generate-more/", response_model=AIExamGenerationJobResponse)
def post_generate_more_questions(
    job_id: int,
    payload: GenerateMoreQuestionsRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> AIExamGenerationJobResponse:
    job, request_data = start_more_questions_for_teacher(
        db,
        current_teacher,
        job_id,
        payload.model_dump(),
    )
    background_tasks.add_task(run_more_questions_job, job.id, request_data)
    return serialize_ai_exam_job(job)


@router.get("/jobs/{job_id}", response_model=AIExamGenerationJobResponse, include_in_schema=False)
@router.get("/jobs/{job_id}/", response_model=AIExamGenerationJobResponse)
def get_ai_exam_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> AIExamGenerationJobResponse:
    job = get_teacher_ai_exam_job(db, current_teacher, job_id)
    return serialize_ai_exam_job(job)


@router.post("/jobs/{job_id}/save-to-quiz", response_model=SaveAIExamToQuizResponse, include_in_schema=False)
@router.post("/jobs/{job_id}/save-to-quiz/", response_model=SaveAIExamToQuizResponse)
def post_save_ai_exam_to_quiz(
    job_id: int,
    payload: SaveAIExamToQuizRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> SaveAIExamToQuizResponse:
    return save_ai_exam_job_to_quiz(
        db,
        current_teacher,
        job_id,
        payload.model_dump(),
    )


@router.patch("/question-drafts/{draft_id}", response_model=AIQuestionDraftResponse, include_in_schema=False)
@router.patch("/question-drafts/{draft_id}/", response_model=AIQuestionDraftResponse)
def patch_question_draft(
    draft_id: int,
    payload: UpdateAIQuestionDraftRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> AIQuestionDraftResponse | JSONResponse:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        draft = update_teacher_question_draft(db, current_teacher, draft_id, data)
    except AIExamGenerationError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "AI question draft validation failed.",
                "errors": exc.errors,
            },
        )

    return serialize_question_draft(draft)
