import os
from dotenv import load_dotenv

load_dotenv()


def _normalize_origin(origin: str) -> str:
    return origin.strip().rstrip("/")


def _split_origins(raw_origins: str) -> list[str]:
    return [
        normalized
        for normalized in (_normalize_origin(origin) for origin in raw_origins.split(","))
        if normalized
    ]


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Quiz Online API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")
    FRONTEND_URL: str = _normalize_origin(os.getenv("FRONTEND_URL", "http://localhost:3000"))
    FRONTEND_AUTH_CALLBACK_PATH: str = os.getenv("FRONTEND_AUTH_CALLBACK_PATH", "/auth/callback").strip() or "/auth/callback"
    ALLOWED_ORIGINS: list[str] = _split_origins(os.getenv("ALLOWED_ORIGINS", FRONTEND_URL))
    ALLOWED_ORIGIN_REGEX: str | None = os.getenv("ALLOWED_ORIGIN_REGEX", "").strip() or None
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "change_me")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "session_token")
    OAUTH_SESSION_COOKIE_NAME: str = os.getenv("OAUTH_SESSION_COOKIE_NAME", "oauth_session")
    REFRESH_COOKIE_NAME: str = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
    SESSION_EXPIRE_MINUTES: int = int(os.getenv("SESSION_EXPIRE_MINUTES", "30"))
    SESSION_REFRESH_DAYS: int = int(os.getenv("SESSION_REFRESH_DAYS", "7"))
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "False").lower() == "true"
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax").lower()

settings = Settings()
