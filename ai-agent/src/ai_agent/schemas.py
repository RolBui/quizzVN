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


class ApprovedDatasetCreate(BaseModel):
    idempotency_key: str = Field(min_length=16, max_length=160)
    external_job_id: str = Field(min_length=1, max_length=64)
    request_data: dict[str, Any]
    questions: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactResponse(BaseModel):
    id: str
    external_job_id: str
    idempotency_key: str
    artifact_type: str
    status: str
    storage_provider: str
    object_name: str
    external_file_id: str
    web_view_link: str
    checksum_sha256: str
    size_bytes: int
    error_message: str
    created_at: datetime | None = None
    uploaded_at: datetime | None = None

    model_config = {"from_attributes": True}


class DatasetSnapshotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    include_private_opt_in: bool = False
    min_quality_score: float | None = Field(default=None, ge=0.0, le=1.0)


class DatasetSnapshotResponse(BaseModel):
    id: str
    idempotency_key: str
    name: str
    status: str
    min_quality_score: float
    include_private_opt_in: bool
    source_count: int
    accepted_count: int
    rejected_count: int
    train_count: int
    validation_count: int
    test_count: int
    output_dir: str
    manifest: dict[str, Any]
    checksum_sha256: str
    error_message: str
    created_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ModelVersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    provider: Literal["local_openai"] = "local_openai"
    base_model: str = Field(min_length=1, max_length=255)
    serving_model: str = Field(min_length=1, max_length=255)
    adapter_uri: str = Field(default="", max_length=2000)
    adapter_checksum: str = Field(default="", max_length=64)
    dataset_snapshot_id: str | None = None
    training_report: dict[str, Any] = Field(default_factory=dict)
    evaluation_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class ModelEvaluationSubmit(BaseModel):
    report: dict[str, Any]
    actor: str = Field(default="evaluation-pipeline", min_length=1, max_length=160)


class ModelApprovalRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=2000)


class ModelDeploymentRequest(BaseModel):
    mode: Literal["shadow", "canary", "active"]
    actor: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=2000)
    routing_weight: int | None = Field(default=None, ge=1, le=99)


class ModelRetireRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=160)
    reason: str = Field(min_length=1, max_length=2000)


class ModelVersionResponse(BaseModel):
    id: str
    idempotency_key: str
    name: str
    version: str
    provider: str
    base_model: str
    serving_model: str
    adapter_uri: str
    adapter_checksum: str
    dataset_snapshot_id: str | None
    status: str
    training_report: dict[str, Any]
    evaluation_report: dict[str, Any]
    evaluation_score: float | None
    evaluation_threshold: float
    routing_weight: int
    approved_by: str
    approval_reason: str
    created_at: datetime | None = None
    evaluated_at: datetime | None = None
    approved_at: datetime | None = None
    activated_at: datetime | None = None
    retired_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ModelRunResponse(BaseModel):
    id: str
    model_version_id: str
    job_id: str | None
    mode: str
    status: str
    provider: str
    model: str
    structural_valid: bool | None
    score: float | None
    latency_ms: int
    metrics: dict[str, Any]
    error_message: str
    created_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ModelEventResponse(BaseModel):
    id: str
    model_version_id: str
    event_type: str
    from_status: str
    to_status: str
    actor: str
    details: dict[str, Any]
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
