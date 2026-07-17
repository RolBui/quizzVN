from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from ai_agent.config import settings


connect_args = (
    {"check_same_thread": False, "timeout": 30}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def bootstrap_storage() -> None:
    from ai_agent import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_agent_job_columns()


def _ensure_agent_job_columns() -> None:
    existing = {column["name"] for column in inspect(engine).get_columns("agent_jobs")}
    columns = {
        "stage": "VARCHAR(30) NOT NULL DEFAULT 'queued'",
        "progress_current": "INTEGER NOT NULL DEFAULT 0",
        "progress_total": "INTEGER NOT NULL DEFAULT 0",
        "progress_message": "TEXT NOT NULL DEFAULT ''",
        "priority": "INTEGER NOT NULL DEFAULT 0",
    }
    with engine.begin() as connection:
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE agent_jobs ADD COLUMN {name} {definition}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
