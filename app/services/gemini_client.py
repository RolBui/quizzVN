import time
from typing import Any

import httpx

from app.core.config import settings
from app.services.ai_provider_client import AIProviderClient, AIProviderError, AIProviderResult, parse_json_from_text


GEMINI_GENERATE_CONTENT_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiAIProviderClient(AIProviderClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
    ) -> None:
        self.api_key = (api_key or settings.GEMINI_API_KEY).strip()
        self.model = (model or settings.AI_MODEL).strip()
        self.timeout_seconds = float(timeout_seconds or settings.AI_PROVIDER_TIMEOUT_SECONDS)
        self.retry_count = max(0, int(settings.AI_PROVIDER_RETRY_COUNT if retry_count is None else retry_count))

    def generate_exam(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
    ) -> AIProviderResult:
        if not self.api_key:
            raise AIProviderError("GEMINI_API_KEY is not configured")

        text, raw_response = self._generate_content_text(prompt, schema)
        try:
            payload = parse_json_from_text(text)
        except AIProviderError:
            repair_prompt = _build_json_repair_prompt(prompt, text)
            retry_text, retry_raw_response = self._generate_content_text(repair_prompt, schema)
            try:
                payload = parse_json_from_text(retry_text)
            except AIProviderError as exc:
                raise AIProviderError(
                    f"AI response is not valid JSON. Raw preview: {_preview_text(retry_text)}"
                ) from exc

            raw_response = {
                "first_response": raw_response,
                "repair_response": retry_raw_response,
            }

        return AIProviderResult(
            payload=payload,
            raw_response=raw_response,
        )

    def _generate_content_text(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        url = GEMINI_GENERATE_CONTENT_URL.format(model=self.model)
        generation_config_attempts = [
            _build_legacy_json_generation_config(schema),
            {"temperature": 0.35},
        ]

        last_error: AIProviderError | None = None
        for generation_config in generation_config_attempts:
            request_payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": prompt,
                            }
                        ],
                    }
                ],
                "generationConfig": generation_config,
            }

            response: httpx.Response | None = None
            for attempt in range(self.retry_count + 1):
                try:
                    with httpx.Client(timeout=self.timeout_seconds) as client:
                        response = client.post(
                            url,
                            headers={
                                "x-goog-api-key": self.api_key,
                            },
                            json=request_payload,
                        )
                        response.raise_for_status()
                    break
                except httpx.HTTPStatusError as exc:
                    detail = _extract_gemini_error(exc.response)
                    last_error = AIProviderError(detail)
                    if _is_unsupported_generation_config_error(detail):
                        continue
                    raise last_error from exc
                except httpx.TimeoutException as exc:
                    if attempt < self.retry_count:
                        time.sleep(min(2, attempt + 1))
                        continue
                    raise AIProviderError(
                        f"AI provider request timed out after {self.timeout_seconds:g}s. Try fewer questions or retry later."
                    ) from exc
                except httpx.HTTPError as exc:
                    raise AIProviderError(f"AI provider request failed: {exc}") from exc

            if response is None:
                raise AIProviderError("AI provider request failed")

            raw_response = response.json()
            return _extract_text(raw_response), raw_response

        if last_error:
            raise last_error
        raise AIProviderError("AI provider request failed")


def _extract_text(raw_response: dict[str, Any]) -> str:
    candidates = raw_response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise AIProviderError("AI provider returned no candidates")

    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise AIProviderError("AI provider returned an invalid candidate")

    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise AIProviderError("AI provider returned no content parts")

    text_parts = [
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ]
    text = "\n".join(part for part in text_parts if part).strip()
    if not text:
        raise AIProviderError("AI provider returned empty text")

    return text


def _extract_gemini_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"AI provider returned HTTP {response.status_code}"

    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])

    return f"AI provider returned HTTP {response.status_code}"


def _build_legacy_json_generation_config(schema: dict[str, Any] | None) -> dict[str, Any]:
    config: dict[str, Any] = {
        "temperature": 0.35,
        "responseMimeType": "application/json",
    }
    if schema:
        config["responseSchema"] = schema
    return config


def _is_unsupported_generation_config_error(detail: str) -> bool:
    normalized = detail.lower()
    return (
        "invalid value" in normalized
        and (
            "response_format" in normalized
            or "responseformat" in normalized
            or "response_mime_type" in normalized
            or "responsemimetype" in normalized
        )
    )


def _build_json_repair_prompt(original_prompt: str, previous_text: str) -> str:
    return f"""{original_prompt}

Your previous response was not valid JSON.

Previous response:
{_preview_text(previous_text, limit=4000)}

Return one valid JSON object only. Do not include markdown, commentary, or code fences.
"""


def _preview_text(text: str, limit: int = 500) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."
