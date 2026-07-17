import json
from typing import Any

import httpx
from celery import Task

from ai_agent.celery_app import celery_app
from ai_agent.config import settings
from ai_agent.database import SessionLocal
from ai_agent.models import AgentAttempt, AgentJob
from ai_agent.provider import ProviderError, get_provider
from ai_agent.security import callback_headers


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
    }


def _deliver_callback(job: AgentJob) -> None:
    body = json.dumps(_callback_payload(job), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with httpx.Client(timeout=settings.CALLBACK_TIMEOUT_SECONDS) as client:
        response = client.post(
            job.callback_url,
            content=body,
            headers=callback_headers(settings.SHARED_SECRET, body),
        )
        response.raise_for_status()


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
                result = get_provider().generate(
                    job.prompt,
                    lambda number, state, http_status, latency_ms, error: _record_attempt(
                        db,
                        job,
                        number,
                        state,
                        http_status,
                        latency_ms,
                        error,
                    ),
                )
                job.result_payload = result.payload
                job.raw_response = result.raw_response
                job.error_message = ""
                job.status = "callback_pending"
            except ProviderError as exc:
                job.error_message = str(exc)
                job.status = "callback_pending"
            db.commit()

        try:
            _deliver_callback(job)
        except httpx.HTTPError as exc:
            job.status = "failed_callback"
            db.commit()
            countdown = min(60, 5 * (2 ** min(self.request.retries, 3)))
            raise self.retry(exc=exc, countdown=countdown)

        job.status = "completed" if job.result_payload is not None else "failed"
        db.commit()
        return {"status": job.status, "attempts": job.attempt_count}
    finally:
        db.close()
