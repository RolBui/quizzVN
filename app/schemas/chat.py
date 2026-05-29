from datetime import datetime

from pydantic import BaseModel, Field


class ChatUserSchema(BaseModel):
    id: int
    full_name: str
    email: str
    avatar_url: str | None = None
    role_name: str | None = None
    school_name: str | None = None
    is_online: bool = False


class ChatMessageSchema(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    sender_name: str
    sender_avatar_url: str | None = None
    body: str
    attachment_url: str | None = None
    attachment_filename: str | None = None
    attachment_content_type: str | None = None
    attachment_size_bytes: int | None = None
    created_at: datetime
    is_own: bool = False


class ChatConversationSchema(BaseModel):
    id: int
    title: str | None = None
    is_group: bool = False
    participants: list[ChatUserSchema]
    last_message: ChatMessageSchema | None = None
    unread_count: int = 0
    updated_at: datetime


class ChatContactListResponse(BaseModel):
    items: list[ChatUserSchema]


class ChatConversationListResponse(BaseModel):
    items: list[ChatConversationSchema]


class CreateChatConversationRequest(BaseModel):
    participant_id: int


class ChatConversationResponse(BaseModel):
    conversation: ChatConversationSchema


class ChatMessageListResponse(BaseModel):
    items: list[ChatMessageSchema]


class CreateChatMessageRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class ShareChatMessageRequest(BaseModel):
    participant_id: int
    body: str | None = Field(default=None, max_length=5000)


class ChatMessageResponse(BaseModel):
    message: ChatMessageSchema
