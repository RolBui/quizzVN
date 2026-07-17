from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    attempts = relationship("AgentAttempt", back_populates="job", cascade="all, delete-orphan")


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
