import json
import re
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import utc_now
from app.database import SessionLocal, engine
from app.models.ai_exam import AIExamGenerationJob, AIQuestionDraft
# Loads the referenced table for AIExamGenerationJob.quiz_id during bootstrap.
from app.models.exam import Exam
from app.models.user import User
from app.services.ai_exam_prompt_builder import (
    build_exam_batch_generation_prompt,
    build_exam_generation_prompt,
    build_exam_repair_prompt,
    build_more_questions_prompt,
)
from app.services.ai_exam_validator import (
    build_question_payload_from_draft,
    sanitize_ai_exam_payload,
    sanitize_ai_text,
    validate_ai_exam_payload,
    validate_ai_question_payload,
)
from app.services.ai_provider_client import AIProviderClient, AIProviderError, AIProviderResult
from app.services.gemini_client import GeminiAIProviderClient
from app.services.billing_service import (
    get_ai_usage_by_operation_key,
    grant_teacher_welcome_qc,
    refund_ai_qc_usage,
    reserve_ai_qc,
    settle_ai_qc_usage,
)
from app.services.teacher_service import create_teacher_exam


TEACHER_QUESTION_TYPE_SINGLE_CHOICE = "single_choice"
TEACHER_QUESTION_TYPE_TRUE_FALSE = "true_false"
TEACHER_QUESTION_TYPE_SHORT_ANSWER = "short_answer"
TEACHER_QUESTION_TYPE_TEXT = "text"
OPTION_KEYS = ("A", "B", "C", "D")


class AIExamGenerationError(RuntimeError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("AI exam generation failed")
        self.errors = errors


class MockAIProviderClient(AIProviderClient):
    def generate_exam(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
    ) -> AIProviderResult:
        question_count = _extract_int_from_prompt(prompt, "Number of questions", 3)
        subject = _extract_text_from_prompt(prompt, "Subject", "Tin hoc")
        grade = _extract_text_from_prompt(prompt, "Grade", "10")
        topic = _extract_text_from_prompt(prompt, "Topic", "Python co ban")
        duration_minutes = _extract_int_from_prompt(prompt, "Duration", 15)
        question_types = _extract_question_types_from_prompt(prompt)
        question_type_sequence = _extract_question_type_sequence_from_prompt(
            prompt,
            question_types,
            question_count,
        )

        payload = {
            "title": f"Mock exam draft for {topic}",
            "description": "Local mock draft generated without calling an AI provider.",
            "subject": subject,
            "grade": grade,
            "duration_minutes": duration_minutes,
            "total_points": question_count,
            "questions": [
                _build_mock_question(index, topic, question_type_sequence[index])
                for index in range(question_count)
            ],
        }
        return AIProviderResult(payload=payload, raw_response=payload)


def bootstrap_ai_exam_storage() -> None:
    AIExamGenerationJob.__table__.create(bind=engine, checkfirst=True)
    AIQuestionDraft.__table__.create(bind=engine, checkfirst=True)
    _ensure_ai_exam_generation_job_columns()


def _ensure_ai_exam_generation_job_columns() -> None:
    if engine.dialect.name == "postgresql":
        statement = """
            ALTER TABLE ai_exam_generation_jobs
            ADD COLUMN IF NOT EXISTS question_type_distribution JSONB NOT NULL DEFAULT '{}'::jsonb;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS qc_reserved INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS qc_charged INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS qc_refunded INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS free_questions_used INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS qc_status VARCHAR(30) NOT NULL DEFAULT 'none';
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_dispatch_id VARCHAR(64);
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_job_id VARCHAR(64);
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_operation VARCHAR(30);
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_request_data JSONB;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_prompt TEXT;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_result_status VARCHAR(30) NOT NULL DEFAULT 'none';
            CREATE UNIQUE INDEX IF NOT EXISTS ix_ai_exam_generation_jobs_agent_dispatch_id
            ON ai_exam_generation_jobs (agent_dispatch_id)
            WHERE agent_dispatch_id IS NOT NULL;
            CREATE INDEX IF NOT EXISTS ix_ai_exam_generation_jobs_agent_job_id
            ON ai_exam_generation_jobs (agent_job_id);
            UPDATE ai_exam_generation_jobs
            SET question_type_distribution = '{}'::jsonb
            WHERE question_type_distribution IS NULL;
        """
    else:
        statement = """
            ALTER TABLE ai_exam_generation_jobs
            ADD COLUMN IF NOT EXISTS question_type_distribution JSON NOT NULL DEFAULT '{}';
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS qc_reserved INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS qc_charged INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS qc_refunded INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS free_questions_used INTEGER NOT NULL DEFAULT 0;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS qc_status VARCHAR(30) NOT NULL DEFAULT 'none';
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_dispatch_id VARCHAR(64);
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_job_id VARCHAR(64);
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_operation VARCHAR(30);
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_request_data JSON;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_prompt TEXT;
            ALTER TABLE ai_exam_generation_jobs ADD COLUMN IF NOT EXISTS agent_result_status VARCHAR(30) NOT NULL DEFAULT 'none';
            CREATE UNIQUE INDEX IF NOT EXISTS ix_ai_exam_generation_jobs_agent_dispatch_id
            ON ai_exam_generation_jobs (agent_dispatch_id);
            CREATE INDEX IF NOT EXISTS ix_ai_exam_generation_jobs_agent_job_id
            ON ai_exam_generation_jobs (agent_job_id);
            UPDATE ai_exam_generation_jobs
            SET question_type_distribution = '{}'
            WHERE question_type_distribution IS NULL;
        """

    with engine.begin() as connection:
        connection.execute(text(statement))


def _ai_operation_key(
    teacher_id: int,
    operation: str,
    idempotency_key: str | None,
) -> str:
    token = (idempotency_key or uuid4().hex).strip()
    if not token or len(token) > 100:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency-Key phải có từ 1 đến 100 ký tự.",
        )
    return f"ai:{operation}:{teacher_id}:{token}"


