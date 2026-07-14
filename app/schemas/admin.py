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
AdminInvitationStatus = Literal["otp_pending", "pending_approval", "approved", "rejected", "expired"]


class AdminAccountSchema(BaseModel):
    id: int
    full_name: str
    username: str
    email: str
    role_name: AdminAccountRole
    status: str
    is_online: bool = False
    admin_permissions: list[str] = []
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


class AdminInvitationSchema(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    status: AdminInvitationStatus
    otp_expires_at: datetime
    invited_by_user_id: int | None = None
    invited_by_name: str | None = None
    invited_by_email: str | None = None
    submitted_at: datetime | None = None
    approved_by_user_id: int | None = None
    approved_at: datetime | None = None
    rejected_by_user_id: int | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    generated_user_id: int | None = None
    created_at: datetime
    updated_at: datetime


class AdminInvitationListResponse(BaseModel):
    items: list[AdminInvitationSchema]


class CreateAdminInvitationRequest(BaseModel):
    email: str


class SendAdminInvitationOtpRequest(BaseModel):
    token: str
    email: str
    full_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None


class VerifyAdminInvitationOtpRequest(BaseModel):
    token: str
    email: str
    otp_code: str
    full_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None


class ApproveAdminInvitationRequest(BaseModel):
    permissions: list[str] = Field(default_factory=list)


class RejectAdminInvitationRequest(BaseModel):
    reason: str | None = None


class AdminInvitationResponse(BaseModel):
    message: str
    invitation: AdminInvitationSchema


class ApproveAdminInvitationResponse(BaseModel):
    message: str
    invitation: AdminInvitationSchema
    admin: AdminAccountSchema


class UpdateAdminPermissionsRequest(BaseModel):
    permissions: list[str] = Field(default_factory=list)


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
    grade: str
    scope: str
    classroom_id: int | None = None
    classroom_name: str | None = None
    teacher_id: int | None = None
    teacher_name: str | None = None
    creator_id: int | None = None
    creator_name: str = "Hệ thống"
    creator_type: str = "system"
    source: str = "system"
    source_label: str = "Hệ thống tạo"
    is_ai_generated: bool = False
    duration_minutes: int
    start_time: datetime | None = None
    end_time: datetime | None = None
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
    total: int = 0
    limit: int | None = None
    offset: int = 0


AdminQuestionType = Literal["single_choice", "true_false", "short_answer", "text"]
AdminExamScope = Literal["system", "class"]


class AdminExamOptionInput(BaseModel):
    option_key: str
    option_text: str = ""
    image_url: str | None = None
    is_correct: bool = False


class AdminExamQuestionInput(BaseModel):
    question_type: AdminQuestionType = "single_choice"
    prompt: str = ""
    explanation: str = ""
    image_url: str | None = None
    order_index: int | None = None
    points: float = Field(default=1.0, gt=0)
    options: list[AdminExamOptionInput] = Field(default_factory=list)
    accepted_answers: list[str] = Field(default_factory=list)


class CreateAdminExamRequest(BaseModel):
    title: str
    description: str | None = None
    grade: str = Field(min_length=1, max_length=50)
    image_url: str | None = None
    scope: AdminExamScope = "system"
    classroom_id: int | None = None
    duration_minutes: int = Field(default=30, ge=1)
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_published: bool = False
    is_active: bool = False
    questions: list[AdminExamQuestionInput]


class AdminExamResponse(BaseModel):
    message: str
    exam: AdminExamSchema


class AdminUploadedImageSchema(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    public_id: str
    url: str
    created_at: str | None = None


class AdminImageUploadResponse(BaseModel):
    message: str
    image: AdminUploadedImageSchema


class AdminImageListResponse(BaseModel):
    items: list[AdminUploadedImageSchema]


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


class AdminDocumentResponse(BaseModel):
    message: str
    document: AdminDocumentSchema


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


