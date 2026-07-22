import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ai_agent.config import settings
from ai_agent.models import AgentDatasetSnapshot, AgentKnowledgeItem


ALLOWED_QUESTION_TYPES = {"multiple_choice", "true_false", "short_answer", "essay"}
PROMPT_INJECTION_PATTERNS = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "developer message",
    "reveal your instructions",
    "bỏ qua hướng dẫn",
    "bỏ qua chỉ dẫn",
    "tiết lộ prompt",
)
PII_PATTERNS = (
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+?84|0)(?:[ .-]?\d){9,10}(?!\d)"), "[PHONE]"),
    (re.compile(r"(?<!\d)\d{9}(?:\d{3})?(?!\d)"), "[IDENTIFIER]"),
)


@dataclass(frozen=True)
class CuratedExample:
    content_hash: str
    quality_score: float
    split: str
    payload: dict[str, Any]


def export_dataset_snapshot(db: Session, snapshot: AgentDatasetSnapshot) -> dict[str, Any]:
    items = (
        db.query(AgentKnowledgeItem)
        .filter(AgentKnowledgeItem.status == "approved")
        .order_by(AgentKnowledgeItem.content_hash, AgentKnowledgeItem.id)
        .all()
    )
    accepted: list[CuratedExample] = []
    rejected_reasons: dict[str, int] = {}

    for item in items:
        allowed, reason = _training_scope_allowed(item, snapshot.include_private_opt_in)
        if not allowed:
            _increment(rejected_reasons, reason)
            continue
        example, reason = curate_knowledge_item(item, snapshot.min_quality_score)
        if example is None:
            _increment(rejected_reasons, reason)
            continue
        accepted.append(example)

    split_rows = {"train": [], "validation": [], "test": []}
    for example in accepted:
        split_rows[example.split].append(example.payload)

    output_dir = Path(settings.ML_DATASET_ROOT) / snapshot.id
    output_dir.mkdir(parents=True, exist_ok=True)
    checksums: dict[str, str] = {}
    for split_name, rows in split_rows.items():
        checksums[f"{split_name}.jsonl"] = _write_jsonl_atomic(
            output_dir / f"{split_name}.jsonl",
            rows,
        )

    manifest = {
        "schema_version": "1.0",
        "snapshot_id": snapshot.id,
        "name": snapshot.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "privacy": {
            "system_data_included": True,
            "private_data_requires_explicit_opt_in": True,
            "private_opt_in_requested": bool(snapshot.include_private_opt_in),
            "private_opt_in_enabled": bool(settings.ML_PRIVATE_OPT_IN_ENABLED),
            "owner_identifiers_exported": False,
        },
        "quality": {
            "minimum_score": snapshot.min_quality_score,
            "rejected_reasons": rejected_reasons,
        },
        "counts": {
            "source": len(items),
            "accepted": len(accepted),
            "rejected": len(items) - len(accepted),
            "train": len(split_rows["train"]),
            "validation": len(split_rows["validation"]),
            "test": len(split_rows["test"]),
        },
        "checksums": checksums,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_checksum = _write_json_atomic(manifest_path, manifest)
    return {
        "output_dir": str(output_dir),
        "manifest": manifest,
        "checksum_sha256": manifest_checksum,
        **manifest["counts"],
    }


def curate_knowledge_item(
    item: AgentKnowledgeItem,
    minimum_score: float,
) -> tuple[CuratedExample | None, str]:
    question_type = str(item.question_type or "").strip()
    content = redact_personal_data(str(item.content or "").strip())
    explanation = redact_personal_data(str(item.explanation or "").strip())
    options = [redact_personal_data(str(option).strip()) for option in (item.options or [])]
    correct_answer = _redact_value(item.correct_answer)

    if question_type not in ALLOWED_QUESTION_TYPES:
        return None, "invalid_question_type"
    if len(content) < 12:
        return None, "content_too_short"
    lowered = f"{content}\n{explanation}".casefold()
    if any(pattern in lowered for pattern in PROMPT_INJECTION_PATTERNS):
        return None, "prompt_injection"
    if not _answer_shape_is_valid(question_type, options, correct_answer):
        return None, "invalid_answer_shape"

    quality_score = score_quality(question_type, content, options, correct_answer, explanation)
    if quality_score < minimum_score:
        return None, "below_quality_threshold"

    subject = redact_personal_data(str(item.subject or "").strip())
    grade = redact_personal_data(str(item.grade or "").strip())
    difficulty = str(item.difficulty or "").strip()
    topic = redact_personal_data(str(item.topic or "").strip())
    answer = {
        "type": question_type,
        "content": content,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "difficulty": difficulty,
        "topic": topic,
    }
    user_request = {
        "subject": subject,
        "grade": grade,
        "difficulty": difficulty,
        "topic": topic,
        "question_type": question_type,
        "instruction": "Tạo một câu hỏi mới, chính xác và đúng định dạng JSON.",
    }
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "Bạn là trợ lý tạo câu hỏi giáo dục QuizzVN. Chỉ trả về JSON hợp lệ.",
            },
            {
                "role": "user",
                "content": json.dumps(user_request, ensure_ascii=False, separators=(",", ":")),
            },
            {
                "role": "assistant",
                "content": json.dumps(answer, ensure_ascii=False, separators=(",", ":")),
            },
        ],
        "metadata": {
            "content_hash": item.content_hash,
            "question_type": question_type,
            "subject": subject,
            "grade": grade,
            "difficulty": difficulty,
            "topic": topic,
            "quality_score": quality_score,
        },
    }
    return CuratedExample(
        content_hash=item.content_hash,
        quality_score=quality_score,
        split=deterministic_split(item.content_hash),
        payload=payload,
    ), "accepted"


