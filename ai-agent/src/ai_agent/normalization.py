import copy
import re
from typing import Any


TRUE_ANSWER_VALUES = {"true", "1", "\u0111\u00fang", "dung", "yes"}
FALSE_ANSWER_VALUES = {"false", "0", "sai", "no"}


def normalize_exam_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized_payload = copy.deepcopy(payload)
    questions = normalized_payload.get("questions")
    if not isinstance(questions, list):
        return normalized_payload

    for question in questions:
        if not isinstance(question, dict):
            continue
        if str(question.get("type") or "").strip().lower() != "true_false":
            continue
        question["correct_answer"] = normalize_true_false_answer(
            question.get("correct_answer")
        )

    return normalized_payload


def normalize_true_false_answer(value: Any) -> Any:
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)

    if isinstance(value, str):
        normalized = re.sub(r"\s+", " ", value).strip().casefold()
        normalized = re.sub(r"[.!?]+$", "", normalized).strip()
        if normalized in TRUE_ANSWER_VALUES:
            return True
        if normalized in FALSE_ANSWER_VALUES:
            return False

    return value
