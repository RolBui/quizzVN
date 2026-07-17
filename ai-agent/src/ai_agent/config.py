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
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()
    SHARED_SECRET = os.getenv("AI_AGENT_SHARED_SECRET", "").strip()

    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower() or "gemini"
    AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    PROVIDER_TIMEOUT_SECONDS = float(os.getenv("AI_PROVIDER_TIMEOUT_SECONDS", "180"))
    PROVIDER_RETRY_COUNT = int(os.getenv("AI_PROVIDER_RETRY_COUNT", "3"))
    RETRY_BASE_SECONDS = float(os.getenv("AI_AGENT_RETRY_BASE_SECONDS", "5"))
    CALLBACK_TIMEOUT_SECONDS = float(os.getenv("AI_AGENT_CALLBACK_TIMEOUT_SECONDS", "15"))
    CALLBACK_RETRY_COUNT = int(os.getenv("AI_AGENT_CALLBACK_RETRY_COUNT", "5"))
    CELERY_EAGER = _as_bool("AI_AGENT_CELERY_EAGER", False)


settings = Settings()
