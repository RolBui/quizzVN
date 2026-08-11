from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


AI_QUESTION_TYPE_VALUES = ("multiple_choice", "true_false", "short_answer", "essay")
AIQuestionType = Literal["multiple_choice", "true_false", "short_answer", "essay"]
AIDifficulty = Literal["easy", "medium", "hard"]
AIExamSaveScope = Literal["system", "class"]
DIFFICULTY_ALIASES = {
    "easy": "easy",
    "medium": "medium",
    "normal": "medium",
    "nomal": "medium",
    "hard": "hard",
}


def _normalize_question_type_distribution(
    question_type_distribution: dict[str, int],
    question_types: list[AIQuestionType],
    question_count: int,
) -> dict[str, int]:
    selected_question_types = list(dict.fromkeys(question_types))
    if not selected_question_types:
        raise ValueError("question_types must not be empty")

    if not question_type_distribution:
        raise ValueError("question_type_distribution is required")

    normalized_distribution = {question_type: 0 for question_type in selected_question_types}
    provided_question_types: set[str] = set()
    for raw_question_type, count in question_type_distribution.items():
        question_type = str(raw_question_type).strip()
        if question_type not in AI_QUESTION_TYPE_VALUES:
            raise ValueError("question_type_distribution keys must be valid question types")
        if question_type not in normalized_distribution:
            raise ValueError("question_type_distribution keys must match question_types")
        if count <= 0:
            raise ValueError("question_type_distribution values must be greater than 0")

        normalized_distribution[question_type] += count
        provided_question_types.add(question_type)

    missing_question_types = [
        question_type
        for question_type in selected_question_types
        if question_type not in provided_question_types
    ]
    if missing_question_types:
        raise ValueError("question_type_distribution must include every selected question type")

    total = sum(normalized_distribution.values())
    if total != question_count:
        raise ValueError("question_type_distribution total must match question_count")

    return normalized_distribution


class GenerateExamRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=150)
    topic: str = Field(min_length=1, max_length=500)
    duration_minutes: int = Field(gt=0, le=300)
    question_count: int = Field(ge=1, le=50)
    question_types: list[AIQuestionType] = Field(min_length=1)
    question_type_distribution: dict[str, int] = Field(min_length=1)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    language: str = Field(default="Vietnamese", min_length=1, max_length=50)
    additional_instructions: str = Field(default="", max_length=1000)

    @field_validator("subject", "grade", "topic", "language", "additional_instructions")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("question_types")
    @classmethod
    def unique_question_types(cls, value: list[AIQuestionType]) -> list[AIQuestionType]:
        unique_values = list(dict.fromkeys(value))
        if not unique_values:
            raise ValueError("question_types must not be empty")
        return unique_values

    @model_validator(mode="after")
    def validate_question_type_distribution(self) -> "GenerateExamRequest":
        self.question_type_distribution = _normalize_question_type_distribution(
            self.question_type_distribution,
            self.question_types,
            self.question_count,
        )
        return self

    @model_validator(mode="after")
    def validate_difficulty_distribution(self) -> "GenerateExamRequest":
        if not self.difficulty_distribution:
            self.difficulty_distribution = {
                "easy": 40,
                "medium": 40,
                "hard": 20,
            }

        normalized_distribution = {
            "easy": 0,
            "medium": 0,
            "hard": 0,
        }
        for difficulty, value in self.difficulty_distribution.items():
            normalized_difficulty = DIFFICULTY_ALIASES.get(str(difficulty).strip().lower())
            if normalized_difficulty is None:
                raise ValueError("difficulty_distribution keys must be easy, medium, or hard")
            normalized_distribution[normalized_difficulty] += value

        negative_keys = [
            difficulty
            for difficulty, value in normalized_distribution.items()
            if value < 0
        ]
        if negative_keys:
            raise ValueError("difficulty_distribution values must be greater than or equal to 0")

        total = sum(normalized_distribution.values())
        if total not in {100, self.question_count}:
            raise ValueError("difficulty_distribution total must be 100 or match question_count")

        self.difficulty_distribution = normalized_distribution
        return self


class GenerateMoreQuestionsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_count: int = Field(alias="count", ge=1, le=50)
    question_types: list[AIQuestionType] | None = None
    question_type_distribution: dict[str, int] = Field(default_factory=dict)
    difficulty_distribution: dict[str, int] = Field(default_factory=dict)
    additional_instructions: str = Field(default="", max_length=1000)

    @field_validator("question_types")
    @classmethod
    def unique_optional_question_types(
        cls,
        value: list[AIQuestionType] | None,
    ) -> list[AIQuestionType] | None:
        if value is None:
            return None
        unique_values = list(dict.fromkeys(value))
        if not unique_values:
            raise ValueError("question_types must not be empty")
        return unique_values

    @field_validator("additional_instructions")
    @classmethod
    def strip_more_instructions(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_more_question_type_distribution(self) -> "GenerateMoreQuestionsRequest":
        if not self.question_types and not self.question_type_distribution:
            return self

        if not self.question_types:
            self.question_types = [
                str(question_type).strip()
                for question_type in self.question_type_distribution
            ]

        self.question_type_distribution = _normalize_question_type_distribution(
            self.question_type_distribution,
            self.question_types,
            self.question_count,
        )
        return self

    @model_validator(mode="after")
    def validate_more_difficulty_distribution(self) -> "GenerateMoreQuestionsRequest":
        if not self.difficulty_distribution:
            return self

        normalized_distribution = {
            "easy": 0,
            "medium": 0,
            "hard": 0,
        }
        for difficulty, value in self.difficulty_distribution.items():
            normalized_difficulty = DIFFICULTY_ALIASES.get(str(difficulty).strip().lower())
            if normalized_difficulty is None:
                raise ValueError("difficulty_distribution keys must be easy, medium, or hard")
            normalized_distribution[normalized_difficulty] += value

        negative_keys = [
            difficulty
            for difficulty, value in normalized_distribution.items()
            if value < 0
        ]
        if negative_keys:
            raise ValueError("difficulty_distribution values must be greater than or equal to 0")

        total = sum(normalized_distribution.values())
        if total not in {100, self.question_count}:
            raise ValueError("difficulty_distribution total must be 100 or match count")

        self.difficulty_distribution = normalized_distribution
        return self


class AIQuestionDraftResponse(BaseModel):
    id: int
    question_type: AIQuestionType
    content: str
    options: list[str]
    correct_answer: Any | None = None
    explanation: str
    difficulty: AIDifficulty
    points: float
    topic: str
    order: int
    is_approved: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AIExamGenerationJobResponse(BaseModel):
    id: int
    status: str
    subject: str
    grade: str
    topic: str
    duration_minutes: int
    question_count: int
    question_types: list[AIQuestionType]
    question_type_distribution: dict[str, int]
    difficulty_distribution: dict[str, int]
    language: str
    additional_instructions: str
    title: str | None = None
    description: str | None = None
    total_points: float
    provider: str
    model: str
    agent_job_id: str | None = None
    agent_operation: str | None = None
    agent_result_status: str = "none"
    agent_stage: str = "none"
    agent_progress_current: int = 0
    agent_progress_total: int = 0
    agent_progress_message: str = ""
    qc_reserved: int = 0
    qc_charged: int = 0
    qc_refunded: int = 0
    free_questions_used: int = 0
    qc_status: str = "none"
    error_message: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    question_drafts: list[AIQuestionDraftResponse]


class UpdateAIQuestionDraftRequest(BaseModel):
    question_type: AIQuestionType | None = None
    content: str | None = Field(default=None, max_length=5000)
    options: list[str] | None = None
    correct_answer: Any | None = None
    explanation: str | None = Field(default=None, max_length=5000)
    difficulty: AIDifficulty | None = None
    points: float | None = Field(default=None, gt=0)
    topic: str | None = Field(default=None, max_length=255)
    is_approved: bool | None = None

    @field_validator("content", "explanation", "topic")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class SaveAIExamToQuizRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=2000)
    scope: AIExamSaveScope = "system"
    classroom_id: int | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=300)
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_published: bool = False
    is_active: bool = True

    @field_validator("title", "description", "image_url")
    @classmethod
    def strip_optional_save_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class SaveAIExamToQuizResponse(BaseModel):
    quiz_id: int
    exam_id: int
    message: str
