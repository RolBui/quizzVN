import json

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.config import settings
from app.database import get_db
from app.services.ai_agent_security import verify_ai_agent_signature
from app.services.ai_exam_service import complete_ai_agent_job, fail_ai_agent_job


router = APIRouter(prefix="/api/internal/ai-agent", tags=["AI Agent Internal"])


class AIAgentCallback(BaseModel):
    dispatch_id: str = Field(min_length=16, max_length=64)
    operation: str
    status: str
    payload: dict | None = None
    raw_response: dict | str | None = None
    error: str = ""
    provider: str = ""
    model: str = ""
    attempts: int = Field(default=0, ge=0)


@router.post("/callbacks/{job_id}", include_in_schema=False)
async def post_ai_agent_callback(
    job_id: int,
    request: Request,
    x_ai_agent_timestamp: str = Header(default="", alias="X-AI-Agent-Timestamp"),
    x_ai_agent_signature: str = Header(default="", alias="X-AI-Agent-Signature"),
    db: Session = Depends(get_db),
) -> dict:
    body = await request.body()
    if not verify_ai_agent_signature(
        settings.AI_AGENT_SHARED_SECRET,
        x_ai_agent_timestamp,
        body,
        x_ai_agent_signature,
        settings.AI_AGENT_CALLBACK_TOLERANCE_SECONDS,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid AI Agent signature")

    try:
        callback = AIAgentCallback.model_validate(json.loads(body))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid callback body") from exc

    if callback.status == "completed" and callback.payload is not None:
        job = complete_ai_agent_job(
            db,
            job_id,
            callback.dispatch_id,
            callback.operation,
            callback.payload,
            callback.raw_response or callback.payload,
            callback.provider,
            callback.model,
        )
    elif callback.status == "failed":
        job = fail_ai_agent_job(
            db,
            job_id,
            callback.dispatch_id,
            callback.operation,
            [callback.error or "AI Agent generation failed"],
        )
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid callback status")

    return {
        "accepted": True,
        "job_id": job.id,
        "status": job.status,
        "agent_result_status": job.agent_result_status,
    }
