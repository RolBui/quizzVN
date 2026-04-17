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
