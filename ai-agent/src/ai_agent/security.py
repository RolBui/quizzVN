import hashlib
import hmac
import time


def build_callback_signature(secret: str, timestamp: str, body: bytes) -> str:
    message = timestamp.encode("utf-8") + b"." + body
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def callback_headers(secret: str, body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    return {
        "Content-Type": "application/json",
        "X-AI-Agent-Timestamp": timestamp,
        "X-AI-Agent-Signature": build_callback_signature(secret, timestamp, body),
    }
