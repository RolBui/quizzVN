from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_agent.config import settings
from ai_agent.models import AgentArtifact, AgentJob


SCHEMA_VERSION = "1.0"


def create_job_artifact(
    db: Session,
    job: AgentJob,
    artifact_type: str,
) -> tuple[AgentArtifact, bool]:
    idempotency_key = f"job:{job.dispatch_id}:{artifact_type}:{SCHEMA_VERSION}"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "job": {
            "dispatch_id": job.dispatch_id,
            "external_job_id": job.external_job_id,
            "operation": job.operation,
            "provider": job.provider,
            "model": job.model,
            "attempt_count": int(job.attempt_count or 0),
        },
        "input": {
            "prompt": job.prompt,
            "request_data": job.request_data or {},
        },
        "output": {
            "payload": job.result_payload,
            "raw_response": job.raw_response,
            "error": job.error_message,
        },
    }
    return _create_artifact(
        db=db,
        job=job,
        external_job_id=job.external_job_id,
        idempotency_key=idempotency_key,
        artifact_type=artifact_type,
        payload=payload,
        metadata={
            "dispatch_id": job.dispatch_id,
            "provider": job.provider,
            "model": job.model,
            "validation_status": "agent_validated" if artifact_type == "generated" else "rejected",
        },
    )


def create_approved_artifact(
    db: Session,
    *,
    external_job_id: str,
    idempotency_key: str,
    request_data: dict[str, Any],
    questions: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> tuple[AgentArtifact, bool]:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "approved",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "job": {"external_job_id": external_job_id},
        "input": {"request_data": request_data},
        "output": {"questions": questions},
        "review": {
            "status": "teacher_approved",
            "approved_question_count": len(questions),
        },
        "metadata": metadata,
    }
    return _create_artifact(
        db=db,
        job=None,
        external_job_id=external_job_id,
        idempotency_key=idempotency_key,
        artifact_type="approved",
        payload=payload,
        metadata={
            **metadata,
            "validation_status": "teacher_approved",
        },
    )


def _create_artifact(
    *,
    db: Session,
    job: AgentJob | None,
    external_job_id: str,
    idempotency_key: str,
    artifact_type: str,
    payload: dict[str, Any],
    metadata: dict[str, Any],
) -> tuple[AgentArtifact, bool]:
    existing = (
        db.query(AgentArtifact)
        .filter(AgentArtifact.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        return existing, False

    artifact_id = str(uuid4())
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    artifact = AgentArtifact(
        id=artifact_id,
        job_id=job.id if job else None,
        external_job_id=external_job_id,
        idempotency_key=idempotency_key,
        artifact_type=artifact_type,
        schema_version=SCHEMA_VERSION,
        status="queued",
        storage_provider=settings.DATA_LAKE_PROVIDER,
        object_name=f"{artifact_type}__{date_part}__job-{external_job_id}__{artifact_id}.json",
        payload=payload,
        artifact_metadata=metadata,
    )
    db.add(artifact)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(AgentArtifact)
            .filter(AgentArtifact.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing, False
        raise
    db.refresh(artifact)
    return artifact, True