def create_ai_exam_generation_job(
    db: Session,
    teacher: User,
    request_data: dict[str, Any],
    idempotency_key: str | None = None,
) -> tuple[AIExamGenerationJob, bool]:
    grant_teacher_welcome_qc(db, teacher)
    operation_key = _ai_operation_key(
        teacher.id,
        "initial",
        idempotency_key,
    )
    db.query(User).filter(User.id == teacher.id).with_for_update().one()
    existing_usage = get_ai_usage_by_operation_key(db, teacher.id, operation_key)
    if existing_usage:
        existing_job = get_teacher_ai_exam_job(
            db,
            teacher,
            existing_usage.ai_job_id,
        )
        return existing_job, False

    provider_name = settings.AI_PROVIDER
    model_name = "mock" if provider_name == "mock" else settings.AI_MODEL

    prompt = build_exam_generation_prompt(request_data)
    job = AIExamGenerationJob(
        teacher_id=teacher.id,
        subject=request_data["subject"],
        grade=request_data["grade"],
        topic=request_data["topic"],
        duration_minutes=request_data["duration_minutes"],
        question_count=request_data["question_count"],
        question_types=request_data["question_types"],
        question_type_distribution=request_data["question_type_distribution"],
        difficulty_distribution=request_data["difficulty_distribution"],
        language=request_data["language"],
        additional_instructions=request_data.get("additional_instructions") or "",
        status="running",
        prompt=prompt,
        provider=provider_name,
        model=model_name,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(job)
    db.flush()
    reserve_ai_qc(
        db,
        teacher,
        job,
        operation_key=operation_key,
        operation_type="initial",
        question_count=int(request_data["question_count"]),
    )
    db.commit()
    db.refresh(job)
    return job, True


def generate_exam_for_teacher(
    db: Session,
    teacher: User,
    request_data: dict[str, Any],
) -> AIExamGenerationJob:
    job, _ = create_ai_exam_generation_job(db, teacher, request_data)
    try:
        _process_ai_exam_job(db, job, request_data)
    except AIExamGenerationError:
        refund_ai_qc_usage(db, job.id, "initial")
        raise
    settle_ai_qc_usage(db, job.id, "initial")
    return get_teacher_ai_exam_job(db, teacher, job.id)


def run_ai_exam_generation_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
        if not job or job.status not in {"running", "queued"}:
            return
        job.status = "running"
        db.commit()
        _process_ai_exam_job(db, job, _build_request_data_from_job(job))
        settle_ai_qc_usage(db, job.id, "initial")
    except AIExamGenerationError:
        refund_ai_qc_usage(db, job_id, "initial")
        return
    finally:
        db.close()


def start_more_questions_for_teacher(
    db: Session,
    teacher: User,
    job_id: int,
    data: dict[str, Any],
    idempotency_key: str | None = None,
) -> tuple[AIExamGenerationJob, dict[str, Any] | None, bool]:
    grant_teacher_welcome_qc(db, teacher)
    job = get_teacher_ai_exam_job(db, teacher, job_id)
    operation_key = _ai_operation_key(
        teacher.id,
        f"generate-more:{job_id}",
        idempotency_key,
    )
    db.query(User).filter(User.id == teacher.id).with_for_update().one()
    existing_usage = get_ai_usage_by_operation_key(db, teacher.id, operation_key)
    if existing_usage:
        return job, None, False
    if job.status in {"running", "queued", "generating_more"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI exam job is already generating questions",
        )

    if job.status == "converted" and job.quiz_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Converted AI exam jobs cannot generate more questions",
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed AI exam jobs can generate more questions",
        )

    request_data = _build_more_request_data(job, data)
    job.status = "generating_more"
    job.error_message = ""
    job.updated_at = utc_now()
    reserve_ai_qc(
        db,
        teacher,
        job,
        operation_key=operation_key,
        operation_type="generate_more",
        question_count=int(request_data["question_count"]),
    )
    db.commit()
    db.refresh(job)
    return job, request_data, True


