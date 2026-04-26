# user của hệ thống
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    full_name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    auth_type = Column(String, nullable=False, default="oauth")
    email_verified = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="active")
    is_first_login = Column(Boolean, nullable=False, default=True)
    max_exam_create = Column(Integer, nullable=False, default=50)
    max_document_create = Column(Integer, nullable=False, default=50)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    role = relationship("Role", back_populates="users")
    oauth_accounts = relationship("OAuthAccount", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    classroom_memberships = relationship(
        "ClassroomMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    exam_attempts = relationship(
        "ExamAttempt",
        back_populates="user",
        cascade="all, delete-orphan",
    )
