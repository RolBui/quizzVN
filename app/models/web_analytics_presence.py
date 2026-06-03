from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class WebAnalyticsPresence(Base):
    __tablename__ = "web_analytics_presence"

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    path = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    origin = Column(Text, nullable=True)
    device_type = Column(String, nullable=False, default="desktop")
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)
    screen_width = Column(Integer, nullable=True)
    screen_height = Column(Integer, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
