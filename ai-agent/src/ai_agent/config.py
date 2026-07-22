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

    RAG_ENABLED = _as_bool("AI_AGENT_RAG_ENABLED", False)
    EMBEDDING_MODEL = (
        os.getenv("AI_AGENT_EMBEDDING_MODEL", "gemini-embedding-2").strip()
        or "gemini-embedding-2"
    )
    EMBEDDING_DIMENSIONS = max(
        128,
        min(int(os.getenv("AI_AGENT_EMBEDDING_DIMENSIONS", "768")), 3072),
    )
    EMBEDDING_TIMEOUT_SECONDS = float(
        os.getenv("AI_AGENT_EMBEDDING_TIMEOUT_SECONDS", "30")
    )
    RAG_TOP_K = max(1, min(int(os.getenv("AI_AGENT_RAG_TOP_K", "6")), 20))
    RAG_MIN_SIMILARITY = max(
        0.0,
        min(float(os.getenv("AI_AGENT_RAG_MIN_SIMILARITY", "0.72")), 1.0),
    )
    RAG_MAX_CONTEXT_CHARS = max(
        1000,
        min(int(os.getenv("AI_AGENT_RAG_MAX_CONTEXT_CHARS", "6000")), 20000),
    )
    RAG_INCLUDE_SYSTEM_KNOWLEDGE = _as_bool(
        "AI_AGENT_RAG_INCLUDE_SYSTEM_KNOWLEDGE",
        True,
    )

    ML_DATASET_ROOT = (
        os.getenv("AI_AGENT_ML_DATASET_ROOT", "/data/ml-datasets").strip()
        or "/data/ml-datasets"
    )
    ML_MIN_QUALITY_SCORE = max(
        0.0,
        min(float(os.getenv("AI_AGENT_ML_MIN_QUALITY_SCORE", "0.75")), 1.0),
    )
    ML_PRIVATE_OPT_IN_ENABLED = _as_bool(
        "AI_AGENT_ML_PRIVATE_OPT_IN_ENABLED",
        False,
    )
    ML_VALIDATION_PERCENT = max(
        0,
        min(int(os.getenv("AI_AGENT_ML_VALIDATION_PERCENT", "10")), 30),
    )
    ML_TEST_PERCENT = max(
        0,
        min(int(os.getenv("AI_AGENT_ML_TEST_PERCENT", "10")), 30),
    )
    ML_BASE_MODEL = (
        os.getenv("AI_AGENT_ML_BASE_MODEL", "Qwen/Qwen2.5-3B-Instruct").strip()
        or "Qwen/Qwen2.5-3B-Instruct"
    )
    ML_OUTPUT_ROOT = (
        os.getenv("AI_AGENT_ML_OUTPUT_ROOT", "/data/ml-models").strip()
        or "/data/ml-models"
    )
    ML_EVALUATION_THRESHOLD = max(
        0.0,
        min(float(os.getenv("AI_AGENT_ML_EVALUATION_THRESHOLD", "0.90")), 1.0),
    )


settings = Settings()
