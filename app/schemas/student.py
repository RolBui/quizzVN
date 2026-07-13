from datetime import datetime
from typing import Literal

from pydantic import BaseModel


StudentScope = Literal["system", "class"]
AttemptStatus = Literal["in_progress", "submitted"]
StudentQuestionType = Literal["single_choice", "true_false", "short_answer", "text"]


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
    file_url: str | None = None
    file_name: str | None = None
    file_content_type: str | None = None
    file_size_bytes: int | None = None
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
    image_url: str | None = None


class StudentExamQuestionSchema(BaseModel):
    id: int
    question_type: StudentQuestionType
    order_index: int
    prompt: str
    image_url: str | None = None
    points: float
    options: list[StudentExamOptionSchema]


class StudentExamSummarySchema(BaseModel):
    id: int
    title: str
    description: str | None = None
    grade: str
    image_url: str | None = None
    scope: StudentScope
    classroom_id: int | None = None
    classroom_name: str | None = None
    duration_minutes: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    total_points: float
    question_count: int
    is_active: bool


class StudentExamListResponse(BaseModel):
    items: list[StudentExamSummarySchema]
    total: int = 0
    limit: int | None = None
    offset: int = 0


class StudentExamDetailSchema(StudentExamSummarySchema):
    questions: list[StudentExamQuestionSchema]
    in_progress_attempt_id: int | None = None


class StudentExamResultSummarySchema(BaseModel):
    total_completed_exams: int
    passed_exams: int
    average_score_percent: float


class StudentExamResultListItemSchema(BaseModel):
    attempt_id: int
    exam_id: int
    exam_title: str
    exam_description: str | None = None
    exam_grade: str
    exam_image_url: str | None = None
    scope: StudentScope
    classroom_id: int | None = None
    classroom_name: str | None = None
    score: float
    total_points: float
    score_percent: float
    correct_answers_count: int
    total_questions: int
    is_passed: bool
    started_at: datetime
    submitted_at: datetime


class StudentExamResultListResponse(BaseModel):
    summary: StudentExamResultSummarySchema
    items: list[StudentExamResultListItemSchema]


class AttemptSummarySchema(BaseModel):
    id: int
    exam_id: int
    status: AttemptStatus
    score: float | None = None
    total_points: float
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
    answer_text: str | None = None


class SaveAttemptAnswersRequest(BaseModel):
    answers: list[AttemptAnswerInput]


class SaveAttemptAnswersResponse(BaseModel):
    message: str
    attempt: AttemptSummarySchema


class AttemptResultAnswerSchema(BaseModel):
    question_id: int
    question_type: StudentQuestionType
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


class AttemptResultSchema(BaseModel):
    attempt_id: int
    exam_id: int
    exam_title: str
    exam_grade: str
    exam_image_url: str | None = None
    status: AttemptStatus
    score: float
    total_points: float
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
