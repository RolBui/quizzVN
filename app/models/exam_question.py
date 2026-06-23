from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    question_type = Column(String, nullable=False, default="single_choice")
    prompt = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False, default="")
    image_url = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False)
    points = Column(Numeric(10, 4, asdecimal=False), nullable=False, default=1)

    exam = relationship("Exam", back_populates="questions")
    options = relationship("ExamQuestionOption", back_populates="question", cascade="all, delete-orphan")
    attempt_answers = relationship("ExamAttemptAnswer", back_populates="question", cascade="all, delete-orphan")