def score_quality(
    question_type: str,
    content: str,
    options: list[str],
    correct_answer: Any,
    explanation: str,
) -> float:
    score = 0.45
    score += 0.15 if len(content) >= 30 else 0.05
    score += 0.15 if len(explanation) >= 20 else 0.0
    score += 0.10 if correct_answer not in (None, "", []) else 0.0
    if question_type == "multiple_choice":
        score += 0.15 if len(options) == 4 and len(set(options)) == 4 else 0.0
    else:
        score += 0.15 if not options else 0.0
    return round(min(score, 1.0), 4)


def deterministic_split(content_hash: str) -> str:
    normalized_hash = str(content_hash or "").strip().lower()
    try:
        bucket = int(normalized_hash[:8], 16) % 100
    except (TypeError, ValueError):
        normalized_hash = hashlib.sha256(normalized_hash.encode("utf-8")).hexdigest()
        bucket = int(normalized_hash[:8], 16) % 100
    if bucket < settings.ML_TEST_PERCENT:
        return "test"
    if bucket < settings.ML_TEST_PERCENT + settings.ML_VALIDATION_PERCENT:
        return "validation"
    return "train"


def redact_personal_data(value: str) -> str:
    result = value
    for pattern, replacement in PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _training_scope_allowed(
    item: AgentKnowledgeItem,
    include_private_opt_in: bool,
) -> tuple[bool, str]:
    if item.visibility == "system":
        return True, "system"
    metadata = item.source_metadata if isinstance(item.source_metadata, dict) else {}
    consent = metadata.get("training_consent") is True
    if (
        item.visibility == "private"
        and include_private_opt_in
        and settings.ML_PRIVATE_OPT_IN_ENABLED
        and consent
    ):
        return True, "private_opt_in"
    return False, "private_without_consent"


def _answer_shape_is_valid(question_type: str, options: list[str], answer: Any) -> bool:
    if question_type == "multiple_choice":
        return len(options) == 4 and len(set(options)) == 4 and answer in options
    if options:
        return False
    if question_type == "true_false":
        return isinstance(answer, bool)
    if question_type == "short_answer":
        return bool(answer) and isinstance(answer, (str, list))
    return bool(answer)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_personal_data(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    return value


def _write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> str:
    content = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )
    return _write_text_atomic(path, content)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> str:
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return _write_text_atomic(path, content)


def _write_text_atomic(path: Path, content: str) -> str:
    temporary = path.with_suffix(path.suffix + ".tmp")
    encoded = content.encode("utf-8")
    temporary.write_bytes(encoded)
    temporary.replace(path)
    return hashlib.sha256(encoded).hexdigest()


def _increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1
