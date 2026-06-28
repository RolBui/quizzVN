import copy
import re
from typing import Any


ALLOWED_QUESTION_TYPES = {"multiple_choice", "true_false", "short_answer", "essay"}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
PHONETIC_PROPER_NOUN_REPLACEMENTS = (
    (
        re.compile(
            "(?<!\\w)In[-\\s](?:\\u0111\\u00f4|d\\u00f4|do)[-\\s]n(?:\\u00ea|e)[-\\s]xi[-\\s]a(?!\\w)",
            re.IGNORECASE,
        ),
        "Indonesia",
    ),
    (
        re.compile(
            "(?<!\\w)Phi[-\\s]l(?:\\u00ed|i)p[-\\s]pin(?!\\w)",
            re.IGNORECASE,
        ),
        "Philippines",
    ),
    (
        re.compile("(?<!\\w)Ma[-\\s]lai[-\\s]xi[-\\s]a(?!\\w)", re.IGNORECASE),
        "Malaysia",
    ),
    (
        re.compile("(?<!\\w)Xin[-\\s]ga[-\\s]po(?!\\w)", re.IGNORECASE),
        "Singapore",
    ),
)


def validate_ai_exam_payload(
    payload: dict[str, Any],
    request_data: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not isinstance(payload, dict):
        return False, ["AI response root must be an object"]

    for field in ("title", "subject", "grade"):
        if not _normalize_text(payload.get(field)):
            errors.append(f"{field} is required")

    duration_minutes = _to_float(payload.get("duration_minutes"))
    if duration_minutes is None or duration_minutes <= 0:
        errors.append("duration_minutes must be greater than 0")

    declared_total_points = _to_float(payload.get("total_points"))
    if declared_total_points is None or declared_total_points <= 0:
        errors.append("total_points must be greater than 0")

    questions = payload.get("questions")
    if not isinstance(questions, list):
        return False, ["questions must be a list"]

    expected_question_count = request_data.get("question_count")
    if len(questions) != expected_question_count:
        errors.append(
            f"Expected {expected_question_count} questions, got {len(questions)}"
        )

    allowed_request_types = set(request_data.get("question_types") or [])
    if not allowed_request_types:
        allowed_request_types = ALLOWED_QUESTION_TYPES

    expected_type_distribution = request_data.get("question_type_distribution") or {}
    actual_type_distribution = {
        question_type: 0
        for question_type in expected_type_distribution
    }

    seen_content: set[str] = set()
    total_points = 0.0
    for index, question in enumerate(questions, start=1):
        errors.extend(validate_ai_question_payload(question, index, allowed_request_types))
        if isinstance(question, dict):
            question_type = _normalize_text(question.get("type"))
            if question_type in actual_type_distribution:
                actual_type_distribution[question_type] += 1

            normalized_content = _normalize_text(question.get("content")).lower()
            if normalized_content:
                if normalized_content in seen_content:
                    errors.append(f"Question {index}: duplicate content")
                seen_content.add(normalized_content)
            total_points += _to_float(question.get("points"), default=0.0)

    if total_points <= 0:
        errors.append("total points must be greater than 0")

    for question_type, expected_count in expected_type_distribution.items():
        actual_count = actual_type_distribution.get(question_type, 0)
        if actual_count != expected_count:
            errors.append(
                f"Expected {expected_count} {question_type} questions, got {actual_count}"
            )

    return not errors, errors


def sanitize_ai_exam_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized_payload = copy.deepcopy(payload)
    if not isinstance(sanitized_payload, dict):
        return sanitized_payload

    for field in ("title", "description", "subject", "grade"):
        if isinstance(sanitized_payload.get(field), str):
            sanitized_payload[field] = sanitize_ai_text(sanitized_payload[field])

    questions = sanitized_payload.get("questions")
    if not isinstance(questions, list):
        return sanitized_payload

    for question in questions:
        if not isinstance(question, dict):
            continue

        for field in ("content", "explanation", "difficulty", "topic", "type"):
            if isinstance(question.get(field), str):
                question[field] = sanitize_ai_text(question[field])

        options = question.get("options")
        if isinstance(options, list):
            question["options"] = [
                sanitize_ai_text(option) if isinstance(option, str) else option
                for option in options
            ]

        correct_answer = question.get("correct_answer")
        if isinstance(correct_answer, str):
            question["correct_answer"] = sanitize_ai_text(correct_answer)
        elif isinstance(correct_answer, list):
            question["correct_answer"] = [
                sanitize_ai_text(answer) if isinstance(answer, str) else answer
                for answer in correct_answer
            ]

    return sanitized_payload


def sanitize_ai_text(value: str) -> str:
    normalized = str(value).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = _strip_markdown_emphasis(normalized)
    normalized = _strip_artificial_underline_markers(normalized)
    normalized = _normalize_phonetic_proper_nouns(normalized)
    return normalized.strip()


def validate_ai_question_payload(
    question: Any,
    index: int = 1,
    allowed_question_types: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    allowed_types = allowed_question_types or ALLOWED_QUESTION_TYPES

    if not isinstance(question, dict):
        return [f"Question {index}: must be an object"]

    question_type = _normalize_text(question.get("type"))
    if question_type not in ALLOWED_QUESTION_TYPES:
        errors.append(f"Question {index}: invalid type")
    elif question_type not in allowed_types:
        errors.append(f"Question {index}: type is not allowed by request")

    content = _normalize_text(question.get("content"))
    if not content:
        errors.append(f"Question {index}: content is required")

    explanation = _normalize_text(question.get("explanation"))
    if not explanation:
        errors.append(f"Question {index}: explanation is required")

    difficulty = _normalize_text(question.get("difficulty"))
    if difficulty not in ALLOWED_DIFFICULTIES:
        errors.append(f"Question {index}: difficulty must be easy, medium, or hard")

    topic = _normalize_text(question.get("topic"))
    if not topic:
        errors.append(f"Question {index}: topic is required")

    points = _to_float(question.get("points"))
    if points is None or points <= 0:
        errors.append(f"Question {index}: points must be greater than 0")

    if question_type == "multiple_choice":
        errors.extend(_validate_multiple_choice(question, index))
    elif question_type == "true_false":
        errors.extend(_validate_true_false(question, index))
    elif question_type == "short_answer":
        errors.extend(_validate_short_answer(question, index))
    elif question_type == "essay":
        errors.extend(_validate_essay(question, index))

    return errors


def build_question_payload_from_draft(draft) -> dict[str, Any]:
    return {
        "type": draft.question_type,
        "content": sanitize_ai_text(draft.content or ""),
        "options": [
            sanitize_ai_text(option) if isinstance(option, str) else option
            for option in draft.options or []
        ],
        "correct_answer": _sanitize_answer_value(draft.correct_answer),
        "explanation": sanitize_ai_text(draft.explanation or ""),
        "difficulty": draft.difficulty,
        "points": float(draft.points or 0),
        "topic": sanitize_ai_text(draft.topic or ""),
    }


def _sanitize_answer_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_ai_text(value)
    if isinstance(value, list):
        return [
            sanitize_ai_text(answer) if isinstance(answer, str) else answer
            for answer in value
        ]
    return value


def _validate_multiple_choice(question: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    options = question.get("options")
    if not isinstance(options, list):
        return [f"Question {index}: multiple_choice options must be a list"]

    normalized_options = [_normalize_text(option) for option in options]
    if len(normalized_options) != 4:
        errors.append(f"Question {index}: multiple_choice must have exactly 4 options")
    if any(not option for option in normalized_options):
        errors.append(f"Question {index}: options cannot be empty")
    if len(set(normalized_options)) != len(normalized_options):
        errors.append(f"Question {index}: options must be unique")
    if any(_contains_artificial_underline_marker(option) for option in normalized_options):
        errors.append(f"Question {index}: options must not contain underscore underline markers")

    correct_answer = _normalize_text(question.get("correct_answer"))
    if not correct_answer:
        errors.append(f"Question {index}: correct_answer is required")
    elif _contains_artificial_underline_marker(correct_answer):
        errors.append(f"Question {index}: correct_answer must not contain underscore underline markers")
    elif correct_answer not in normalized_options:
        errors.append(f"Question {index}: correct_answer is not in options")

    return errors


def _validate_true_false(question: dict[str, Any], index: int) -> list[str]:
    correct_answer = question.get("correct_answer")
    if isinstance(correct_answer, bool):
        return []

    if isinstance(correct_answer, str) and correct_answer.strip().lower() in {"true", "false"}:
        return []

    return [f"Question {index}: true_false correct_answer must be true or false"]


def _validate_short_answer(question: dict[str, Any], index: int) -> list[str]:
    correct_answer = question.get("correct_answer")
    if isinstance(correct_answer, str) and correct_answer.strip():
        return []

    if isinstance(correct_answer, list) and any(_normalize_text(answer) for answer in correct_answer):
        return []

    return [f"Question {index}: short_answer correct_answer is required"]


def _validate_essay(question: dict[str, Any], index: int) -> list[str]:
    if _normalize_text(question.get("explanation")):
        return []
    return [f"Question {index}: essay explanation or rubric is required"]


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _strip_markdown_emphasis(value: str) -> str:
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"__([^_]+)__", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    return value


def _strip_artificial_underline_markers(value: str) -> str:
    value = re.sub(r"(?<!\w)_([A-Za-z]+)_(?!\w)", r"\1", value)

    def remove_internal_underscores(match: re.Match[str]) -> str:
        return match.group(0).replace("_", "")

    return re.sub(r"\b[A-Za-z]+(?:_[A-Za-z]+){2,}\b", remove_internal_underscores, value)


def _normalize_phonetic_proper_nouns(value: str) -> str:
    normalized = value
    for pattern, replacement in PHONETIC_PROPER_NOUN_REPLACEMENTS:
        normalized = pattern.sub(replacement, normalized)
    return normalized


def _contains_artificial_underline_marker(value: str) -> bool:
    if re.search(r"(?<!\w)_[A-Za-z]+_(?!\w)", value):
        return True
    return bool(re.search(r"\b[A-Za-z]+(?:_[A-Za-z]+){2,}\b", value))
