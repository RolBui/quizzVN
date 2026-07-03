from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TeacherScope = Literal["system", "class"]
TeacherQuestionType = Literal["single_choice", "true_false", "short_answer", "text"]
TeacherAttemptStatus = Literal["in_progress", "submitted"]


class TeacherClassSchema(BaseModel):
    id: int
    name: str
    description: str | None = None
    join_code: str
    student_count: int
    exam_count: int
    document_count: int
    created_at: datetime


class TeacherClassListResponse(BaseModel):
    items: list[TeacherClassSchema]


class CreateTeacherClassRequest(BaseModel):
    name: str
    description: str | None = None
    join_code: str | None = None


class UpdateTeacherClassRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    join_code: str | None = None


class TeacherClassResponse(BaseModel):
    message: str
    classroom: TeacherClassSchema


class TeacherStudentSchema(BaseModel):
    id: int
    full_name: str
    username: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    gender: str | None = None
    school_name: str | None = None
    joined_at: datetime | None = None


class TeacherStudentListResponse(BaseModel):
    items: list[TeacherStudentSchema]


class AddTeacherStudentRequest(BaseModel):
    student_id: int


class TeacherStudentResponse(BaseModel):
    message: str
    student: TeacherStudentSchema


class TeacherDocumentSchema(BaseModel):
    id: int
    title: str
    summary: str | None = None
    content: str
    file_url: str | None = None
    file_name: str | None = None
    file_content_type: str | None = None
    file_size_bytes: int | None = None
    scope: TeacherScope
    classroom_id: int | None = None
    classroom_name: str | None = None
    is_published: bool
    created_at: datetime
    updated_at: datetime


class TeacherDocumentListResponse(BaseModel):
    items: list[TeacherDocumentSchema]


class TeacherDocumentResponse(BaseModel):
    message: str
    document: TeacherDocumentSchema


class TeacherExamOptionSchema(BaseModel):
    id: int
    option_key: str
    option_text: str
    image_url: str | None = None
    is_correct: bool


class TeacherExamQuestionSchema(BaseModel):
    id: int
    question_type: TeacherQuestionType
    order_index: int
    prompt: str
    explanation: str = ""
    image_url: str | None = None
    points: float
    options: list[TeacherExamOptionSchema]
    accepted_answers: list[str]


class TeacherExamSummarySchema(BaseModel):
    id: int
    title: str
    description: str | None = None
    grade: str
    image_url: str | None = None
    scope: TeacherScope
    classroom_id: int | None = None
    classroom_name: str | None = None
    duration_minutes: int
    total_points: float
    question_count: int
    attempt_count: int
    is_published: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TeacherExamListResponse(BaseModel):
    items: list[TeacherExamSummarySchema]


class TeacherExamDetailSchema(TeacherExamSummarySchema):
    questions: list[TeacherExamQuestionSchema]


class TeacherExamResultSummarySchema(BaseModel):
    submitted_count: int
    average_score_percent: float


class TeacherExamResultListItemSchema(BaseModel):
    attempt_id: int
    student_id: int
    student_name: str
    student_email: str
    student_avatar_url: str | None = None
    score: float
    total_points: float
    score_percent: float
    correct_answers_count: int
    total_questions: int
    is_passed: bool
    started_at: datetime
    submitted_at: datetime


class TeacherExamResultListResponse(BaseModel):
    summary: TeacherExamResultSummarySchema
    items: list[TeacherExamResultListItemSchema]


class TeacherExamAttemptAnswerSchema(BaseModel):
    question_id: int
    question_type: TeacherQuestionType
    prompt: str
    explanation: str | None = None
    question_image_url: str | None = None
    selected_option_id: int | None = None
    selected_option_text: str | None = None
    selected_option_image_url: str | None = None
    submitted_answer_text: str | None = None
    correct_option_id: int | None = None
    correct_option_text: str | None = None
    correct_option_image_url: str | None = None
    accepted_answers: list[str]
    is_correct: bool
    points_earned: float
    max_points: float


class TeacherExamAttemptResultSchema(BaseModel):
    attempt_id: int
    exam_id: int
    exam_title: str
    status: TeacherAttemptStatus
    student_id: int
    student_name: str
    student_email: str
    student_avatar_url: str | None = None
    score: float
    total_points: float
    score_percent: float
    correct_answers_count: int
    total_questions: int
    started_at: datetime
    submitted_at: datetime
    answers: list[TeacherExamAttemptAnswerSchema]


class TeacherExamAttemptResultResponse(BaseModel):
    result: TeacherExamAttemptResultSchema


class TeacherExamOptionInput(BaseModel):
    option_key: str
    option_text: str = ""
    image_url: str | None = None
    is_correct: bool = False


class TeacherExamQuestionInput(BaseModel):
    question_type: TeacherQuestionType = "single_choice"
    prompt: str = ""
    explanation: str = ""
    image_url: str | None = None
    order_index: int | None = None
    points: float = Field(default=1.0, gt=0)
    options: list[TeacherExamOptionInput] = Field(default_factory=list)
    accepted_answers: list[str] = Field(default_factory=list)


class CreateTeacherExamRequest(BaseModel):
    title: str
    description: str | None = None
    grade: str = Field(min_length=1, max_length=50)
    image_url: str | None = None
    duration_minutes: int = Field(default=30, ge=1)
    is_published: bool = False
    is_active: bool = False
    questions: list[TeacherExamQuestionInput]


class UpdateTeacherExamRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    grade: str | None = Field(default=None, min_length=1, max_length=50)
    image_url: str | None = None
    scope: TeacherScope | None = None
    classroom_id: int | None = None
    duration_minutes: int | None = Field(default=None, ge=1)
    is_published: bool | None = None
    is_active: bool | None = None
    questions: list[TeacherExamQuestionInput] | None = None


class UpdateTeacherClassExamRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    grade: str | None = Field(default=None, min_length=1, max_length=50)
    image_url: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1)
    is_published: bool | None = None
    is_active: bool | None = None
    questions: list[TeacherExamQuestionInput] | None = None


class TeacherExamResponse(BaseModel):
    message: str
    exam: TeacherExamDetailSchema


class TeacherUploadedImageSchema(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    public_id: str
    url: str
    created_at: str | None = None


class TeacherImageUploadResponse(BaseModel):
    message: str
    image: TeacherUploadedImageSchema


class TeacherImageListResponse(BaseModel):
    items: list[TeacherUploadedImageSchema]
