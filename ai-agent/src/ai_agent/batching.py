import json
from typing import Any


def build_batch_specs(request_data: dict[str, Any], batch_size: int) -> list[dict[str, Any]]:
    distribution = dict(request_data.get("question_type_distribution") or {})
    question_types = list(request_data.get("question_types") or [])
    if not distribution and question_types:
        distribution[question_types[0]] = int(request_data.get("question_count") or 0)
    type_batches = _build_type_batches(
        distribution,
        question_types,
        max(1, batch_size),
    )
    difficulty_batches = _build_difficulty_batches(request_data, type_batches)
    return [
        _build_batch_request(request_data, type_distribution, difficulty_batches[index])
        for index, type_distribution in enumerate(type_batches)
    ]


def build_batch_prompt(
    original_prompt: str,
    batch_data: dict[str, Any],
    batch_index: int,
    batch_count: int,
    existing_questions: list[dict[str, Any]],
) -> str:
    existing = [
        {"type": question.get("type"), "content": question.get("content")}
        for question in existing_questions
        if isinstance(question, dict)
    ]
    return f"""{original_prompt}

IMPORTANT BATCH OVERRIDE (this section takes precedence over the full-exam counts above):
- Generate batch {batch_index} of {batch_count}.
- Return exactly {batch_data['question_count']} questions in this response.
- Question type counts: {json.dumps(batch_data['question_type_distribution'], ensure_ascii=False)}
- Difficulty distribution: {json.dumps(batch_data['difficulty_distribution'], ensure_ascii=False)}
- Return a complete exam JSON object, but its questions array must contain this batch only.
- Do not mention batch numbers in the questions.
- Do not repeat or closely paraphrase any question listed below.

Questions already generated for this job:
{json.dumps(existing, ensure_ascii=False, indent=2)}
"""


def aggregate_batch_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not payloads:
        return {}
    combined = dict(payloads[0])
    questions: list[dict[str, Any]] = []
    for payload in payloads:
        batch_questions = payload.get("questions")
        if isinstance(batch_questions, list):
            questions.extend(batch_questions)
    combined["questions"] = questions
    combined["total_points"] = sum(
        float(question.get("points") or 0)
        for question in questions
        if isinstance(question, dict)
    )
    return combined


def _build_type_batches(
    distribution: dict[str, int],
    question_types: list[str],
    batch_size: int,
) -> list[dict[str, int]]:
    remaining = {
        str(question_type): int(count or 0)
        for question_type, count in distribution.items()
        if int(count or 0) > 0
    }
    if not remaining:
        return []

    ordered = [question_type for question_type in question_types if question_type in remaining]
    ordered.extend(question_type for question_type in remaining if question_type not in ordered)
    batches: list[dict[str, int]] = []
    while sum(remaining.values()) > 0:
        slots = batch_size
        batch: dict[str, int] = {}
        for question_type in ordered:
            available = remaining.get(question_type, 0)
            if slots <= 0:
                break
            if available <= 0:
                continue
            take = min(available, slots)
            batch[question_type] = take
            remaining[question_type] = available - take
            slots -= take
        if not batch:
            break
        batches.append(batch)
    return batches


def _build_difficulty_batches(
    request_data: dict[str, Any],
    type_batches: list[dict[str, int]],
) -> list[dict[str, int]]:
    distribution = {
        str(difficulty): int(count or 0)
        for difficulty, count in (request_data.get("difficulty_distribution") or {}).items()
    }
    if sum(distribution.values()) != int(request_data.get("question_count") or 0):
        return [dict(distribution) for _ in type_batches]

    remaining = dict(distribution)
    result: list[dict[str, int]] = []
    for type_batch in type_batches:
        slots = sum(type_batch.values())
        batch: dict[str, int] = {}
        for difficulty in ("easy", "medium", "hard"):
            available = remaining.get(difficulty, 0)
            if slots <= 0:
                break
            if available <= 0:
                continue
            take = min(available, slots)
            batch[difficulty] = take
            remaining[difficulty] = available - take
            slots -= take
        result.append(batch)
    return result


def _build_batch_request(
    request_data: dict[str, Any],
    type_distribution: dict[str, int],
    difficulty_distribution: dict[str, int],
) -> dict[str, Any]:
    batch = dict(request_data)
    batch["question_count"] = sum(type_distribution.values())
    batch["question_types"] = list(type_distribution)
    batch["question_type_distribution"] = dict(type_distribution)
    batch["difficulty_distribution"] = dict(difficulty_distribution)
    return batch
