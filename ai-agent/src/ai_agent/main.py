import hmac

import redis
from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_agent.config import settings
from ai_agent.database import bootstrap_storage, get_db
from ai_agent.models import AgentJob
from ai_agent.schemas import AgentJobCreate, AgentJobResponse
from ai_agent.tasks import generate_exam


app = FastAPI(title=settings.APP_NAME, version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    bootstrap_storage()


def require_internal_auth(authorization: str = Header(default="")) -> None:
    expected = f"Bearer {settings.SHARED_SECRET}"
    if not settings.SHARED_SECRET or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token")


@app.get("/health")
def health() -> dict:
    redis_status = "unavailable"
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        redis_status = "ok" if client.ping() else "unavailable"
    except redis.RedisError:
        pass
    return {"status": "ok" if redis_status == "ok" else "degraded", "redis": redis_status}


@app.post("/v1/jobs", response_model=AgentJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    payload: AgentJobCreate,
    _: None = Depends(require_internal_auth),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> AgentJob:
    if idempotency_key != payload.dispatch_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid idempotency key")

    existing = db.query(AgentJob).filter(AgentJob.dispatch_id == payload.dispatch_id).first()
    if existing:
        if existing.status == "dispatch_failed":
            existing.status = "queued"
            existing.error_message = ""
            db.commit()
            try:
                generate_exam.delay(existing.id)
            except Exception as exc:
                existing.status = "dispatch_failed"
                existing.error_message = str(exc)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Queue unavailable",
                ) from exc
        return existing

    job = AgentJob(
        dispatch_id=payload.dispatch_id,
        external_job_id=payload.external_job_id,
        operation=payload.operation,
        prompt=payload.prompt,
        request_data=payload.request_data,
        callback_url=str(payload.callback_url),
        status="queued",
        provider=settings.AI_PROVIDER,
        model=settings.AI_MODEL,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(AgentJob).filter(AgentJob.dispatch_id == payload.dispatch_id).first()
        if existing:
            return existing
        raise
    db.refresh(job)
    try:
        generate_exam.delay(job.id)
    except Exception as exc:
        job.status = "dispatch_failed"
        job.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Queue unavailable") from exc
    return job


@app.get("/v1/jobs/{job_id}", response_model=AgentJobResponse)
def get_job(
    job_id: str,
    _: None = Depends(require_internal_auth),
    db: Session = Depends(get_db),
) -> AgentJob:
    job = db.get(AgentJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent job not found")
    return job
