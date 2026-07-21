import argparse
import os
from collections.abc import Iterable

from sqlalchemy import MetaData, create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine

from ai_agent.database import Base
from ai_agent import models  # noqa: F401


TABLE_ORDER = ("agent_jobs", "agent_attempts", "agent_artifacts")


def migrate_storage(source_url: str, target_url: str) -> dict[str, int]:
    if source_url == target_url:
        raise ValueError("Source and target database URLs must be different")

    source = create_engine(source_url, pool_pre_ping=True)
    target = create_engine(target_url, pool_pre_ping=True)
    try:
        Base.metadata.create_all(target)
        _assert_target_is_empty(target)
        source_metadata = MetaData()
        source_metadata.reflect(bind=source)
        migrated: dict[str, int] = {}

        for table_name in TABLE_ORDER:
            if table_name not in source_metadata.tables:
                migrated[table_name] = 0
                continue
            source_table = source_metadata.tables[table_name]
            target_table = Base.metadata.tables[table_name]
            target_columns = {column.name for column in target_table.columns}
            with source.connect() as connection:
                rows = [
                    {
                        key: value
                        for key, value in dict(row).items()
                        if key in target_columns
                    }
                    for row in connection.execute(select(source_table)).mappings()
                ]
            if rows:
                with target.begin() as connection:
                    connection.execute(target_table.insert(), rows)
            migrated[table_name] = len(rows)

        _reset_postgres_sequence(target, "agent_attempts", "id")
        return migrated
    finally:
        source.dispose()
        target.dispose()


def _assert_target_is_empty(engine: Engine) -> None:
    inspector = inspect(engine)
    nonempty: list[str] = []
    with engine.connect() as connection:
        for table_name in TABLE_ORDER:
            if table_name not in inspector.get_table_names():
                continue
            table = Base.metadata.tables[table_name]
            count = int(connection.execute(select(func.count()).select_from(table)).scalar_one())
            if count:
                nonempty.append(f"{table_name}={count}")
    if nonempty:
        raise RuntimeError(
            "Target database must be empty before migration: " + ", ".join(nonempty)
        )


def _reset_postgres_sequence(engine: Engine, table_name: str, column_name: str) -> None:
    if engine.dialect.name != "postgresql":
        return
    statement = text(
        "SELECT setval(pg_get_serial_sequence(:table_name, :column_name), "
        "COALESCE((SELECT MAX(id) FROM agent_attempts), 1), "
        "(SELECT COUNT(*) > 0 FROM agent_attempts))"
    )
    with engine.begin() as connection:
        connection.execute(
            statement,
            {"table_name": table_name, "column_name": column_name},
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate QuizzVN AI Agent storage from SQLite to an empty PostgreSQL database."
    )
    parser.add_argument(
        "--source",
        default=os.getenv("AI_AGENT_MIGRATION_SOURCE_URL", "sqlite:////data/ai_agent.db"),
    )
    parser.add_argument(
        "--target",
        default=os.getenv("AI_AGENT_MIGRATION_TARGET_URL", ""),
    )
    return parser


def main(args: Iterable[str] | None = None) -> int:
    options = _parser().parse_args(args)
    if not options.target:
        raise SystemExit("AI_AGENT_MIGRATION_TARGET_URL or --target is required")
    result = migrate_storage(options.source, options.target)
    for table_name, count in result.items():
        print(f"{table_name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
