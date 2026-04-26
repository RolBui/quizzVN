from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    prompt = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False, default=1)

    exam = relationship("Exam", back_populates="questions")
    options = relationship("ExamQuestionOption", back_populates="question", cascade="all, delete-orphan")
    attempt_answers = relationship("ExamAttemptAnswer", back_populates="question", cascade="all, delete-orphan")
