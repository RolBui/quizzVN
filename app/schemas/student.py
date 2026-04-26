from datetime import datetime
from typing import Literal

from pydantic import BaseModel


StudentScope = Literal["system", "class"]
AttemptStatus = Literal["in_progress", "submitted"]


class StudentClassSchema(BaseModel):
    id: int
    name: str
    description: str | None = None
    join_code: str
    joined_at: datetime
    exam_count: int
    document_count: int


class StudentClassListResponse(BaseModel):
    items: list[StudentClassSchema]


class JoinClassRequest(BaseModel):
    join_code: str


class JoinClassResponse(BaseModel):
    message: str
    classroom: StudentClassSchema


class StudentDocumentSchema(BaseModel):
    id: int
    title: str
    summary: str | None = None
    content: str
    scope: StudentScope
    classroom_id: int | None = None
    classroom_name: str | None = None
    created_at: datetime


class StudentDocumentListResponse(BaseModel):
    items: list[StudentDocumentSchema]


class StudentExamOptionSchema(BaseModel):
    id: int
    option_key: str
    option_text: str


class StudentExamQuestionSchema(BaseModel):
    id: int
    order_index: int
    prompt: str
    points: int
    options: list[StudentExamOptionSchema]


class StudentExamSummarySchema(BaseModel):
    id: int
    title: str
    description: str | None = None
    scope: StudentScope
    classroom_id: int | None = None
    classroom_name: str | None = None
    duration_minutes: int
    total_points: int
    question_count: int
    is_active: bool


class StudentExamListResponse(BaseModel):
    items: list[StudentExamSummarySchema]


class StudentExamDetailSchema(StudentExamSummarySchema):
    questions: list[StudentExamQuestionSchema]
    in_progress_attempt_id: int | None = None


class AttemptSummarySchema(BaseModel):
    id: int
    exam_id: int
    status: AttemptStatus
    score: int | None = None
    total_points: int
    correct_answers_count: int | None = None
    total_questions: int
    answered_count: int
    started_at: datetime
    submitted_at: datetime | None = None


class StartAttemptResponse(BaseModel):
    message: str
    attempt: AttemptSummarySchema


class AttemptAnswerInput(BaseModel):
    question_id: int
    selected_option_id: int | None = None


class SaveAttemptAnswersRequest(BaseModel):
    answers: list[AttemptAnswerInput]


class SaveAttemptAnswersResponse(BaseModel):
    message: str
    attempt: AttemptSummarySchema


class AttemptResultAnswerSchema(BaseModel):
    question_id: int
    prompt: str
    selected_option_id: int | None = None
    selected_option_text: str | None = None
    correct_option_id: int | None = None
    correct_option_text: str | None = None
    is_correct: bool
    points_earned: int
    max_points: int


class AttemptResultSchema(BaseModel):
    attempt_id: int
    exam_id: int
    exam_title: str
    status: AttemptStatus
    score: int
    total_points: int
    correct_answers_count: int
    total_questions: int
    started_at: datetime
    submitted_at: datetime
    answers: list[AttemptResultAnswerSchema]


class SubmitAttemptResponse(BaseModel):
    message: str
    result: AttemptResultSchema


class AttemptResultResponse(BaseModel):
    result: AttemptResultSchema
