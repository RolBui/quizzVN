from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    join_code = Column(String, nullable=False, unique=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    memberships = relationship("ClassroomMembership", back_populates="classroom", cascade="all, delete-orphan")
    documents = relationship("LearningDocument", back_populates="classroom", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="classroom", cascade="all, delete-orphan")
