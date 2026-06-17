import json
from dataclasses import dataclass
from typing import Any


class AIProviderError(RuntimeError):
    pass


@dataclass
class AIProviderResult:
    payload: dict[str, Any]
    raw_response: dict[str, Any] | str


class AIProviderClient:
    def generate_exam(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
    ) -> AIProviderResult:
        raise NotImplementedError


def parse_json_from_text(text: str) -> dict[str, Any]:
    normalized = text.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        start = normalized.find("{")
        end = normalized.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AIProviderError("AI response is not valid JSON") from None
        try:
            parsed = json.loads(normalized[start : end + 1])
        except json.JSONDecodeError as exc:
            raise AIProviderError("AI response is not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise AIProviderError("AI response JSON root must be an object")

    return parsed
