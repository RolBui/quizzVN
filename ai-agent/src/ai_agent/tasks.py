import json
import logging
from typing import Any

import httpx
from celery import Task

from ai_agent.celery_app import celery_app
from ai_agent.batching import aggregate_batch_payloads, build_batch_prompt, build_batch_specs
from ai_agent.config import settings
from ai_agent.database import SessionLocal
from ai_agent.models import AgentAttempt, AgentJob
from ai_agent.provider import ProviderError, build_semantic_repair_prompt, get_provider
from ai_agent.security import callback_headers
from ai_agent.validation import validate_exam_payload


logger = logging.getLogger(__name__)


def _record_attempt(db, job: AgentJob, number: int, state: str, http_status, latency_ms: int, error: str) -> None:
    db.add(
        AgentAttempt(
            job_id=job.id,
            attempt_number=number,
            status=state,
            http_status=http_status,
            latency_ms=latency_ms,
            error_message=error,
        )
    )
    job.attempt_count = max(int(job.attempt_count or 0), number)
    db.commit()


def _callback_payload(job: AgentJob) -> dict[str, Any]:
    status = "completed" if job.result_payload is not None else "failed"
    return {
        "dispatch_id": job.dispatch_id,
        "operation": job.operation,
        "status": status,
        "payload": job.result_payload,
        "raw_response": job.raw_response,
        "error": job.error_message,
        "provider": job.provider,
        "model": job.model,
        "attempts": int(job.attempt_count or 0),
        "stage": getattr(job, "stage", status),
        "progress_current": int(getattr(job, "progress_current", 0) or 0),
        "progress_total": int(getattr(job, "progress_total", 0) or 0),
        "progress_message": getattr(job, "progress_message", "") or "",
    }


def _progress_payload(job: AgentJob) -> dict[str, Any]:
    payload = _callback_payload(job)
    payload["status"] = "progress"
    payload["payload"] = None
    payload["raw_response"] = None
    payload["error"] = ""
    return payload


