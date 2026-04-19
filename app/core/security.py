import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def generate_session_token() -> str:
    return secrets.token_urlsafe(48)

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)

def get_expiry(minutes: int | None = None):
    ttl_minutes = minutes or settings.SESSION_EXPIRE_MINUTES
    return utc_now() + timedelta(minutes=ttl_minutes)

def get_refresh_expiry(days: int | None = None):
    ttl_days = days or settings.SESSION_REFRESH_DAYS
    return utc_now() + timedelta(days=ttl_days)


def hash_password(password: str) -> str:
    import base64
    import hashlib

    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        390000,
    )
    return f"{base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(derived_key).decode()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    import base64
    import hashlib
    import hmac

    if not password_hash or "$" not in password_hash:
        return False

    encoded_salt, encoded_hash = password_hash.split("$", 1)
    salt = base64.urlsafe_b64decode(encoded_salt.encode())
    expected_hash = base64.urlsafe_b64decode(encoded_hash.encode())
    candidate_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        390000,
    )
    return hmac.compare_digest(candidate_hash, expected_hash)
