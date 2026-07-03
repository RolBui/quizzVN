import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

LOCAL_DEV_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
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


def _parse_session_expire_minutes() -> int:
    raw_days = os.getenv("SESSION_EXPIRE_DAYS")
    if raw_days is not None and raw_days.strip():
        return int(raw_days.strip()) * 24 * 60

    return int(os.getenv("SESSION_EXPIRE_MINUTES", "30"))


def _derive_origin_from_url(url: str) -> str | None:
    raw_url = url.strip()
    if not raw_url:
        return None

    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        return None

    return f"{parsed.scheme}://{parsed.netloc}"


def _build_allowed_origins(
    frontend_url: str,
    raw_origins: str,
    include_local_dev_origins: bool,
    extra_origins: tuple[str, ...] = (),
) -> list[str]:
    origins = [frontend_url]

    for origin in extra_origins:
        normalized = _normalize_origin(origin)
        if normalized and normalized not in origins:
            origins.append(normalized)

    for origin in _split_origins(raw_origins):
        if origin not in origins:
            origins.append(origin)

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
    BACKEND_URL: str = _normalize_origin(
        os.getenv(
            "BACKEND_URL",
            _derive_origin_from_url(os.getenv("GOOGLE_REDIRECT_URI", "")) or "http://localhost:8000",
        )
    )
    FRONTEND_URL: str = _normalize_origin(
        os.getenv(
            "FRONTEND_URL",
            (
                "https://quizz-vn-admin.vercel.app"
                if BACKEND_URL.startswith("https://")
                else "http://localhost:3000"
            ),
        )
    )
    ADMIN_WEB_URL: str = _normalize_origin(os.getenv("ADMIN_WEB_URL", FRONTEND_URL))
    FRONTEND_AUTH_CALLBACK_PATH: str = os.getenv("FRONTEND_AUTH_CALLBACK_PATH", "/auth/callback").strip() or "/auth/callback"
    FRONTEND_EMAIL_VERIFICATION_PATH: str = (
        os.getenv("FRONTEND_EMAIL_VERIFICATION_PATH", "/verify-email").strip() or "/verify-email"
    )
    FRONTEND_ADMIN_INVITATION_PATH: str = (
        os.getenv("FRONTEND_ADMIN_INVITATION_PATH", "/admin/invitations/accept").strip()
        or "/admin/invitations/accept"
    )
    ADMIN_INVITATION_BASE_URL: str = _normalize_origin(
        os.getenv("ADMIN_INVITATION_BASE_URL", BACKEND_URL)
    )
    INCLUDE_LOCAL_DEV_CORS_ORIGINS: bool = _parse_bool(
        os.getenv("INCLUDE_LOCAL_DEV_CORS_ORIGINS"),
        not BACKEND_URL.startswith("https://"),
    )
    ALLOWED_ORIGINS: list[str] = _build_allowed_origins(
        FRONTEND_URL,
        os.getenv("ALLOWED_ORIGINS", ""),
        INCLUDE_LOCAL_DEV_CORS_ORIGINS,
        extra_origins=(ADMIN_WEB_URL,),
    )
    ALLOWED_ORIGIN_REGEX: str | None = os.getenv("ALLOWED_ORIGIN_REGEX", "").strip() or None
    SESSION_SECRET_KEY: str = os.getenv("SESSION_SECRET_KEY", "change_me")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "session_token")
    OAUTH_SESSION_COOKIE_NAME: str = os.getenv("OAUTH_SESSION_COOKIE_NAME", "oauth_session")
    REFRESH_COOKIE_NAME: str = os.getenv("REFRESH_COOKIE_NAME", "refresh_token")
    SESSION_EXPIRE_MINUTES: int = _parse_session_expire_minutes()
    SESSION_REFRESH_DAYS: int = int(os.getenv("SESSION_REFRESH_DAYS", "7"))
    COOKIE_SECURE: bool = _parse_bool(
        os.getenv("COOKIE_SECURE"),
        BACKEND_URL.startswith("https://"),
    )
    COOKIE_SAMESITE: str = os.getenv(
        "COOKIE_SAMESITE",
        "none" if COOKIE_SECURE else "lax",
    ).strip().lower()
    EMAIL_DELIVERY_MODE: str = os.getenv("EMAIL_DELIVERY_MODE", "log").strip().lower() or "log"
    EMAIL_FROM_ADDRESS: str = os.getenv("EMAIL_FROM_ADDRESS", "").strip()
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", APP_NAME).strip() or APP_NAME
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = _parse_bool(os.getenv("SMTP_USE_TLS"), True)
    SMTP_USE_SSL: bool = _parse_bool(os.getenv("SMTP_USE_SSL"), False)
    SMTP_TIMEOUT_SECONDS: int = int(os.getenv("SMTP_TIMEOUT_SECONDS", "15"))
    EMAIL_VERIFICATION_SECRET: str = (
        os.getenv("EMAIL_VERIFICATION_SECRET", SESSION_SECRET_KEY).strip() or SESSION_SECRET_KEY
    )
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = int(os.getenv("EMAIL_VERIFICATION_EXPIRE_HOURS", "24"))
    EMAIL_VERIFICATION_OTP_EXPIRE_MINUTES: int = int(os.getenv("EMAIL_VERIFICATION_OTP_EXPIRE_MINUTES", "15"))
    EMAIL_VERIFICATION_OTP_MAX_ATTEMPTS: int = int(os.getenv("EMAIL_VERIFICATION_OTP_MAX_ATTEMPTS", "5"))
    ADMIN_INVITATION_OTP_EXPIRE_MINUTES: int = int(os.getenv("ADMIN_INVITATION_OTP_EXPIRE_MINUTES", "15"))
    ADMIN_INVITATION_OTP_MAX_ATTEMPTS: int = int(os.getenv("ADMIN_INVITATION_OTP_MAX_ATTEMPTS", "5"))
    MAX_IMAGE_UPLOAD_BYTES: int = int(os.getenv("MAX_IMAGE_UPLOAD_BYTES", str(5 * 1024 * 1024)))
    MAX_CHAT_FILE_UPLOAD_BYTES: int = int(os.getenv("MAX_CHAT_FILE_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    MAX_DOCUMENT_UPLOAD_BYTES: int = int(os.getenv("MAX_DOCUMENT_UPLOAD_BYTES", str(20 * 1024 * 1024)))
    CLOUDINARY_URL: str = os.getenv("CLOUDINARY_URL", "").strip()
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "").strip()
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "").strip()
    CLOUDINARY_UPLOAD_FOLDER: str = os.getenv("CLOUDINARY_UPLOAD_FOLDER", "quiz/exam-images").strip() or "quiz/exam-images"
    CLOUDINARY_CHAT_UPLOAD_FOLDER: str = os.getenv("CLOUDINARY_CHAT_UPLOAD_FOLDER", "quiz/chat-files").strip() or "quiz/chat-files"
    CLOUDINARY_DOCUMENT_UPLOAD_FOLDER: str = (
        os.getenv("CLOUDINARY_DOCUMENT_UPLOAD_FOLDER", "quiz/documents").strip() or "quiz/documents"
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "").strip()
    CHAT_EVENTS_CHANNEL: str = os.getenv("CHAT_EVENTS_CHANNEL", "chat:events").strip() or "chat:events"
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini").strip().lower() or "gemini"
    AI_MODEL: str = os.getenv("AI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()

settings = Settings()
