from uuid import uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ai_agent.config import settings
from ai_agent.database import Base


KnowledgeVectorType = VECTOR(settings.EMBEDDING_DIMENSIONS)


class AgentJob(Base):
    __tablename__ = "agent_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dispatch_id = Column(String(64), nullable=False, unique=True, index=True)
    external_job_id = Column(String(64), nullable=False, index=True)
    operation = Column(String(30), nullable=False)
    prompt = Column(Text, nullable=False)
    request_data = Column(JSON, nullable=False, default=dict)
    callback_url = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="queued", index=True)
    provider = Column(String(50), nullable=False, default="")
    model = Column(String(100), nullable=False, default="")
    result_payload = Column(JSON, nullable=True)
    raw_response = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=False, default="")
    attempt_count = Column(Integer, nullable=False, default=0)
    stage = Column(String(30), nullable=False, default="queued")
    progress_current = Column(Integer, nullable=False, default=0)
    progress_total = Column(Integer, nullable=False, default=0)
    progress_message = Column(Text, nullable=False, default="")
    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    attempts = relationship("AgentAttempt", back_populates="job", cascade="all, delete-orphan")
    artifacts = relationship("AgentArtifact", back_populates="job", cascade="all, delete-orphan")


class AgentAttempt(Base):
    __tablename__ = "agent_attempts"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(36), ForeignKey("agent_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False)
    http_status = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("AgentJob", back_populates="attempts")


class AgentArtifact(Base):
    __tablename__ = "agent_artifacts"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_agent_artifacts_idempotency_key"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id = Column(
        String(36),
        ForeignKey("agent_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_job_id = Column(String(64), nullable=False, index=True)
    idempotency_key = Column(String(160), nullable=False, index=True)
    artifact_type = Column(String(30), nullable=False, index=True)
    schema_version = Column(String(20), nullable=False, default="1.0")
    status = Column(String(30), nullable=False, default="queued", index=True)
    storage_provider = Column(String(30), nullable=False, default="google_drive")
    object_name = Column(String(255), nullable=False)
    external_file_id = Column(String(255), nullable=False, default="")
    web_view_link = Column(Text, nullable=False, default="")
    checksum_sha256 = Column(String(64), nullable=False, default="")
    size_bytes = Column(BigInteger, nullable=False, default=0)
    payload = Column(JSON, nullable=True)
    artifact_metadata = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job = relationship("AgentJob", back_populates="artifacts")


class AgentKnowledgeItem(Base):
    __tablename__ = "agent_knowledge_items"
    __table_args__ = (
        UniqueConstraint(
            "owner_type",
            "owner_id",
            "content_hash",
            "embedding_model",
            name="uq_agent_knowledge_owner_content_model",
        ),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_artifact_id = Column(
        String(36),
        ForeignKey("agent_artifacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_job_id = Column(String(64), nullable=False, index=True)
    owner_type = Column(String(30), nullable=False, index=True)
    owner_id = Column(String(64), nullable=False, index=True)
    visibility = Column(String(20), nullable=False, default="private", index=True)
    status = Column(String(20), nullable=False, default="approved", index=True)
    content_hash = Column(String(64), nullable=False, index=True)
    embedding_model = Column(String(100), nullable=False)
    embedding_dimensions = Column(Integer, nullable=False)
    question_type = Column(String(40), nullable=False, default="", index=True)
    subject = Column(String(160), nullable=False, default="", index=True)
    grade = Column(String(100), nullable=False, default="", index=True)
    difficulty = Column(String(50), nullable=False, default="", index=True)
    topic = Column(String(255), nullable=False, default="", index=True)
    content = Column(Text, nullable=False)
    options = Column(JSON, nullable=False, default=list)
    correct_answer = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=False, default="")
    source_metadata = Column(JSON, nullable=False, default=dict)
    embedding = Column(KnowledgeVectorType, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentDatasetSnapshot(Base):
    __tablename__ = "agent_dataset_snapshots"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_agent_dataset_snapshots_idempotency_key"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idempotency_key = Column(String(160), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    status = Column(String(30), nullable=False, default="queued", index=True)
    min_quality_score = Column(Float, nullable=False, default=0.75)
    include_private_opt_in = Column(Boolean, nullable=False, default=False)
    source_count = Column(Integer, nullable=False, default=0)
    accepted_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    train_count = Column(Integer, nullable=False, default=0)
    validation_count = Column(Integer, nullable=False, default=0)
    test_count = Column(Integer, nullable=False, default=0)
    output_dir = Column(Text, nullable=False, default="")
    manifest = Column(JSON, nullable=False, default=dict)
    checksum_sha256 = Column(String(64), nullable=False, default="")
    error_message = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentModelVersion(Base):
    __tablename__ = "agent_model_versions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_agent_model_versions_idempotency_key"),
        UniqueConstraint("name", "version", name="uq_agent_model_versions_name_version"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idempotency_key = Column(String(160), nullable=False, index=True)
    name = Column(String(120), nullable=False, index=True)
    version = Column(String(80), nullable=False)
    provider = Column(String(40), nullable=False, default="local_openai")
    base_model = Column(String(255), nullable=False)
    serving_model = Column(String(255), nullable=False)
    adapter_uri = Column(Text, nullable=False, default="")
    adapter_checksum = Column(String(64), nullable=False, default="")
    dataset_snapshot_id = Column(
        String(36),
        ForeignKey("agent_dataset_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(30), nullable=False, default="registered", index=True)
    training_report = Column(JSON, nullable=False, default=dict)
    evaluation_report = Column(JSON, nullable=False, default=dict)
    evaluation_score = Column(Float, nullable=True)
    evaluation_threshold = Column(Float, nullable=False, default=0.9)
    routing_weight = Column(Integer, nullable=False, default=0)
    approved_by = Column(String(160), nullable=False, default="")
    approval_reason = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentModelEvent(Base):
    __tablename__ = "agent_model_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    model_version_id = Column(
        String(36),
        ForeignKey("agent_model_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False, index=True)
    from_status = Column(String(30), nullable=False, default="")
    to_status = Column(String(30), nullable=False, default="")
    actor = Column(String(160), nullable=False, default="system")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentModelRun(Base):
    __tablename__ = "agent_model_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    model_version_id = Column(
        String(36),
        ForeignKey("agent_model_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = Column(
        String(36),
        ForeignKey("agent_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mode = Column(String(20), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="queued", index=True)
    provider = Column(String(40), nullable=False, default="local_openai")
    model = Column(String(255), nullable=False)
    structural_valid = Column(Boolean, nullable=True)
    score = Column(Float, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    metrics = Column(JSON, nullable=False, default=dict)
    error_message = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
