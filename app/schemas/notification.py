from datetime import datetime
from pydantic import BaseModel, Field


class NotificationBase(BaseModel):
    title: str
    description: str
    type: str = "system"
    link_to: str | None = None


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationSchema(BaseModel):
    id: str
    title: str
    description: str
    type: str
    unread: bool
    link_to: str | None = None
    time: str

    class Config:
        from_attributes = True
