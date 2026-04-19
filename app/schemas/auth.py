from datetime import date, datetime

from pydantic import BaseModel
from typing import Literal


class UserProfileSchema(BaseModel):
    date_of_birth: date
    age: int
    gender: Literal["male", "female", "other"]
    school_name: str | None = None
    onboarding_completed_at: datetime


class RoleOptionSchema(BaseModel):
    id: int
    name: Literal["teacher", "student"]
    display_name: str
    required_fields: list[str]


class UserSchema(BaseModel):
    id: int
    role_id: int | None = None
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
    needs_onboarding: bool
    profile: UserProfileSchema | None = None


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


class GoogleCallbackResponse(BaseModel):
    message: str
    is_new_user: bool
    user: UserSchema
    session: SessionSchema


class AuthSessionResponse(BaseModel):
    message: str
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


class RoleListResponse(BaseModel):
    roles: list[RoleOptionSchema]


class CompleteOnboardingRequest(BaseModel):
    role: Literal["teacher", "student"]
    full_name: str
    date_of_birth: date
    gender: Literal["male", "female", "other"]
    school_name: str | None = None


class CompleteOnboardingResponse(BaseModel):
    message: str
    user: UserSchema


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str
