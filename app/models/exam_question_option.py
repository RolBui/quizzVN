from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ExamQuestionOption(Base):
    __tablename__ = "exam_question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("exam_questions.id"), nullable=False)
    option_key = Column(String, nullable=False)
    option_text = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False)

    question = relationship("ExamQuestion", back_populates="options")
    selected_in_answers = relationship("ExamAttemptAnswer", back_populates="selected_option")
