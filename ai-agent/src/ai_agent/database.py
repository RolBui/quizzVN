from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from ai_agent.config import settings


is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
engine_options = {
    "pool_pre_ping": True,
    "connect_args": connect_args,
}
if not is_sqlite:
    engine_options.update(
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    )
engine = create_engine(settings.DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


if is_sqlite:
    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def bootstrap_storage() -> None:
    from ai_agent import models  # noqa: F401

    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    _ensure_agent_job_columns()
    _ensure_vector_index()


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


def _ensure_vector_index() -> None:
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_agent_knowledge_embedding_hnsw "
                "ON agent_knowledge_items USING hnsw (embedding vector_cosine_ops) "
                "WITH (m = 16, ef_construction = 64)"
            )
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
