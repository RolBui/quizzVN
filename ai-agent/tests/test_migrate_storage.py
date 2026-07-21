import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, func, select

from ai_agent.database import Base
from ai_agent.migrate_storage import migrate_storage
from ai_agent.models import AgentAttempt, AgentJob


class StorageMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source_path = Path.cwd() / f".migration-source-{uuid4().hex}.db"
        self.target_path = Path.cwd() / f".migration-target-{uuid4().hex}.db"
        self.source_url = f"sqlite:///{self.source_path.as_posix()}"
        self.target_url = f"sqlite:///{self.target_path.as_posix()}"
        source = create_engine(self.source_url)
        Base.metadata.create_all(source)
        with source.begin() as connection:
            connection.execute(
                AgentJob.__table__.insert(),
                {
                    "id": "job-1",
                    "dispatch_id": "dispatch-0000000000000001",
                    "external_job_id": "42",
                    "operation": "initial",
                    "prompt": "Create an exam",
                    "request_data": {"question_count": 1},
                    "callback_url": "https://backend.example/callback",
                    "status": "completed",
                },
            )
            connection.execute(
                AgentAttempt.__table__.insert(),
                {
                    "id": 1,
                    "job_id": "job-1",
                    "attempt_number": 1,
                    "status": "completed",
                },
            )
        source.dispose()

    def tearDown(self) -> None:
        self.source_path.unlink(missing_ok=True)
        self.target_path.unlink(missing_ok=True)

    def test_migrates_jobs_and_attempts_to_empty_database(self) -> None:
        counts = migrate_storage(self.source_url, self.target_url)
        target = create_engine(self.target_url)
        try:
            with target.connect() as connection:
                job_count = connection.execute(
                    select(func.count()).select_from(AgentJob.__table__)
                ).scalar_one()
                attempt_count = connection.execute(
                    select(func.count()).select_from(AgentAttempt.__table__)
                ).scalar_one()
        finally:
            target.dispose()

        self.assertEqual(counts["agent_jobs"], 1)
        self.assertEqual(counts["agent_attempts"], 1)
        self.assertEqual(job_count, 1)
        self.assertEqual(attempt_count, 1)

    def test_refuses_to_merge_into_nonempty_database(self) -> None:
        migrate_storage(self.source_url, self.target_url)
        with self.assertRaisesRegex(RuntimeError, "must be empty"):
            migrate_storage(self.source_url, self.target_url)


if __name__ == "__main__":
    unittest.main()
