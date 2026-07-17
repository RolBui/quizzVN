from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class AgentJobCreate(BaseModel):
    dispatch_id: str = Field(min_length=16, max_length=64)
    external_job_id: str = Field(min_length=1, max_length=64)
    operation: Literal["initial", "generate_more"]
    prompt: str = Field(min_length=1)
    request_data: dict[str, Any]
    callback_url: HttpUrl
    priority: int = Field(default=0, ge=0, le=9)


class AgentJobResponse(BaseModel):
    id: str
    dispatch_id: str
    external_job_id: str
    operation: str
    status: str
    provider: str
    model: str
    error_message: str
    attempt_count: int
    stage: str
    progress_current: int
    progress_total: int
    progress_message: str
    priority: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
