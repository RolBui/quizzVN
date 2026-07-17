from typing import Any

import httpx

from app.core.config import settings


class AIAgentDispatchError(RuntimeError):
    pass


def is_ai_agent_enabled() -> bool:
    return settings.AI_EXECUTION_MODE == "agent"


def dispatch_ai_agent_job(payload: dict[str, Any]) -> str:
    if not settings.AI_AGENT_URL:
        raise AIAgentDispatchError("AI_AGENT_URL is not configured")
    if not settings.AI_AGENT_SHARED_SECRET:
        raise AIAgentDispatchError("AI_AGENT_SHARED_SECRET is not configured")

    request_payload = dict(payload)
    request_payload["callback_url"] = (
        f"{settings.AI_AGENT_CALLBACK_BASE_URL}/api/internal/ai-agent/callbacks/"
        f"{request_payload['external_job_id']}"
    )
    try:
        with httpx.Client(timeout=settings.AI_AGENT_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{settings.AI_AGENT_URL}/v1/jobs",
                headers={
                    "Authorization": f"Bearer {settings.AI_AGENT_SHARED_SECRET}",
                    "Idempotency-Key": request_payload["dispatch_id"],
                },
                json=request_payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AIAgentDispatchError(
            f"AI Agent rejected the job with HTTP {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        raise AIAgentDispatchError(f"Unable to reach AI Agent: {exc}") from exc

    try:
        data = response.json()
        return str(data["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AIAgentDispatchError("AI Agent returned an invalid response") from exc
