from uuid import uuid4

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ai_agent.database import Base


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
