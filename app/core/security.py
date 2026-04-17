import secrets
from datetime import datetime, timedelta

def generate_session_token() -> str:
    return secrets.token_urlsafe(48)

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)

def get_expiry(minutes: int = 30):
    return datetime.utcnow() + timedelta(minutes=minutes)

def get_refresh_expiry(days: int = 7):
    return datetime.utcnow() + timedelta(days=days)