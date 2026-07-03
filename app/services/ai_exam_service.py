import json
import re
from typing import Any

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
            UPDATE ai_exam_generation_jobs
            SET question_type_distribution = '{}'::jsonb
            WHERE question_type_distribution IS NULL;
        """
    else:
        statement = """
            ALTER TABLE ai_exam_generation_jobs
            ADD COLUMN IF NOT EXISTS question_type_distribution JSON NOT NULL DEFAULT '{}';
            UPDATE ai_exam_generation_jobs
            SET question_type_distribution = '{}'
            WHERE question_type_distribution IS NULL;
        """

    with engine.begin() as connection:
        connection.execute(text(statement))


def create_ai_exam_generation_job(
    db: Session,
    teacher: User,
    request_data: dict[str, Any],
) -> AIExamGenerationJob:
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
    db.commit()
    db.refresh(job)
    return job


def generate_exam_for_teacher(
    db: Session,
    teacher: User,
    request_data: dict[str, Any],
) -> AIExamGenerationJob:
    job = create_ai_exam_generation_job(db, teacher, request_data)
    _process_ai_exam_job(db, job, request_data)
    return get_teacher_ai_exam_job(db, teacher, job.id)


def run_ai_exam_generation_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
        if not job or job.status != "running":
            return
        _process_ai_exam_job(db, job, _build_request_data_from_job(job))
    except AIExamGenerationError:
        return
    finally:
        db.close()


def start_more_questions_for_teacher(
    db: Session,
    teacher: User,
    job_id: int,
    data: dict[str, Any],
) -> tuple[AIExamGenerationJob, dict[str, Any]]:
    job = get_teacher_ai_exam_job(db, teacher, job_id)
    if job.status in {"running", "generating_more"}:
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
    db.commit()
    db.refresh(job)
    return job, request_data


def run_more_questions_job(job_id: int, request_data: dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
        if not job or job.status != "generating_more":
            return
        _process_more_questions_job(db, job, request_data)
    except AIExamGenerationError:
        return
    finally:
        db.close()


def _process_ai_exam_job(
    db: Session,
    job: AIExamGenerationJob,
    request_data: dict[str, Any],
) -> None:
    try:
        provider = _get_ai_provider_client()
        result = provider.generate_exam(job.prompt)
        result.payload = sanitize_ai_exam_payload(result.payload)
        valid, errors = validate_ai_exam_payload(result.payload, request_data)

        if not valid:
            repair_prompt = build_exam_repair_prompt(job.prompt, result.payload, errors)
            retry_result = provider.generate_exam(repair_prompt)
            retry_result.payload = sanitize_ai_exam_payload(retry_result.payload)
            retry_valid, retry_errors = validate_ai_exam_payload(retry_result.payload, request_data)
            result = retry_result
            valid = retry_valid
            errors = retry_errors

        if not valid:
            raise AIExamGenerationError(errors)

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
        return GeminiAIProviderClient()

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
    job.question_count = int(existing_count) + len(questions)
    job.raw_response = result.raw_response
    job.error_message = ""
    job.status = "completed"
    job.updated_at = utc_now()
    db.commit()
    db.refresh(job)


def _mark_job_failed(db: Session, job_id: int, errors: list[str]) -> None:
    db.rollback()
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job:
        return

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
