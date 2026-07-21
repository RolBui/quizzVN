import os

from dotenv import load_dotenv


load_dotenv()


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() == "true"


class Settings:
    APP_NAME = os.getenv("AI_AGENT_APP_NAME", "QuizzVN AI Agent").strip() or "QuizzVN AI Agent"
    DEBUG = _as_bool("DEBUG", False)
    DATABASE_URL = os.getenv("AI_AGENT_DATABASE_URL", "sqlite:///./ai_agent.db").strip()
    DB_POOL_SIZE = max(1, int(os.getenv("AI_AGENT_DB_POOL_SIZE", "5")))
    DB_MAX_OVERFLOW = max(0, int(os.getenv("AI_AGENT_DB_MAX_OVERFLOW", "5")))
    DB_POOL_RECYCLE_SECONDS = max(60, int(os.getenv("AI_AGENT_DB_POOL_RECYCLE_SECONDS", "300")))
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
    SHARED_SECRET = os.getenv("AI_AGENT_SHARED_SECRET", "").strip()

    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower() or "gemini"
    AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    PROVIDER_TIMEOUT_SECONDS = float(os.getenv("AI_PROVIDER_TIMEOUT_SECONDS", "180"))
    PROVIDER_RETRY_COUNT = int(os.getenv("AI_PROVIDER_RETRY_COUNT", "3"))
    RETRY_BASE_SECONDS = float(os.getenv("AI_AGENT_RETRY_BASE_SECONDS", "5"))
    BATCH_SIZE = max(1, min(int(os.getenv("AI_AGENT_BATCH_SIZE", "10")), 50))
    SEMANTIC_REPAIR_COUNT = max(
        0,
        min(int(os.getenv("AI_AGENT_SEMANTIC_REPAIR_COUNT", "2")), 3),
    )
    TASK_RATE_LIMIT = os.getenv("AI_AGENT_TASK_RATE_LIMIT", "").strip()
    CALLBACK_TIMEOUT_SECONDS = float(os.getenv("AI_AGENT_CALLBACK_TIMEOUT_SECONDS", "15"))
    CALLBACK_RETRY_COUNT = int(os.getenv("AI_AGENT_CALLBACK_RETRY_COUNT", "5"))
    CELERY_EAGER = _as_bool("AI_AGENT_CELERY_EAGER", False)

    DATA_LAKE_ENABLED = _as_bool("AI_AGENT_DATA_LAKE_ENABLED", False)
    DATA_LAKE_PROVIDER = (
        os.getenv("AI_AGENT_DATA_LAKE_PROVIDER", "google_drive").strip().lower()
        or "google_drive"
    )
    DATA_LAKE_TIMEOUT_SECONDS = float(os.getenv("AI_AGENT_DATA_LAKE_TIMEOUT_SECONDS", "30"))
    GOOGLE_DRIVE_CLIENT_ID = os.getenv("AI_AGENT_GOOGLE_DRIVE_CLIENT_ID", "").strip()
    GOOGLE_DRIVE_CLIENT_SECRET = os.getenv("AI_AGENT_GOOGLE_DRIVE_CLIENT_SECRET", "").strip()
    GOOGLE_DRIVE_REFRESH_TOKEN = os.getenv("AI_AGENT_GOOGLE_DRIVE_REFRESH_TOKEN", "").strip()
    GOOGLE_DRIVE_FOLDER_ID = os.getenv("AI_AGENT_GOOGLE_DRIVE_FOLDER_ID", "").strip()
    GOOGLE_DRIVE_FOLDER_NAME = (
        os.getenv("AI_AGENT_GOOGLE_DRIVE_FOLDER_NAME", "QuizzVN AI Dataset").strip()
        or "QuizzVN AI Dataset"
    )


settings = Settings()
