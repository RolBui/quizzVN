from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class AdminCrmMetricSchema(BaseModel):
    key: str
    label: str
    value: int
    suffix: str = ""
    trend: str
    is_up: bool
    subtext: str
    sparkline: list[int] = Field(default_factory=list)


class AdminCrmTrafficPointSchema(BaseModel):
    name: str
    current: int
    last: int


class AdminCrmScoreBucketSchema(BaseModel):
    name: str
    users: int


class AdminCrmRecentResultSchema(BaseModel):
    attempt_id: int
    code: str
    student_name: str
    exam_title: str
    submitted_at: datetime
    score_label: str
    score_percent: float
    status: str


class AdminCrmOverviewResponse(BaseModel):
    metrics: list[AdminCrmMetricSchema]
    traffic: list[AdminCrmTrafficPointSchema]
    score_distribution: list[AdminCrmScoreBucketSchema]
    recent_results: list[AdminCrmRecentResultSchema]
    last_updated_at: datetime


AdminAccountRole = Literal["administrator", "admin"]
AdminAccountStatus = Literal["active", "disabled"]


class AdminAccountSchema(BaseModel):
    id: int
    full_name: str
    username: str
    email: str
    role_name: AdminAccountRole
    status: str
    is_online: bool = False
    email_verified: bool
    auth_type: str
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminAccountListResponse(BaseModel):
    items: list[AdminAccountSchema]


class CreateAdminAccountRequest(BaseModel):
    full_name: str
    email: str
    password: str


class AdminAccountResponse(BaseModel):
    message: str
    admin: AdminAccountSchema


class AdminMetricSchema(BaseModel):
    key: str
    label: str
    value: float
    suffix: str = ""
    trend: str = "0%"
    is_up: bool = True
    subtext: str = ""
    sparkline: list[int] = Field(default_factory=list)


class AdminTeacherSchema(BaseModel):
    id: int
    code: str
    full_name: str
    username: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    status: str
    is_online: bool = False
    school_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    class_count: int
    exam_count: int
    document_count: int
    last_login_at: datetime | None = None
    created_at: datetime


class AdminTeacherOverviewResponse(BaseModel):
    metrics: list[AdminMetricSchema]
    items: list[AdminTeacherSchema]


class AdminStudentSchema(BaseModel):
    id: int
    code: str
    full_name: str
    username: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    status: str
    is_online: bool = False
    school_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    class_count: int
    attempt_count: int
    average_score: float | None = None
    last_login_at: datetime | None = None
    created_at: datetime


class AdminStudentOverviewResponse(BaseModel):
    metrics: list[AdminMetricSchema]
    items: list[AdminStudentSchema]


class AdminClassSchema(BaseModel):
    id: int
    name: str
    description: str | None = None
    join_code: str
    teacher_id: int | None = None
    teacher_name: str | None = None
    teacher_avatar_url: str | None = None
    student_count: int
    exam_count: int
    document_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class AdminClassOverviewResponse(BaseModel):
    metrics: list[AdminMetricSchema]
    items: list[AdminClassSchema]


class AdminExamSchema(BaseModel):
    id: int
    title: str
    description: str | None = None
    scope: str
    classroom_id: int | None = None
    classroom_name: str | None = None
    teacher_id: int | None = None
    teacher_name: str | None = None
    duration_minutes: int
    total_points: float
    question_count: int
    attempt_count: int
    average_score: float | None = None
    is_published: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminExamOverviewResponse(BaseModel):
    metrics: list[AdminMetricSchema]
    items: list[AdminExamSchema]


class AdminDocumentSchema(BaseModel):
    id: int
    title: str
    summary: str | None = None
    content_preview: str
    file_url: str | None = None
    file_name: str | None = None
    file_content_type: str | None = None
    file_size_bytes: int | None = None
    scope: str
    classroom_id: int | None = None
    classroom_name: str | None = None
    teacher_id: int | None = None
    teacher_name: str | None = None
    is_published: bool
    content_length: int
    created_at: datetime
    updated_at: datetime


class AdminDocumentOverviewResponse(BaseModel):
    metrics: list[AdminMetricSchema]
    items: list[AdminDocumentSchema]


class AdminTeacherClassDetailSchema(BaseModel):
    id: int
    name: str
    description: str | None = None
    join_code: str
    student_count: int
    exam_count: int
    document_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class AdminStudentClassDetailSchema(BaseModel):
    id: int
    name: str
    description: str | None = None
    join_code: str
    teacher_id: int | None = None
    teacher_name: str | None = None
    student_count: int
    exam_count: int
    document_count: int
    joined_at: datetime | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class AdminStudentAttemptSchema(BaseModel):
    id: int
    exam_id: int
    exam_title: str
    classroom_id: int | None = None
    classroom_name: str | None = None
    score: float | None = None
    total_points: float
    score_percent: float | None = None
    status: str
    started_at: datetime
    submitted_at: datetime | None = None
    created_at: datetime


class AdminTeacherDetailResponse(BaseModel):
    teacher: AdminTeacherSchema
    metrics: list[AdminMetricSchema]
    classes: list[AdminTeacherClassDetailSchema]
    exams: list[AdminExamSchema]
    documents: list[AdminDocumentSchema]


class AdminStudentDetailResponse(BaseModel):
    student: AdminStudentSchema
    metrics: list[AdminMetricSchema]
    classes: list[AdminStudentClassDetailSchema]
    attempts: list[AdminStudentAttemptSchema]
    exams: list[AdminExamSchema]
    documents: list[AdminDocumentSchema]


class UpdateAdminUserProfileRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    school_name: str | None = None
    status: AdminAccountStatus | None = None


class ResetAdminUserPasswordRequest(BaseModel):
    password: str


