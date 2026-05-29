from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UploadedImage(Base):
    __tablename__ = "uploaded_images"

    id = Column(Integer, primary_key=True, index=True)
    uploaded_by_user_id = Column(Integer, nullable=False, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    public_id = Column(String, nullable=False, unique=True)
    url = Column(Text, nullable=False)
    category = Column(String, nullable=False, default="exam")  # exam, avatar, document, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
