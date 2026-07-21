import re
from typing import Any

from ai_agent.normalization import normalize_exam_payload


ALLOWED_QUESTION_TYPES = {"multiple_choice", "true_false", "short_answer", "essay"}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


def validate_exam_payload(
    payload: dict[str, Any],
    request_data: dict[str, Any],
    existing_questions: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    normalized = normalize_exam_payload(payload)
    errors: list[str] = []

    if not isinstance(normalized, dict):
        return normalized, ["AI response root must be an object"]

    for field in ("title", "subject", "grade"):
        if not _text(normalized.get(field)):
            errors.append(f"{field} is required")

    duration = _number(normalized.get("duration_minutes"))
    if duration is None or duration <= 0:
        errors.append("duration_minutes must be greater than 0")
    expected_duration = _number(request_data.get("duration_minutes"))
    if (
        duration is not None
        and expected_duration is not None
        and duration != expected_duration
    ):
        errors.append(
            f"Expected duration_minutes {expected_duration:g}, got {duration:g}"
        )

    questions = normalized.get("questions")
    if not isinstance(questions, list):
        return normalized, errors + ["questions must be a list"]

    expected_count = int(request_data.get("question_count") or 0)
    if len(questions) != expected_count:
        errors.append(f"Expected {expected_count} questions, got {len(questions)}")

    allowed_types = set(request_data.get("question_types") or ALLOWED_QUESTION_TYPES)
    expected_types = {
        str(question_type): int(count or 0)
        for question_type, count in (request_data.get("question_type_distribution") or {}).items()
    }
    actual_types = {question_type: 0 for question_type in expected_types}
    expected_difficulties = {
        str(difficulty): int(count or 0)
        for difficulty, count in (request_data.get("difficulty_distribution") or {}).items()
    }
    actual_difficulties = {difficulty: 0 for difficulty in expected_difficulties}
    seen = {
        _content_key(question.get("content"))
        for question in (existing_questions or [])
        if isinstance(question, dict) and _content_key(question.get("content"))
    }
    total_points = 0.0

    for index, question in enumerate(questions, start=1):
        errors.extend(validate_question(question, index, allowed_types))
        if not isinstance(question, dict):
            continue

        question_type = _text(question.get("type"))
        if question_type in actual_types:
            actual_types[question_type] += 1
        difficulty = _text(question.get("difficulty"))
        if difficulty in actual_difficulties:
            actual_difficulties[difficulty] += 1

        content_key = _content_key(question.get("content"))
        if content_key:
            if content_key in seen:
                errors.append(f"Question {index}: duplicate content")
            seen.add(content_key)
        total_points += _number(question.get("points")) or 0.0

    if total_points <= 0:
        errors.append("total points must be greater than 0")
    else:
        normalized["total_points"] = total_points

    for question_type, expected in expected_types.items():
        actual = actual_types.get(question_type, 0)
        if actual != expected:
            errors.append(f"Expected {expected} {question_type} questions, got {actual}")

    if sum(expected_difficulties.values()) == expected_count:
        for difficulty, expected in expected_difficulties.items():
            actual = actual_difficulties.get(difficulty, 0)
            if actual != expected:
                errors.append(f"Expected {expected} {difficulty} questions, got {actual}")

    return normalized, errors


def validate_question(
    question: Any,
    index: int,
    allowed_types: set[str],
) -> list[str]:
    if not isinstance(question, dict):
        return [f"Question {index}: must be an object"]

    errors: list[str] = []
    question_type = _text(question.get("type"))
    if question_type not in ALLOWED_QUESTION_TYPES:
        errors.append(f"Question {index}: invalid type")
    elif question_type not in allowed_types:
        errors.append(f"Question {index}: type is not allowed by request")

    if not _text(question.get("content")):
        errors.append(f"Question {index}: content is required")
    if not _text(question.get("explanation")):
        errors.append(f"Question {index}: explanation is required")
    if _text(question.get("difficulty")) not in ALLOWED_DIFFICULTIES:
        errors.append(f"Question {index}: difficulty must be easy, medium, or hard")
    if not _text(question.get("topic")):
        errors.append(f"Question {index}: topic is required")

    points = _number(question.get("points"))
    if points is None or points <= 0:
        errors.append(f"Question {index}: points must be greater than 0")

    if question_type == "multiple_choice":
        options = question.get("options")
        if not isinstance(options, list):
            errors.append(f"Question {index}: multiple_choice options must be a list")
        else:
            normalized_options = [_text(option) for option in options]
            if len(normalized_options) != 4:
                errors.append(f"Question {index}: multiple_choice must have exactly 4 options")
            if any(not option for option in normalized_options):
                errors.append(f"Question {index}: options cannot be empty")
            if len(set(normalized_options)) != len(normalized_options):
                errors.append(f"Question {index}: options must be unique")
            answer = _text(question.get("correct_answer"))
            if not answer:
                errors.append(f"Question {index}: correct_answer is required")
            elif answer not in normalized_options:
                errors.append(f"Question {index}: correct_answer is not in options")
    elif question_type == "true_false":
        if not isinstance(question.get("correct_answer"), bool):
            errors.append(f"Question {index}: true_false correct_answer must be true or false")
        options = question.get("options")
        if options not in (None, []):
            errors.append(f"Question {index}: true_false options must be an empty list")
    elif question_type == "short_answer":
        options = question.get("options")
        if options not in (None, []):
            errors.append(f"Question {index}: short_answer options must be an empty list")
        answer = question.get("correct_answer")
        if not (
            isinstance(answer, str) and answer.strip()
        ) and not (
            isinstance(answer, list) and any(_text(item) for item in answer)
        ):
            errors.append(f"Question {index}: short_answer correct_answer is required")
    elif question_type == "essay":
        options = question.get("options")
        if options not in (None, []):
            errors.append(f"Question {index}: essay options must be an empty list")

    return errors


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _content_key(value: Any) -> str:
    return _text(value).casefold()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
