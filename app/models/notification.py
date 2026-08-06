from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    type = Column(String(30), nullable=False, default="system")
    is_read = Column(Boolean, nullable=False, default=False)
    link_to = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="notifications")
