# app/models/oauth_provider.py
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class OAuthProvider(Base):
    __tablename__ = "oauth_providers"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    oauth_accounts = relationship("OAuthAccount", back_populates="provider")
