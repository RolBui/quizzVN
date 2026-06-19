import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import utc_now
from app.database import engine
from app.models.ai_exam import AIExamGenerationJob, AIQuestionDraft
# Loads the referenced table for AIExamGenerationJob.quiz_id during bootstrap.
from app.models.exam import Exam
from app.models.user import User
from app.services.ai_exam_prompt_builder import build_exam_generation_prompt, build_exam_repair_prompt
from app.services.ai_exam_validator import (
    build_question_payload_from_draft,
    sanitize_ai_exam_payload,
    validate_ai_exam_payload,
    validate_ai_question_payload,
)
from app.services.ai_provider_client import AIProviderClient, AIProviderError, AIProviderResult
from app.services.gemini_client import GeminiAIProviderClient
from app.services.teacher_service import create_teacher_exam


TEACHER_QUESTION_TYPE_SINGLE_CHOICE = "single_choice"
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

        payload = {
            "title": f"Mock exam draft for {topic}",
            "description": "Local mock draft generated without calling an AI provider.",
            "subject": subject,
            "grade": grade,
            "duration_minutes": duration_minutes,
            "total_points": question_count,
            "questions": [
                _build_mock_question(index, topic, question_types[index % len(question_types)])
                for index in range(question_count)
            ],
        }
        return AIProviderResult(payload=payload, raw_response=payload)


def bootstrap_ai_exam_storage() -> None:
    AIExamGenerationJob.__table__.create(bind=engine, checkfirst=True)
    AIQuestionDraft.__table__.create(bind=engine, checkfirst=True)


def generate_exam_for_teacher(
    db: Session,
    teacher: User,
    request_data: dict[str, Any],
) -> AIExamGenerationJob:
    provider = _get_ai_provider_client()
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

    try:
        result = provider.generate_exam(prompt)
        result.payload = sanitize_ai_exam_payload(result.payload)
        valid, errors = validate_ai_exam_payload(result.payload, request_data)

        if not valid:
            repair_prompt = build_exam_repair_prompt(prompt, result.payload, errors)
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

    return get_teacher_ai_exam_job(db, teacher, job.id)


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
        elif draft.question_type in {"short_answer", "essay"}:
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


def _build_single_choice_question(draft: AIQuestionDraft, order_index: int) -> dict[str, Any]:
    correct_answer = _normalize_answer_text(draft.correct_answer)
    return {
        "question_type": TEACHER_QUESTION_TYPE_SINGLE_CHOICE,
        "prompt": _build_exam_prompt(draft),
        "order_index": order_index,
        "points": float(draft.points or 1),
        "options": [
            {
                "option_key": OPTION_KEYS[index] if index < len(OPTION_KEYS) else str(index + 1),
                "option_text": str(option).strip(),
                "is_correct": str(option).strip() == correct_answer,
            }
            for index, option in enumerate(draft.options or [])
        ],
        "accepted_answers": [],
    }


def _build_true_false_question(draft: AIQuestionDraft, order_index: int) -> dict[str, Any]:
    correct_bool = _to_bool_answer(draft.correct_answer)
    return {
        "question_type": TEACHER_QUESTION_TYPE_SINGLE_CHOICE,
        "prompt": _build_exam_prompt(draft),
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


def _build_text_question(draft: AIQuestionDraft, order_index: int) -> dict[str, Any]:
    accepted_answers = _extract_text_answers(draft.correct_answer)
    if not accepted_answers:
        accepted_answers = [draft.explanation.strip()]

    return {
        "question_type": TEACHER_QUESTION_TYPE_TEXT,
        "prompt": _build_exam_prompt(draft, include_explanation=draft.question_type == "essay"),
        "order_index": order_index,
        "points": float(draft.points or 1),
        "options": [],
        "accepted_answers": accepted_answers,
    }


def _build_exam_prompt(draft: AIQuestionDraft, include_explanation: bool = False) -> str:
    content = draft.content.strip()
    if include_explanation and draft.explanation.strip():
        return f"{content}\n\nHướng dẫn chấm: {draft.explanation.strip()}"
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
            str(answer).strip()
            for answer in value
            if str(answer).strip()
        ]

    if value is None:
        return []

    answer = str(value).strip()
    return [answer] if answer else []


def serialize_question_draft(draft: AIQuestionDraft) -> dict[str, Any]:
    return {
        "id": draft.id,
        "question_type": draft.question_type,
        "content": draft.content,
        "options": draft.options or [],
        "correct_answer": draft.correct_answer,
        "explanation": draft.explanation or "",
        "difficulty": draft.difficulty,
        "points": float(draft.points or 0),
        "topic": draft.topic or "",
        "order": draft.order,
        "is_approved": draft.is_approved,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
    }


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


def _mark_job_failed(db: Session, job_id: int, errors: list[str]) -> None:
    db.rollback()
    job = db.query(AIExamGenerationJob).filter(AIExamGenerationJob.id == job_id).first()
    if not job:
        return

    job.status = "failed"
    job.error_message = "\n".join(errors)
    job.updated_at = utc_now()
    db.commit()
