import os
from dotenv import load_dotenv

load_dotenv()

LOCAL_DEV_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def _normalize_origin(origin: str) -> str:
    return origin.strip().rstrip("/")


def _split_origins(raw_origins: str) -> list[str]:
    return [
        normalized
        for normalized in (_normalize_origin(origin) for origin in raw_origins.split(","))
        if normalized
    ]


def _parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return raw_value.strip().lower() == "true"


def _build_allowed_origins(
    frontend_url: str,
    raw_origins: str,
    include_local_dev_origins: bool,
) -> list[str]:
    origins = _split_origins(raw_origins) if raw_origins.strip() else [frontend_url]

    if include_local_dev_origins:
        for origin in LOCAL_DEV_FRONTEND_ORIGINS:
            normalized = _normalize_origin(origin)
            if normalized not in origins:
                origins.append(normalized)

    return origins


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Quiz Online API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "")
    GOOGLE_OAUTH_PROMPT: str = os.getenv("GOOGLE_OAUTH_PROMPT", "select_account").strip() or "select_account"
    FRONTEND_URL: str = _normalize_origin(os.getenv("FRONTEND_URL", "http://localhost:3000"))
    FRONTEND_AUTH_CALLBACK_PATH: str = os.getenv("FRONTEND_AUTH_CALLBACK_PATH", "/auth/callback").strip() or "/auth/callback"
    INCLUDE_LOCAL_DEV_CORS_ORIGINS: bool = _parse_bool(
        os.getenv("INCLUDE_LOCAL_DEV_CORS_ORIGINS"),
        True,
    )
    ALLOWED_ORIGINS: list[str] = _build_allowed_origins(
        FRONTEND_URL,
        os.getenv("ALLOWED_ORIGINS", ""),
        INCLUDE_LOCAL_DEV_CORS_ORIGINS,
    )
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
