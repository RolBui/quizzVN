from datetime import datetime

from pydantic import BaseModel


class UserSchema(BaseModel):
    id: int
    role_id: int
    role_name: str | None = None
    full_name: str
    username: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    auth_type: str
    email_verified: bool
    status: str
    is_first_login: bool
    max_exam_create: int
    max_document_create: int
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SessionSchema(BaseModel):
    id: int
    login_method: str
    ip_address: str | None = None
    user_agent: str | None = None
    is_revoked: bool
    expires_at: datetime
    refresh_expires_at: datetime | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    session_token: str


class GoogleCallbackResponse(BaseModel):
    message: str
    is_new_user: bool
    user: UserSchema
    session: SessionSchema


class MeResponse(BaseModel):
    user: UserSchema
    session: SessionSchema


class RefreshSessionResponse(BaseModel):
    message: str
    session: SessionSchema


class SessionListResponse(BaseModel):
    sessions: list[SessionSchema]


class RevokeSessionResponse(BaseModel):
    message: str
    session: SessionSchema
