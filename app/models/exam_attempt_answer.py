from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ExamAttemptAnswer(Base):
    __tablename__ = "exam_attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_exam_attempt_answers_attempt_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("exam_questions.id"), nullable=False)
    selected_option_id = Column(Integer, ForeignKey("exam_question_options.id"), nullable=True)
    answer_text = Column(Text, nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    attempt = relationship("ExamAttempt", back_populates="answers")
    question = relationship("ExamQuestion", back_populates="attempt_answers")
    selected_option = relationship("ExamQuestionOption", back_populates="selected_in_answers")
