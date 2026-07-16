from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AIExamGenerationJob(Base):
    __tablename__ = "ai_exam_generation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("exams.id", ondelete="SET NULL"), nullable=True)

    subject = Column(String(100), nullable=False)
    grade = Column(String(50), nullable=False)
    topic = Column(Text, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    question_count = Column(Integer, nullable=False)
    question_types = Column(JSON, nullable=False, default=list)
    question_type_distribution = Column(JSON, nullable=False, default=dict)
    difficulty_distribution = Column(JSON, nullable=False, default=dict)
    language = Column(String(50), nullable=False, default="Vietnamese")
    additional_instructions = Column(Text, nullable=False, default="")

    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    total_points = Column(Numeric(10, 4, asdecimal=False), nullable=False, default=0)

    status = Column(String(30), nullable=False, default="pending")
    prompt = Column(Text, nullable=False, default="")
    raw_response = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=False, default="")

    provider = Column(String(50), nullable=False, default="")
    model = Column(String(100), nullable=False, default="")

    qc_reserved = Column(Integer, nullable=False, default=0)
    qc_charged = Column(Integer, nullable=False, default=0)
    qc_refunded = Column(Integer, nullable=False, default=0)
    free_questions_used = Column(Integer, nullable=False, default=0)
    qc_status = Column(String(30), nullable=False, default="none")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    question_drafts = relationship(
        "AIQuestionDraft",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class AIQuestionDraft(Base):
    __tablename__ = "ai_question_drafts"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("ai_exam_generation_jobs.id"), nullable=False, index=True)

    question_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    options = Column(JSON, nullable=False, default=list)
    correct_answer = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=False, default="")
    difficulty = Column(String(30), nullable=False, default="medium")
    points = Column(Numeric(10, 4, asdecimal=False), nullable=False, default=1)
    topic = Column(String(255), nullable=False, default="")
    order = Column("order_index", Integer, nullable=False, default=0)
    is_approved = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job = relationship("AIExamGenerationJob", back_populates="question_drafts")