class CallbackValidationError(RuntimeError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("Backend rejected the generated exam")
        self.errors = errors


def _post_callback(job: AgentJob, payload: dict[str, Any]) -> httpx.Response:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with httpx.Client(timeout=settings.CALLBACK_TIMEOUT_SECONDS) as client:
        response = client.post(
            job.callback_url,
            content=body,
            headers=callback_headers(settings.SHARED_SECRET, body),
        )
    return response


def _deliver_callback(job: AgentJob) -> None:
    response = _post_callback(job, _callback_payload(job))
    validation_errors = _callback_validation_errors(response)
    if validation_errors:
        raise CallbackValidationError(validation_errors)
    response.raise_for_status()


def _deliver_progress(job: AgentJob) -> None:
    response = _post_callback(job, _progress_payload(job))
    response.raise_for_status()


def _set_progress(
    db,
    job: AgentJob,
    stage: str,
    current: int,
    total: int,
    message: str,
) -> None:
    job.stage = stage
    job.progress_current = max(0, min(int(current), int(total)))
    job.progress_total = max(0, int(total))
    job.progress_message = message
    db.commit()
    try:
        _deliver_progress(job)
    except httpx.HTTPError as exc:
        logger.warning("Unable to deliver AI Agent progress for job %s: %s", job.id, exc)


def _callback_validation_errors(response: httpx.Response) -> list[str]:
    if response.status_code != 422:
        return []
    try:
        detail = response.json().get("detail")
    except (ValueError, AttributeError):
        return []
    if not isinstance(detail, dict) or detail.get("code") != "semantic_validation_failed":
        return []
    errors = detail.get("errors")
    if not isinstance(errors, list):
        return []
    return [str(error) for error in errors if str(error).strip()]


def _mark_generation_failed(job: AgentJob, message: str) -> None:
    job.result_payload = None
    job.error_message = message
    job.status = "callback_pending"
    job.stage = "failed"
    job.progress_message = message


def _record_provider_attempt(db, job: AgentJob):
    return lambda number, state, http_status, latency_ms, error: _record_attempt(
        db,
        job,
        number,
        state,
        http_status,
        latency_ms,
        error,
    )


def _generate_valid_batch(
    db,
    job: AgentJob,
    prompt: str,
    batch_data: dict[str, Any],
    existing_questions: list[dict[str, Any]],
    completed_count: int,
    total_count: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = get_provider()
    current_prompt = prompt
    previous_payload: dict[str, Any] | None = None
    raw_responses: list[dict[str, Any]] = []
    errors: list[str] = []

    for repair_index in range(settings.SEMANTIC_REPAIR_COUNT + 1):
        stage = "generating" if repair_index == 0 else "repairing"
        message = (
            f"\u0110ang t\u1ea1o c\u00e2u {completed_count + 1}-{completed_count + int(batch_data['question_count'])}"
            if repair_index == 0
            else f"\u0110ang s\u1eeda l\u00f4 c\u00e2u h\u1ecfi l\u1ea7n {repair_index}"
        )
        _set_progress(db, job, stage, completed_count, total_count, message)
        result = provider.generate(
            current_prompt,
            _record_provider_attempt(db, job),
            attempt_offset=int(job.attempt_count or 0),
        )
        previous_payload, errors = validate_exam_payload(
            result.payload,
            batch_data,
            existing_questions,
        )
        raw_responses.append(result.raw_response)
        if not errors:
            return previous_payload, {"responses": raw_responses, "repairs": repair_index}
        if repair_index < settings.SEMANTIC_REPAIR_COUNT:
            current_prompt = build_semantic_repair_prompt(
                prompt,
                previous_payload,
                errors,
            )

    raise ProviderError("Semantic validation failed: " + "; ".join(errors[:12]))


def _generate_job_payload(db, job: AgentJob) -> tuple[dict[str, Any], dict[str, Any]]:
    request_data = dict(job.request_data or {})
    total_count = int(request_data.get("question_count") or 0)
    batch_specs = build_batch_specs(request_data, settings.BATCH_SIZE)
    if not batch_specs:
        raise ProviderError("Unable to split the AI request into batches")

    payloads: list[dict[str, Any]] = []
    raw_batches: list[dict[str, Any]] = []
    generated_questions: list[dict[str, Any]] = []
    completed_count = 0

    for batch_index, batch_data in enumerate(batch_specs, start=1):
        prompt = build_batch_prompt(
            job.prompt,
            batch_data,
            batch_index,
            len(batch_specs),
            generated_questions,
        )
        payload, raw = _generate_valid_batch(
            db,
            job,
            prompt,
            batch_data,
            generated_questions,
            completed_count,
            total_count,
        )
        payloads.append(payload)
        generated_questions.extend(payload.get("questions") or [])
        completed_count = len(generated_questions)
        raw_batches.append(
            {
                "batch": batch_index,
                "question_count": int(batch_data["question_count"]),
                "question_type_distribution": batch_data["question_type_distribution"],
                "provider_response": raw,
            }
        )
        _set_progress(
            db,
            job,
            "validating",
            completed_count,
            total_count,
            f"\u0110\u00e3 ki\u1ec3m tra {completed_count}/{total_count} c\u00e2u",
        )

    combined = aggregate_batch_payloads(payloads)
    combined, errors = validate_exam_payload(combined, request_data)
    if errors:
        raise ProviderError("Combined exam validation failed: " + "; ".join(errors[:12]))
    return combined, {"batches": raw_batches}


def _deliver_with_semantic_repair(db, job: AgentJob) -> None:
    semantic_errors: list[str] = []
    try:
        _deliver_callback(job)
        return
    except CallbackValidationError as first_error:
        if job.result_payload is None:
            raise
        semantic_errors = list(first_error.errors)

    previous_payload = job.result_payload
    repair_prompt = build_semantic_repair_prompt(
        job.prompt,
        previous_payload,
        semantic_errors,
    )
    try:
        repaired_result = get_provider().generate(
            repair_prompt,
            _record_provider_attempt(db, job),
            attempt_offset=int(job.attempt_count or 0),
        )
        job.result_payload = repaired_result.payload
        job.raw_response = {
            "initial_response": job.raw_response,
            "semantic_repair_response": repaired_result.raw_response,
        }
        job.error_message = ""
        job.status = "callback_pending"
        db.commit()
    except ProviderError as exc:
        _mark_generation_failed(job, f"Semantic repair failed: {exc}")
        db.commit()
        _deliver_callback(job)
        return

    try:
        _deliver_callback(job)
    except CallbackValidationError as second_error:
        message = "; ".join(second_error.errors)
        _mark_generation_failed(job, f"Semantic validation failed after repair: {message}")
        db.commit()
        _deliver_callback(job)


@celery_app.task(bind=True, name="ai_agent.generate_exam", max_retries=settings.CALLBACK_RETRY_COUNT)
def generate_exam(self: Task, job_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        job = db.get(AgentJob, job_id)
        if not job:
            return {"status": "missing"}
        if job.status == "completed":
            return {"status": "completed"}

        if job.result_payload is None and job.status not in {"callback_pending", "failed_callback"}:
            job.status = "running"
            job.provider = settings.AI_PROVIDER
            job.model = settings.AI_MODEL
            db.commit()
            try:
                job.result_payload, job.raw_response = _generate_job_payload(db, job)
                job.error_message = ""
                job.status = "callback_pending"
                job.stage = "callback_pending"
                job.progress_current = int(job.progress_total or 0)
                job.progress_message = "\u0110ang g\u1eedi k\u1ebft qu\u1ea3 v\u1ec1 QuizzVN"
            except ProviderError as exc:
                _mark_generation_failed(job, str(exc))
            db.commit()

        try:
            _deliver_with_semantic_repair(db, job)
        except httpx.HTTPError as exc:
            job.status = "failed_callback"
            db.commit()
            countdown = min(60, 5 * (2 ** min(self.request.retries, 3)))
            raise self.retry(exc=exc, countdown=countdown)

        job.status = "completed" if job.result_payload is not None else "failed"
        job.stage = job.status
        if job.status == "completed":
            job.progress_current = int(job.progress_total or 0)
            job.progress_message = "\u0110\u00e3 ho\u00e0n t\u1ea5t t\u1ea1o c\u00e2u h\u1ecfi"
        db.commit()
        return {"status": job.status, "attempts": job.attempt_count}
    finally:
        db.close()
