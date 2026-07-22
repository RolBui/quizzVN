import json
import random
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from ai_agent.config import settings
from ai_agent.normalization import normalize_exam_payload


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ProviderResult:
    payload: dict[str, Any]
    raw_response: dict[str, Any]
    attempts: int


AttemptRecorder = Callable[[int, str, int | None, int, str], None]


class GeminiProvider:
    def __init__(
        self,
        sleep: Callable[[float], None] = time.sleep,
        model: str | None = None,
    ) -> None:
        self.sleep = sleep
        self.model = model or settings.AI_MODEL

    def generate(
        self,
        prompt: str,
        record_attempt: AttemptRecorder,
        attempt_offset: int = 0,
    ) -> ProviderResult:
        text, raw_response, attempts = self._request_text(
            prompt,
            record_attempt,
            attempt_offset=attempt_offset,
        )
        try:
            return ProviderResult(
                normalize_exam_payload(_parse_json(text)),
                raw_response,
                attempts,
            )
        except ProviderError:
            repair_prompt = _repair_prompt(prompt, text)
            repaired_text, repaired_raw, repair_attempts = self._request_text(
                repair_prompt,
                record_attempt,
                attempt_offset=attempt_offset + attempts,
            )
            return ProviderResult(
                normalize_exam_payload(_parse_json(repaired_text)),
                {"first_response": raw_response, "repair_response": repaired_raw},
                attempts + repair_attempts,
            )

    def _request_text(
        self,
        prompt: str,
        record_attempt: AttemptRecorder,
        attempt_offset: int = 0,
    ) -> tuple[str, dict[str, Any], int]:
        if not settings.GEMINI_API_KEY:
            raise ProviderError("GEMINI_API_KEY is not configured")

        url = GEMINI_URL.format(model=self.model)
        request_payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.45,
                "responseMimeType": "application/json",
            },
        }
        max_attempts = max(1, settings.PROVIDER_RETRY_COUNT + 1)
        last_error: ProviderError | None = None

        for index in range(max_attempts):
            attempt_number = attempt_offset + index + 1
            started = time.monotonic()
            try:
                with httpx.Client(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                    response = client.post(
                        url,
                        headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                        json=request_payload,
                    )
                latency_ms = int((time.monotonic() - started) * 1000)
                if response.status_code >= 400:
                    detail = _provider_error(response)
                    record_attempt(attempt_number, "failed", response.status_code, latency_ms, detail)
                    last_error = ProviderError(detail, response.status_code)
                    if response.status_code in RETRYABLE_STATUS_CODES and index + 1 < max_attempts:
                        self.sleep(_retry_delay(index, response.headers.get("Retry-After")))
                        continue
                    raise last_error

                raw_response = response.json()
                text = _extract_text(raw_response)
                record_attempt(attempt_number, "succeeded", response.status_code, latency_ms, "")
                return text, raw_response, index + 1
            except httpx.TimeoutException as exc:
                latency_ms = int((time.monotonic() - started) * 1000)
                detail = f"Gemini timed out after {settings.PROVIDER_TIMEOUT_SECONDS:g} seconds"
                record_attempt(attempt_number, "failed", None, latency_ms, detail)
                last_error = ProviderError(detail)
                if index + 1 < max_attempts:
                    self.sleep(_retry_delay(index, None))
                    continue
                raise last_error from exc
            except httpx.HTTPError as exc:
                latency_ms = int((time.monotonic() - started) * 1000)
                detail = f"Gemini request failed: {exc}"
                record_attempt(attempt_number, "failed", None, latency_ms, detail)
                last_error = ProviderError(detail)
                if index + 1 < max_attempts:
                    self.sleep(_retry_delay(index, None))
                    continue
                raise last_error from exc
            except (ValueError, KeyError) as exc:
                latency_ms = int((time.monotonic() - started) * 1000)
                detail = "Gemini returned an invalid response"
                record_attempt(attempt_number, "failed", None, latency_ms, detail)
                raise ProviderError(detail) from exc

        raise last_error or ProviderError("Gemini request failed")


class LocalOpenAIProvider:
    def __init__(
        self,
        model: str,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model
        self.sleep = sleep

    def generate(
        self,
        prompt: str,
        record_attempt: AttemptRecorder,
        attempt_offset: int = 0,
    ) -> ProviderResult:
        text, raw_response, attempts = self._request_text(
            prompt,
            record_attempt,
            attempt_offset,
        )
        try:
            return ProviderResult(
                normalize_exam_payload(_parse_json(text)),
                raw_response,
                attempts,
            )
        except ProviderError:
            repair_prompt = _repair_prompt(prompt, text)
            repaired_text, repaired_raw, repair_attempts = self._request_text(
                repair_prompt,
                record_attempt,
                attempt_offset + attempts,
            )
            return ProviderResult(
                normalize_exam_payload(_parse_json(repaired_text)),
                {"first_response": raw_response, "repair_response": repaired_raw},
                attempts + repair_attempts,
            )

    def _request_text(
        self,
        prompt: str,
        record_attempt: AttemptRecorder,
        attempt_offset: int,
    ) -> tuple[str, dict[str, Any], int]:
        if not settings.LOCAL_INFERENCE_URL:
            raise ProviderError("AI_AGENT_LOCAL_INFERENCE_URL is not configured")

        headers = {"Content-Type": "application/json"}
        if settings.LOCAL_INFERENCE_SECRET:
            headers["Authorization"] = f"Bearer {settings.LOCAL_INFERENCE_SECRET}"
        request_payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.45,
            "response_format": {"type": "json_object"},
        }
        max_attempts = max(1, settings.PROVIDER_RETRY_COUNT + 1)
        last_error: ProviderError | None = None
        for index in range(max_attempts):
            attempt_number = attempt_offset + index + 1
            started = time.monotonic()
            try:
                with httpx.Client(timeout=settings.LOCAL_INFERENCE_TIMEOUT_SECONDS) as client:
                    response = client.post(
                        settings.LOCAL_INFERENCE_URL,
                        headers=headers,
                        json=request_payload,
                    )
                latency_ms = int((time.monotonic() - started) * 1000)
                if response.status_code >= 400:
                    detail = _local_provider_error(response)
                    record_attempt(attempt_number, "failed", response.status_code, latency_ms, detail)
                    last_error = ProviderError(detail, response.status_code)
                    if response.status_code in RETRYABLE_STATUS_CODES and index + 1 < max_attempts:
                        self.sleep(_retry_delay(index, response.headers.get("Retry-After")))
                        continue
                    raise last_error
                raw_response = response.json()
                text = _extract_local_text(raw_response)
                record_attempt(attempt_number, "succeeded", response.status_code, latency_ms, "")
                return text, raw_response, index + 1
            except httpx.TimeoutException as exc:
                latency_ms = int((time.monotonic() - started) * 1000)
                detail = (
                    "Local model timed out after "
                    f"{settings.LOCAL_INFERENCE_TIMEOUT_SECONDS:g} seconds"
                )
                record_attempt(attempt_number, "failed", None, latency_ms, detail)
                last_error = ProviderError(detail)
                if index + 1 < max_attempts:
                    self.sleep(_retry_delay(index, None))
                    continue
                raise last_error from exc
            except httpx.HTTPError as exc:
                latency_ms = int((time.monotonic() - started) * 1000)
                detail = f"Local model request failed: {exc}"
                record_attempt(attempt_number, "failed", None, latency_ms, detail)
                last_error = ProviderError(detail)
                if index + 1 < max_attempts:
                    self.sleep(_retry_delay(index, None))
                    continue
                raise last_error from exc
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                latency_ms = int((time.monotonic() - started) * 1000)
                detail = "Local model returned an invalid response"
                record_attempt(attempt_number, "failed", None, latency_ms, detail)
                raise ProviderError(detail) from exc
        raise last_error or ProviderError("Local model request failed")


def get_provider(provider_name: str | None = None, model: str | None = None):
    selected = (provider_name or settings.AI_PROVIDER).strip().lower()
    if selected == "gemini":
        return GeminiProvider(model=model)
    if selected == "local_openai":
        if not model:
            raise ProviderError("Local model name is required")
        return LocalOpenAIProvider(model=model)
    raise ProviderError(f"Unsupported AI provider: {selected}")


def _retry_delay(index: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return max(0.0, min(float(retry_after), 60.0))
        except ValueError:
            pass
    base = max(0.1, settings.RETRY_BASE_SECONDS)
    return min(60.0, base * (2**index) + random.uniform(0, base))


def _provider_error(response: httpx.Response) -> str:
    try:
        error = response.json().get("error") or {}
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
    except ValueError:
        pass
    return f"Gemini returned HTTP {response.status_code}"


def _local_provider_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if isinstance(error, str) and error:
            return error
        if isinstance(payload, dict) and payload.get("detail"):
            return str(payload["detail"])
    except ValueError:
        pass
    return f"Local model returned HTTP {response.status_code}"


def _extract_text(raw_response: dict[str, Any]) -> str:
    candidates = raw_response.get("candidates") or []
    parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
    text = "\n".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ).strip()
    if not text:
        raise ProviderError("Gemini returned no content")
    return text


def _extract_local_text(raw_response: dict[str, Any]) -> str:
    choices = raw_response.get("choices") or []
    if not choices:
        raise ProviderError("Local model returned no choices")
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        text = "\n".join(
            str(part.get("text") or "")
            for part in content
            if isinstance(part, dict)
        ).strip()
        if text:
            return text
    raise ProviderError("Local model returned no content")


def _parse_json(text: str) -> dict[str, Any]:
    normalized = text.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()
    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError as exc:
        start, end = normalized.find("{"), normalized.rfind("}")
        if start < 0 or end <= start:
            raise ProviderError("Gemini response is not valid JSON") from exc
        try:
            payload = json.loads(normalized[start : end + 1])
        except json.JSONDecodeError as nested_exc:
            raise ProviderError("Gemini response is not valid JSON") from nested_exc
    if not isinstance(payload, dict):
        raise ProviderError("Gemini JSON root must be an object")
    return payload


def _repair_prompt(original_prompt: str, previous_text: str) -> str:
    return f"""{original_prompt}

Your previous response was not valid JSON.
Return one valid JSON object only, without markdown or commentary.

Previous response:
{previous_text[:4000]}
"""


def build_semantic_repair_prompt(
    original_prompt: str,
    previous_payload: dict[str, Any],
    errors: list[str],
) -> str:
    previous_json = json.dumps(previous_payload, ensure_ascii=False, indent=2)
    error_text = "\n".join(f"- {error}" for error in errors)
    return f"""{original_prompt}

The previous JSON was syntactically valid but failed semantic validation.

Validation errors:
{error_text}

Previous JSON:
{previous_json}

Fix every validation error and return one complete valid JSON object only.
Do not include markdown or commentary.
For true_false questions, correct_answer must be the unquoted JSON boolean true or false.
"""
