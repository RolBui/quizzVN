from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class LearningDocument(Base):
    __tablename__ = "learning_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False, default="")
    file_url = Column(Text, nullable=True)
    file_name = Column(String, nullable=True)
    file_content_type = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    file_public_id = Column(String, nullable=True)
    scope = Column(String, nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_published = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    classroom = relationship("Classroom", back_populates="documents")
