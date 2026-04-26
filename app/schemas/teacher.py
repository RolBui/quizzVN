from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TeacherScope = Literal["system", "class"]


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
    scope: TeacherScope
    classroom_id: int | None = None
    classroom_name: str | None = None
    is_published: bool
    created_at: datetime
    updated_at: datetime


class TeacherDocumentListResponse(BaseModel):
    items: list[TeacherDocumentSchema]


class CreateTeacherDocumentRequest(BaseModel):
    title: str
    summary: str | None = None
    content: str
    scope: TeacherScope
    classroom_id: int | None = None
    is_published: bool = False


class UpdateTeacherDocumentRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    scope: TeacherScope | None = None
    classroom_id: int | None = None
    is_published: bool | None = None


class TeacherDocumentResponse(BaseModel):
    message: str
    document: TeacherDocumentSchema


class TeacherExamOptionSchema(BaseModel):
    id: int
    option_key: str
    option_text: str
    is_correct: bool


class TeacherExamQuestionSchema(BaseModel):
    id: int
    order_index: int
    prompt: str
    points: int
    options: list[TeacherExamOptionSchema]


class TeacherExamSummarySchema(BaseModel):
    id: int
    title: str
    description: str | None = None
    scope: TeacherScope
    classroom_id: int | None = None
    classroom_name: str | None = None
    duration_minutes: int
    total_points: int
    question_count: int
    attempt_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TeacherExamListResponse(BaseModel):
    items: list[TeacherExamSummarySchema]


class TeacherExamDetailSchema(TeacherExamSummarySchema):
    questions: list[TeacherExamQuestionSchema]


class TeacherExamOptionInput(BaseModel):
    option_key: str
    option_text: str
    is_correct: bool = False


class TeacherExamQuestionInput(BaseModel):
    prompt: str
    order_index: int | None = None
    points: int = Field(default=1, ge=1)
    options: list[TeacherExamOptionInput]


class CreateTeacherExamRequest(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int = Field(default=30, ge=1)
    is_active: bool = False
    questions: list[TeacherExamQuestionInput]


class UpdateTeacherExamRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    scope: TeacherScope | None = None
    classroom_id: int | None = None
    duration_minutes: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    questions: list[TeacherExamQuestionInput] | None = None


class TeacherExamResponse(BaseModel):
    message: str
    exam: TeacherExamDetailSchema