def run_more_questions_job(job_id: int, request_data: dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
        if not job or job.status != "generating_more":
            return
        _process_more_questions_job(db, job, request_data)
        settle_ai_qc_usage(db, job.id, "generate_more")
    except AIExamGenerationError:
        refund_ai_qc_usage(db, job_id, "generate_more")
        return
    finally:
        db.close()


def prepare_ai_agent_dispatch(
    db: Session,
    job_id: int,
    operation: str,
    request_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    job = (
        db.query(AIExamGenerationJob)
        .filter(AIExamGenerationJob.id == job_id)
        .with_for_update()
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI exam job not found")
    if operation not in {"initial", "generate_more"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported AI operation")

    normalized_request = dict(request_data or _build_request_data_from_job(job))
    if operation == "generate_more":
        existing_questions = _build_existing_question_context(db, job.id)
        prompt = build_more_questions_prompt(normalized_request, existing_questions)
    else:
        prompt = job.prompt

    dispatch_id = uuid4().hex
    job.agent_dispatch_id = dispatch_id
    job.agent_job_id = None
    job.agent_operation = operation
    job.agent_request_data = normalized_request
    job.agent_prompt = prompt
    job.agent_result_status = "pending"
    job.status = "queued"
    job.error_message = ""
    job.updated_at = utc_now()
    db.commit()

    return {
        "dispatch_id": dispatch_id,
        "external_job_id": str(job.id),
        "operation": operation,
        "prompt": prompt,
        "request_data": normalized_request,
    }


def register_ai_agent_job(db: Session, job_id: int, dispatch_id: str, agent_job_id: str) -> None:
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job or job.agent_dispatch_id != dispatch_id:
        return
    job.agent_job_id = agent_job_id
    job.updated_at = utc_now()
    db.commit()


def restore_local_ai_execution(db: Session, job_id: int, operation: str) -> None:
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job:
        return
    job.status = "running" if operation == "initial" else "generating_more"
    job.agent_result_status = "fallback_local"
    job.updated_at = utc_now()
    db.commit()


def fail_ai_agent_job(
    db: Session,
    job_id: int,
    dispatch_id: str,
    operation: str,
    errors: list[str],
) -> AIExamGenerationJob:
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI exam job not found")
    if job.agent_dispatch_id != dispatch_id or job.agent_operation != operation:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale AI Agent callback")
    if job.agent_result_status in {"completed", "failed"}:
        return job

    if operation == "initial":
        _mark_job_failed(db, job.id, errors)
    else:
        _mark_more_questions_failed(db, job.id, errors)
    refund_ai_qc_usage(db, job.id, operation)

    job = db.get(AIExamGenerationJob, job_id)
    job.agent_result_status = "failed"
    job.updated_at = utc_now()
    db.commit()
    return job


def complete_ai_agent_job(
    db: Session,
    job_id: int,
    dispatch_id: str,
    operation: str,
    payload: dict[str, Any],
    raw_response: dict[str, Any] | str,
    provider: str,
    model: str,
) -> AIExamGenerationJob:
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI exam job not found")
    if job.agent_dispatch_id != dispatch_id or job.agent_operation != operation:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale AI Agent callback")
    if job.agent_result_status == "completed":
        return job
    if job.agent_result_status == "failed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI Agent job already failed")

    request_data = dict(job.agent_request_data or {})
    if not request_data:
        return fail_ai_agent_job(
            db,
            job_id,
            dispatch_id,
            operation,
            ["AI Agent request context is missing"],
        )

    # A callback can be retried after the result was saved but before QC settlement.
    already_applied = job.status == "completed"
    if not already_applied:
        sanitized_payload = sanitize_ai_exam_payload(payload)
        if operation == "initial":
            errors = _validate_generated_ai_exam_payload(
                db,
                job.id,
                sanitized_payload,
                request_data,
                False,
            )
        else:
            errors = _validate_more_questions_payload(db, job.id, sanitized_payload, request_data)

        if errors:
            return fail_ai_agent_job(db, job_id, dispatch_id, operation, errors)

        result = AIProviderResult(payload=sanitized_payload, raw_response=raw_response)
        if operation == "initial":
            _save_completed_job(db, job, result)
        else:
            _append_questions_to_job(db, job, result)

    settle_ai_qc_usage(db, job_id, operation)
    job = db.get(AIExamGenerationJob, job_id)
    job.provider = provider or job.provider
    job.model = model or job.model
    job.agent_result_status = "completed"
    job.updated_at = utc_now()
    db.commit()
    return job


def _process_ai_exam_job(
    db: Session,
    job: AIExamGenerationJob,
    request_data: dict[str, Any],
) -> None:
    try:
        provider = _get_ai_provider_client()
        batch_size = _get_ai_exam_batch_size()
        if int(request_data["question_count"]) > batch_size:
            _process_ai_exam_job_in_batches(db, job, request_data, provider, batch_size)
            return

        result = _generate_valid_ai_exam_result(provider, job.prompt, request_data)
        _save_completed_job(db, job, result)
    except AIExamGenerationError as exc:
        _mark_job_failed(db, job.id, exc.errors)
        raise
    except AIProviderError as exc:
        errors = [str(exc)]
        _mark_job_failed(db, job.id, errors)
        raise AIExamGenerationError(errors) from exc
    except Exception as exc:
        errors = ["Unexpected AI exam generation error"]
        _mark_job_failed(db, job.id, errors)
        raise AIExamGenerationError(errors) from exc


def _process_ai_exam_job_in_batches(
    db: Session,
    job: AIExamGenerationJob,
    request_data: dict[str, Any],
    provider: AIProviderClient,
    batch_size: int,
) -> None:
    question_type_batches = _build_question_type_distribution_batches(
        request_data.get("question_type_distribution") or {},
        list(request_data.get("question_types") or []),
        batch_size,
    )
    if not question_type_batches:
        raise AIExamGenerationError(["Unable to split AI exam into batches"])

    difficulty_batches = _build_difficulty_distribution_batches(request_data, question_type_batches)
    raw_batches: list[dict[str, Any]] = []
    batch_count = len(question_type_batches)

    for batch_index, type_distribution in enumerate(question_type_batches, start=1):
        batch_data = _build_batch_request_data(
            request_data,
            type_distribution,
            difficulty_batches[batch_index - 1],
        )
        existing_questions = _build_existing_question_context(db, job.id)
        batch_prompt = build_exam_batch_generation_prompt(
            batch_data,
            batch_index,
            batch_count,
            existing_questions,
        )
        result = _generate_valid_ai_exam_result(
            provider,
            batch_prompt,
            batch_data,
            db=db,
            job_id=job.id,
            check_existing_duplicates=bool(existing_questions),
        )
        raw_batches.append(
            {
                "batch": batch_index,
                "question_count": batch_data["question_count"],
                "question_type_distribution": batch_data["question_type_distribution"],
                "raw_response": result.raw_response,
            }
        )
        _append_questions_to_job(
            db,
            job,
            result,
            status="running",
            question_count=int(request_data["question_count"]),
            raw_response={"batches": raw_batches},
        )

    _finalize_batched_ai_exam_job(db, job.id, request_data, raw_batches)


def _generate_valid_ai_exam_result(
    provider: AIProviderClient,
    prompt: str,
    request_data: dict[str, Any],
    db: Session | None = None,
    job_id: int | None = None,
    check_existing_duplicates: bool = False,
) -> AIProviderResult:
    result = provider.generate_exam(prompt)
    result.payload = sanitize_ai_exam_payload(result.payload)
    errors = _validate_generated_ai_exam_payload(
        db,
        job_id,
        result.payload,
        request_data,
        check_existing_duplicates,
    )

    if errors:
        repair_prompt = build_exam_repair_prompt(prompt, result.payload, errors)
        retry_result = provider.generate_exam(repair_prompt)
        retry_result.payload = sanitize_ai_exam_payload(retry_result.payload)
        retry_errors = _validate_generated_ai_exam_payload(
            db,
            job_id,
            retry_result.payload,
            request_data,
            check_existing_duplicates,
        )
        result = retry_result
        errors = retry_errors

    if errors:
        raise AIExamGenerationError(errors)

    return result


def _validate_generated_ai_exam_payload(
    db: Session | None,
    job_id: int | None,
    payload: dict[str, Any],
    request_data: dict[str, Any],
    check_existing_duplicates: bool,
) -> list[str]:
    _, errors = validate_ai_exam_payload(payload, request_data)
    if check_existing_duplicates and db is not None and job_id is not None:
        errors.extend(_validate_new_questions_against_existing(db, job_id, payload))
    return errors


def _get_ai_exam_batch_size() -> int:
    return max(1, min(int(settings.AI_EXAM_BATCH_SIZE or 10), 50))


def _build_question_type_distribution_batches(
    distribution: dict[str, int],
    question_types: list[str],
    batch_size: int,
) -> list[dict[str, int]]:
    remaining = {
        str(question_type): int(count or 0)
        for question_type, count in distribution.items()
        if int(count or 0) > 0
    }
    ordered_types = [question_type for question_type in question_types if question_type in remaining]
    ordered_types.extend(question_type for question_type in remaining if question_type not in ordered_types)

    batches: list[dict[str, int]] = []
    while sum(remaining.values()) > 0:
        slots = batch_size
        batch: dict[str, int] = {}
        for question_type in ordered_types:
            if slots <= 0:
                break
            available = remaining.get(question_type, 0)
            if available <= 0:
                continue
            take = min(available, slots)
            batch[question_type] = take
            remaining[question_type] = available - take
            slots -= take

        if not batch:
            break
        batches.append(batch)

    return batches


def _build_difficulty_distribution_batches(
    request_data: dict[str, Any],
    question_type_batches: list[dict[str, int]],
) -> list[dict[str, int]]:
    distribution = {
        str(difficulty): int(count or 0)
        for difficulty, count in (request_data.get("difficulty_distribution") or {}).items()
    }
    if sum(distribution.values()) != int(request_data["question_count"]):
        return [dict(distribution) for _ in question_type_batches]

    remaining = dict(distribution)
    difficulty_order = ["easy", "medium", "hard"]
    batches: list[dict[str, int]] = []
    for question_type_batch in question_type_batches:
        target_count = sum(question_type_batch.values())
        batch: dict[str, int] = {}
        slots = target_count
        for difficulty in difficulty_order:
            if slots <= 0:
                break
            available = remaining.get(difficulty, 0)
            if available <= 0:
                continue
            take = min(available, slots)
            batch[difficulty] = take
            remaining[difficulty] = available - take
            slots -= take
        batches.append(batch or dict(distribution))

    return batches


def _build_batch_request_data(
    request_data: dict[str, Any],
    question_type_distribution: dict[str, int],
    difficulty_distribution: dict[str, int],
) -> dict[str, Any]:
    batch_data = dict(request_data)
    batch_question_types = [
        question_type
        for question_type in request_data.get("question_types", [])
        if question_type_distribution.get(question_type, 0) > 0
    ]
    batch_question_types.extend(
        question_type
        for question_type in question_type_distribution
        if question_type not in batch_question_types
    )
    batch_data["question_count"] = sum(question_type_distribution.values())
    batch_data["question_types"] = batch_question_types
    batch_data["question_type_distribution"] = dict(question_type_distribution)
    batch_data["difficulty_distribution"] = dict(difficulty_distribution)
    return batch_data


def _finalize_batched_ai_exam_job(
    db: Session,
    job_id: int,
    request_data: dict[str, Any],
    raw_batches: list[dict[str, Any]],
) -> None:
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job:
        return

    drafts = (
        db.query(AIQuestionDraft)
        .filter(AIQuestionDraft.job_id == job_id)
        .order_by(AIQuestionDraft.order.asc())
        .all()
    )
    expected_count = int(request_data["question_count"])
    if len(drafts) != expected_count:
        raise AIExamGenerationError([f"Expected {expected_count} questions, got {len(drafts)}"])

    expected_distribution = request_data.get("question_type_distribution") or {}
    actual_distribution: dict[str, int] = {}
    for draft in drafts:
        actual_distribution[draft.question_type] = actual_distribution.get(draft.question_type, 0) + 1

    distribution_errors = []
    for question_type, expected in expected_distribution.items():
        actual = actual_distribution.get(question_type, 0)
        if actual != expected:
            distribution_errors.append(f"Expected {expected} {question_type} questions, got {actual}")
    if distribution_errors:
        raise AIExamGenerationError(distribution_errors)

    job.question_count = expected_count
    job.total_points = sum(float(draft.points or 0) for draft in drafts)
    job.raw_response = {"batches": raw_batches}
    job.error_message = ""
    job.status = "completed"
    job.updated_at = utc_now()
    db.commit()
    db.refresh(job)

def _process_more_questions_job(
    db: Session,
    job: AIExamGenerationJob,
    request_data: dict[str, Any],
) -> None:
    existing_questions = _build_existing_question_context(db, job.id)
    prompt = build_more_questions_prompt(request_data, existing_questions)

    try:
        provider = _get_ai_provider_client()
        result = provider.generate_exam(prompt)
        result.payload = sanitize_ai_exam_payload(result.payload)
        errors = _validate_more_questions_payload(db, job.id, result.payload, request_data)

        if errors:
            repair_prompt = build_exam_repair_prompt(prompt, result.payload, errors)
            retry_result = provider.generate_exam(repair_prompt)
            retry_result.payload = sanitize_ai_exam_payload(retry_result.payload)
            retry_errors = _validate_more_questions_payload(
                db,
                job.id,
                retry_result.payload,
                request_data,
            )
            result = retry_result
            errors = retry_errors

        if errors:
            raise AIExamGenerationError(errors)

        _append_questions_to_job(db, job, result)
    except AIExamGenerationError as exc:
        _mark_more_questions_failed(db, job.id, exc.errors)
        raise
    except AIProviderError as exc:
        errors = [str(exc)]
        _mark_more_questions_failed(db, job.id, errors)
        raise AIExamGenerationError(errors) from exc
    except Exception as exc:
        errors = ["Unexpected AI exam generation error"]
        _mark_more_questions_failed(db, job.id, errors)
        raise AIExamGenerationError(errors) from exc


def get_teacher_ai_exam_job(db: Session, teacher: User, job_id: int) -> AIExamGenerationJob:
    job = (
        db.query(AIExamGenerationJob)
        .options(joinedload(AIExamGenerationJob.question_drafts))
        .filter(
            AIExamGenerationJob.id == job_id,
            AIExamGenerationJob.teacher_id == teacher.id,
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI exam job not found")
    return job


def update_teacher_question_draft(
    db: Session,
    teacher: User,
    draft_id: int,
    data: dict[str, Any],
) -> AIQuestionDraft:
    draft = (
        db.query(AIQuestionDraft)
        .join(AIExamGenerationJob, AIExamGenerationJob.id == AIQuestionDraft.job_id)
        .filter(
            AIQuestionDraft.id == draft_id,
            AIExamGenerationJob.teacher_id == teacher.id,
        )
        .first()
    )
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question draft not found")

    for field in (
        "question_type",
        "content",
        "options",
        "correct_answer",
        "explanation",
        "difficulty",
        "points",
        "topic",
        "is_approved",
    ):
        if field in data:
            setattr(draft, field, data[field])

    payload = build_question_payload_from_draft(draft)
    errors = validate_ai_question_payload(payload, 1, {draft.question_type})
    if errors:
        raise AIExamGenerationError(errors)

    draft.updated_at = utc_now()
    db.commit()
    db.refresh(draft)
    return draft


def save_ai_exam_job_to_quiz(
    db: Session,
    teacher: User,
    job_id: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    job = get_teacher_ai_exam_job(db, teacher, job_id)
    if job.status == "converted" and job.quiz_id:
        return {
            "quiz_id": job.quiz_id,
            "exam_id": job.quiz_id,
            "message": "AI exam draft was already converted to exam.",
        }

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed AI exam jobs can be converted to exam",
        )

    approved_drafts = [
        draft
        for draft in sorted(job.question_drafts, key=lambda item: item.order)
        if draft.is_approved
    ]
    if not approved_drafts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one approved question draft is required",
        )

    questions = build_teacher_exam_questions_from_drafts(approved_drafts)
    title = data.get("title") or job.title or f"Đề kiểm tra {job.topic}"
    description = data.get("description")
    if description is None:
        description = job.description or "Đề được tạo bằng AI và giáo viên đã duyệt."

    result = create_teacher_exam(
        db=db,
        teacher=teacher,
        title=title,
        description=description,
        grade=job.grade,
        image_url=None,
        scope=data.get("scope") or "system",
        classroom_id=data.get("classroom_id"),
        duration_minutes=data.get("duration_minutes") or job.duration_minutes,
        start_time=data.get("start_time"),
        end_time=data.get("end_time"),
        is_published=bool(data.get("is_published", False)),
        is_active=bool(data.get("is_active", True)),
        questions=questions,
    )

    exam = result["exam"]
    job.quiz_id = exam["id"]
    job.status = "converted"
    job.updated_at = utc_now()
    db.commit()

    return {
        "quiz_id": exam["id"],
        "exam_id": exam["id"],
        "message": "AI exam draft was converted to exam successfully.",
    }


def build_teacher_exam_questions_from_drafts(drafts: list[AIQuestionDraft]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for index, draft in enumerate(drafts, start=1):
        payload = build_question_payload_from_draft(draft)
        errors = validate_ai_question_payload(payload, index, {draft.question_type})
        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=errors,
            )

        if draft.question_type == "multiple_choice":
            questions.append(_build_single_choice_question(draft, index))
        elif draft.question_type == "true_false":
            questions.append(_build_true_false_question(draft, index))
        elif draft.question_type == "short_answer":
            questions.append(_build_short_answer_question(draft, index))
        elif draft.question_type == "essay":
            questions.append(_build_text_question(draft, index))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {index}: unsupported question type",
            )

    return questions


def serialize_ai_exam_job(job: AIExamGenerationJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "status": job.status,
        "subject": job.subject,
        "grade": job.grade,
        "topic": job.topic,
        "duration_minutes": job.duration_minutes,
        "question_count": job.question_count,
        "question_types": job.question_types or [],
        "question_type_distribution": _build_job_question_type_distribution(job),
        "difficulty_distribution": job.difficulty_distribution or {},
        "language": job.language,
        "additional_instructions": job.additional_instructions or "",
        "title": job.title,
        "description": job.description,
        "total_points": float(job.total_points or 0),
        "provider": job.provider or "",
        "model": job.model or "",
        "agent_job_id": job.agent_job_id,
        "agent_operation": job.agent_operation,
        "agent_result_status": job.agent_result_status or "none",
        "qc_reserved": int(job.qc_reserved or 0),
        "qc_charged": int(job.qc_charged or 0),
        "qc_refunded": int(job.qc_refunded or 0),
        "free_questions_used": int(job.free_questions_used or 0),
        "qc_status": job.qc_status or "none",
        "error_message": job.error_message or "",
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "question_drafts": [
            serialize_question_draft(draft)
            for draft in sorted(job.question_drafts, key=lambda item: item.order)
        ],
    }


def _build_request_data_from_job(job: AIExamGenerationJob) -> dict[str, Any]:
    return {
        "subject": job.subject,
        "grade": job.grade,
        "topic": job.topic,
        "duration_minutes": job.duration_minutes,
        "question_count": job.question_count,
        "question_types": list(job.question_types or []),
        "question_type_distribution": _build_job_question_type_distribution(job),
        "difficulty_distribution": dict(job.difficulty_distribution or {}),
        "language": job.language,
        "additional_instructions": job.additional_instructions or "",
    }


def _build_more_request_data(
    job: AIExamGenerationJob,
    data: dict[str, Any],
) -> dict[str, Any]:
    extra_instructions = data.get("additional_instructions") or ""
    base_instructions = job.additional_instructions or ""
    if base_instructions and extra_instructions:
        additional_instructions = f"{base_instructions}\n{extra_instructions}"
    else:
        additional_instructions = base_instructions or extra_instructions

    question_types = data.get("question_types") or list(job.question_types or []) or ["multiple_choice"]
    question_type_distribution = data.get("question_type_distribution") or _build_default_more_question_type_distribution(
        question_types,
        data["question_count"],
    )

    return {
        "subject": job.subject,
        "grade": job.grade,
        "topic": job.topic,
        "duration_minutes": job.duration_minutes,
        "question_count": data["question_count"],
        "question_types": question_types,
        "question_type_distribution": question_type_distribution,
        "difficulty_distribution": data.get("difficulty_distribution")
        or _build_default_more_difficulty_distribution(job),
        "language": job.language,
        "additional_instructions": additional_instructions,
    }


def _build_default_more_difficulty_distribution(job: AIExamGenerationJob) -> dict[str, int]:
    default_distribution = {
        "easy": 40,
        "medium": 40,
        "hard": 20,
    }
    distribution = job.difficulty_distribution or {}
    values = {
        "easy": int(distribution.get("easy") or 0),
        "medium": int(distribution.get("medium") or 0),
        "hard": int(distribution.get("hard") or 0),
    }
    total = sum(values.values())
    if total <= 0:
        return default_distribution
    if total == 100:
        return values

    easy = round(values["easy"] * 100 / total)
    medium = round(values["medium"] * 100 / total)
    hard = max(0, 100 - easy - medium)
    return {
        "easy": easy,
        "medium": medium,
        "hard": hard,
    }


def _build_default_more_question_type_distribution(
    question_types: list[str],
    question_count: int,
) -> dict[str, int]:
    if not question_types:
        return {"multiple_choice": question_count}

    if len(question_types) == 1:
        return {question_types[0]: question_count}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="question_type_distribution is required when using multiple question types",
    )


def _build_job_question_type_distribution(job: AIExamGenerationJob) -> dict[str, int]:
    distribution = dict(job.question_type_distribution or {})
    if distribution:
        return distribution

    drafts = list(getattr(job, "question_drafts", None) or [])
    if drafts:
        actual_distribution: dict[str, int] = {}
        for draft in drafts:
            actual_distribution[draft.question_type] = actual_distribution.get(draft.question_type, 0) + 1
        return actual_distribution

    question_types = list(job.question_types or [])
    if len(question_types) == 1:
        return {question_types[0]: job.question_count}

    return {}


def _build_existing_question_context(
    db: Session,
    job_id: int,
) -> list[dict[str, Any]]:
    drafts = (
        db.query(AIQuestionDraft)
        .filter(AIQuestionDraft.job_id == job_id)
        .order_by(AIQuestionDraft.order.asc())
        .all()
    )
    return [
        {
            "id": draft.id,
            "status": "approved" if draft.is_approved else "rejected",
            "type": draft.question_type,
            "content": draft.content,
            "options": draft.options or [],
            "difficulty": draft.difficulty,
            "topic": draft.topic,
        }
        for draft in drafts
    ]


def _validate_more_questions_payload(
    db: Session,
    job_id: int,
    payload: dict[str, Any],
    request_data: dict[str, Any],
) -> list[str]:
    _, errors = validate_ai_exam_payload(payload, request_data)
    errors.extend(_validate_new_questions_against_existing(db, job_id, payload))
    return errors


def _validate_new_questions_against_existing(
    db: Session,
    job_id: int,
    payload: dict[str, Any],
) -> list[str]:
    if not isinstance(payload, dict):
        return []

    existing_contents = {
        _normalize_duplicate_text(content)
        for (content,) in db.query(AIQuestionDraft.content)
        .filter(AIQuestionDraft.job_id == job_id)
        .all()
    }
    existing_contents.discard("")

    questions = payload.get("questions")
    if not isinstance(questions, list):
        return []

    errors: list[str] = []
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            continue
        content_key = _normalize_duplicate_text(question.get("content"))
        if content_key and content_key in existing_contents:
            errors.append(f"Question {index}: duplicates an existing draft question")

    return errors


def _normalize_duplicate_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _build_single_choice_question(draft: AIQuestionDraft, order_index: int) -> dict[str, Any]:
    correct_answer = sanitize_ai_text(_normalize_answer_text(draft.correct_answer))
    options = []
    for index, option in enumerate(draft.options or []):
        option_text = sanitize_ai_text(str(option))
        options.append(
            {
                "option_key": OPTION_KEYS[index] if index < len(OPTION_KEYS) else str(index + 1),
                "option_text": option_text,
                "is_correct": option_text == correct_answer,
            }
        )

    return {
        "question_type": TEACHER_QUESTION_TYPE_SINGLE_CHOICE,
        "prompt": _build_exam_prompt(draft),
        "explanation": sanitize_ai_text(draft.explanation or ""),
        "order_index": order_index,
        "points": float(draft.points or 1),
        "options": options,
        "accepted_answers": [],
    }


def _build_true_false_question(draft: AIQuestionDraft, order_index: int) -> dict[str, Any]:
    correct_bool = _to_bool_answer(draft.correct_answer)
    return {
        "question_type": TEACHER_QUESTION_TYPE_TRUE_FALSE,
        "prompt": _build_exam_prompt(draft),
        "explanation": sanitize_ai_text(draft.explanation or ""),
        "order_index": order_index,
        "points": float(draft.points or 1),
        "options": [
            {
                "option_key": "A",
                "option_text": "Đúng",
                "is_correct": correct_bool is True,
            },
            {
                "option_key": "B",
                "option_text": "Sai",
                "is_correct": correct_bool is False,
            },
        ],
        "accepted_answers": [],
    }


def _build_short_answer_question(draft: AIQuestionDraft, order_index: int) -> dict[str, Any]:
    accepted_answers = _extract_text_answers(draft.correct_answer)
    if not accepted_answers:
        accepted_answers = [sanitize_ai_text(draft.explanation or "")]

    return {
        "question_type": TEACHER_QUESTION_TYPE_SHORT_ANSWER,
        "prompt": _build_exam_prompt(draft),
        "explanation": sanitize_ai_text(draft.explanation or ""),
        "order_index": order_index,
        "points": float(draft.points or 1),
        "options": [],
        "accepted_answers": accepted_answers,
    }


def _build_text_question(draft: AIQuestionDraft, order_index: int) -> dict[str, Any]:
    accepted_answers = _extract_text_answers(draft.correct_answer)
    if not accepted_answers:
        accepted_answers = [sanitize_ai_text(draft.explanation or "")]

    return {
        "question_type": TEACHER_QUESTION_TYPE_TEXT,
        "prompt": _build_exam_prompt(draft, include_explanation=draft.question_type == "essay"),
        "explanation": sanitize_ai_text(draft.explanation or ""),
        "order_index": order_index,
        "points": float(draft.points or 1),
        "options": [],
        "accepted_answers": accepted_answers,
    }


def _build_exam_prompt(draft: AIQuestionDraft, include_explanation: bool = False) -> str:
    content = sanitize_ai_text(draft.content or "")
    explanation = sanitize_ai_text(draft.explanation or "")
    if include_explanation and explanation:
        return f"{content}\n\nHướng dẫn chấm: {explanation}"
    return content


def _normalize_answer_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_bool_answer(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    return normalized in {"true", "đúng", "dung", "yes", "1"}


def _extract_text_answers(value: Any) -> list[str]:
    if isinstance(value, list):
        return [
            sanitize_ai_text(str(answer))
            for answer in value
            if sanitize_ai_text(str(answer))
        ]

    if value is None:
        return []

    answer = sanitize_ai_text(str(value))
    return [answer] if answer else []


def serialize_question_draft(draft: AIQuestionDraft) -> dict[str, Any]:
    return {
        "id": draft.id,
        "question_type": draft.question_type,
        "content": sanitize_ai_text(draft.content or ""),
        "options": [
            sanitize_ai_text(option) if isinstance(option, str) else option
            for option in draft.options or []
        ],
        "correct_answer": _sanitize_serialized_answer(draft.correct_answer),
        "explanation": sanitize_ai_text(draft.explanation or ""),
        "difficulty": draft.difficulty,
        "points": float(draft.points or 0),
        "topic": sanitize_ai_text(draft.topic or ""),
        "order": draft.order,
        "is_approved": draft.is_approved,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
    }


def _sanitize_serialized_answer(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_ai_text(value)
    if isinstance(value, list):
        return [
            sanitize_ai_text(answer) if isinstance(answer, str) else answer
            for answer in value
        ]
    return value


def _get_ai_provider_client() -> AIProviderClient:
    provider = settings.AI_PROVIDER.strip().lower()
    if provider == "mock":
        if not settings.DEBUG:
            raise AIProviderError("AI_PROVIDER=mock is only allowed when DEBUG=true")
        return MockAIProviderClient()

    if provider == "gemini":
        return GeminiAIProviderClient(
            timeout_seconds=settings.AI_PROVIDER_TIMEOUT_SECONDS,
            retry_count=settings.AI_PROVIDER_RETRY_COUNT,
        )

    raise AIProviderError(f"Unsupported AI_PROVIDER: {settings.AI_PROVIDER}")


def _extract_int_from_prompt(prompt: str, label: str, default: int) -> int:
    match = re.search(rf"{re.escape(label)}:\s*(\d+)", prompt)
    if not match:
        return default
    return int(match.group(1))


def _extract_text_from_prompt(prompt: str, label: str, default: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*(.+)", prompt)
    if not match:
        return default
    return match.group(1).strip()


def _extract_question_types_from_prompt(prompt: str) -> list[str]:
    raw_value = _extract_text_from_prompt(prompt, "Question types", "multiple_choice")
    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return values or ["multiple_choice"]


def _extract_json_object_from_prompt(prompt: str, label: str) -> dict[str, Any]:
    match = re.search(
        rf"{re.escape(label)}(?:\s*\([^)]*\))?:\s*(\{{[^\n]*\}})",
        prompt,
    )
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _extract_question_type_sequence_from_prompt(
    prompt: str,
    question_types: list[str],
    question_count: int,
) -> list[str]:
    distribution = _extract_json_object_from_prompt(prompt, "Question type distribution")
    sequence: list[str] = []
    for question_type in question_types:
        try:
            count = int(distribution.get(question_type) or 0)
        except (TypeError, ValueError):
            count = 0
        sequence.extend([question_type] * count)

    if len(sequence) == question_count:
        return sequence

    return [
        question_types[index % len(question_types)]
        for index in range(question_count)
    ]


def _build_mock_question(index: int, topic: str, question_type: str) -> dict[str, Any]:
    number = index + 1
    difficulty = ("easy", "medium", "hard")[index % 3]

    if question_type == "true_false":
        return {
            "type": "true_false",
            "content": f"Mock true/false question {number} about {topic}.",
            "options": [],
            "correct_answer": True,
            "explanation": "This is a local mock explanation.",
            "difficulty": difficulty,
            "points": 1,
            "topic": topic,
        }

    if question_type == "short_answer":
        return {
            "type": "short_answer",
            "content": f"Mock short answer question {number} about {topic}.",
            "options": [],
            "correct_answer": f"Answer {number}",
            "explanation": "This is a local mock explanation.",
            "difficulty": difficulty,
            "points": 1,
            "topic": topic,
        }

    if question_type == "essay":
        return {
            "type": "essay",
            "content": f"Mock essay question {number} about {topic}.",
            "options": [],
            "correct_answer": None,
            "explanation": "Use this mock rubric to evaluate clarity, relevance, and correctness.",
            "difficulty": difficulty,
            "points": 1,
            "topic": topic,
        }

    return {
        "type": "multiple_choice",
        "content": f"Mock multiple choice question {number} about {topic}.",
        "options": [
            f"Correct option {number}",
            f"Wrong option {number}.1",
            f"Wrong option {number}.2",
            f"Wrong option {number}.3",
        ],
        "correct_answer": f"Correct option {number}",
        "explanation": "This is a local mock explanation.",
        "difficulty": difficulty,
        "points": 1,
        "topic": topic,
    }


def _save_completed_job(
    db: Session,
    job: AIExamGenerationJob,
    result: AIProviderResult,
) -> None:
    payload = result.payload
    questions = payload.get("questions") or []

    job.title = (payload.get("title") or "").strip() or None
    job.description = (payload.get("description") or "").strip() or None
    job.total_points = float(payload.get("total_points") or 0)
    job.raw_response = result.raw_response
    job.error_message = ""
    job.status = "completed"
    job.updated_at = utc_now()

    for order, question in enumerate(questions, start=1):
        draft = AIQuestionDraft(
            job_id=job.id,
            question_type=question["type"],
            content=question["content"].strip(),
            options=question.get("options") or [],
            correct_answer=question.get("correct_answer"),
            explanation=(question.get("explanation") or "").strip(),
            difficulty=question["difficulty"],
            points=float(question.get("points") or 1),
            topic=(question.get("topic") or "").strip(),
            order=order,
            is_approved=True,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(draft)

    db.commit()
    db.refresh(job)


def _append_questions_to_job(
    db: Session,
    job: AIExamGenerationJob,
    result: AIProviderResult,
    *,
    status: str = "completed",
    question_count: int | None = None,
    raw_response: dict[str, Any] | None = None,
) -> None:
    payload = result.payload
    questions = payload.get("questions") or []
    latest_order = (
        db.query(func.max(AIQuestionDraft.order))
        .filter(AIQuestionDraft.job_id == job.id)
        .scalar()
        or 0
    )
    existing_count = (
        db.query(func.count(AIQuestionDraft.id))
        .filter(AIQuestionDraft.job_id == job.id)
        .scalar()
        or 0
    )
    existing_points = (
        db.query(func.coalesce(func.sum(AIQuestionDraft.points), 0))
        .filter(AIQuestionDraft.job_id == job.id)
        .scalar()
        or 0
    )

    new_points = 0.0
    for offset, question in enumerate(questions, start=1):
        new_points += float(question.get("points") or 1)
        draft = AIQuestionDraft(
            job_id=job.id,
            question_type=question["type"],
            content=question["content"].strip(),
            options=question.get("options") or [],
            correct_answer=question.get("correct_answer"),
            explanation=(question.get("explanation") or "").strip(),
            difficulty=question["difficulty"],
            points=float(question.get("points") or 1),
            topic=(question.get("topic") or "").strip(),
            order=latest_order + offset,
            is_approved=True,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(draft)

    if not job.title:
        job.title = (payload.get("title") or "").strip() or None
    if not job.description:
        job.description = (payload.get("description") or "").strip() or None
    job.total_points = float(existing_points or 0) + new_points
    job.question_count = question_count if question_count is not None else int(existing_count) + len(questions)
    job.raw_response = raw_response if raw_response is not None else result.raw_response
    job.error_message = ""
    job.status = status
    job.updated_at = utc_now()
    db.commit()
    db.refresh(job)


def _mark_job_failed(db: Session, job_id: int, errors: list[str]) -> None:
    db.rollback()
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job:
        return

    db.query(AIQuestionDraft).filter(AIQuestionDraft.job_id == job_id).delete(
        synchronize_session=False
    )
    job.status = "failed"
    job.error_message = "\n".join(errors)
    job.updated_at = utc_now()
    db.commit()


def _mark_more_questions_failed(db: Session, job_id: int, errors: list[str]) -> None:
    db.rollback()
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job:
        return

    has_existing_drafts = (
        db.query(AIQuestionDraft.id)
        .filter(AIQuestionDraft.job_id == job_id)
        .first()
        is not None
    )
    job.status = "completed" if has_existing_drafts else "failed"
    job.error_message = "\n".join(errors)
    job.updated_at = utc_now()
    db.commit()
