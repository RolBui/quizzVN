import hashlib
import hmac
import time


def build_ai_agent_signature(secret: str, timestamp: str, body: bytes) -> str:
    message = timestamp.encode("utf-8") + b"." + body
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_ai_agent_signature(
    secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
    tolerance_seconds: int,
) -> bool:
    if not secret or not timestamp or not signature:
        return False
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - sent_at) > max(1, tolerance_seconds):
        return False
    expected = build_ai_agent_signature(secret, timestamp, body)
    return hmac.compare_digest(expected, signature)
