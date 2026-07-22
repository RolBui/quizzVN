import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from ai_agent.config import settings
from ai_agent.database import Base, get_db
from ai_agent.main import app


class AgentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_secret = settings.SHARED_SECRET
        settings.SHARED_SECRET = "test-shared-secret"
        self.database_path = Path.cwd() / f".agent-api-tests-{uuid4().hex}.db"
        engine = create_engine(
            URL.create("sqlite", database=str(self.database_path)),
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        self.engine = engine
        Base.metadata.create_all(engine)
        self.session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

        def override_db():
            db = self.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.payload = {
            "dispatch_id": "0123456789abcdef0123456789abcdef",
            "external_job_id": "42",
            "operation": "initial",
            "prompt": "Create an exam",
            "request_data": {"question_count": 1},
            "callback_url": "https://backend.example/api/callbacks/42",
        }
        self.headers = {
            "Authorization": "Bearer test-shared-secret",
            "Idempotency-Key": self.payload["dispatch_id"],
        }

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        settings.SHARED_SECRET = self.original_secret
        self.engine.dispose()
        self.database_path.unlink(missing_ok=True)

    def test_create_job_is_idempotent(self) -> None:
        with patch("ai_agent.main.generate_exam.apply_async") as delay:
            first = self.client.post("/v1/jobs", json=self.payload, headers=self.headers)
            second = self.client.post("/v1/jobs", json=self.payload, headers=self.headers)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json()["id"], second.json()["id"])
        delay.assert_called_once()

    def test_create_job_requires_internal_token(self) -> None:
        response = self.client.post(
            "/v1/jobs",
            json=self.payload,
            headers={"Idempotency-Key": self.payload["dispatch_id"]},
        )

        self.assertEqual(response.status_code, 401)

    def test_accepts_100_jobs_without_executing_them_in_request_thread(self) -> None:
        with patch("ai_agent.main.generate_exam.apply_async") as delay:
            responses = []
            for index in range(100):
                dispatch_id = f"{index:032x}"
                payload = {
                    **self.payload,
                    "dispatch_id": dispatch_id,
                    "external_job_id": str(index + 1),
                }
                headers = {
                    **self.headers,
                    "Idempotency-Key": dispatch_id,
                }
                responses.append(self.client.post("/v1/jobs", json=payload, headers=headers))

        self.assertTrue(all(response.status_code == 202 for response in responses))
        self.assertTrue(all(response.json()["status"] == "queued" for response in responses))
        self.assertEqual(delay.call_count, 100)

    def test_accepts_20_jobs_submitted_concurrently(self) -> None:
        def submit(index: int):
            dispatch_id = f"{index + 1000:032x}"
            payload = {
                **self.payload,
                "dispatch_id": dispatch_id,
                "external_job_id": str(index + 1),
            }
            headers = {
                **self.headers,
                "Idempotency-Key": dispatch_id,
            }
            return self.client.post("/v1/jobs", json=payload, headers=headers)

        with patch("ai_agent.main.generate_exam.apply_async") as delay:
            with ThreadPoolExecutor(max_workers=20) as executor:
                responses = list(executor.map(submit, range(20)))

        self.assertTrue(all(response.status_code == 202 for response in responses))
        self.assertTrue(all(response.json()["status"] == "queued" for response in responses))
        self.assertEqual(len({response.json()["id"] for response in responses}), 20)
        self.assertEqual(delay.call_count, 20)

    def test_approved_dataset_is_idempotent_and_queued(self) -> None:
        payload = {
            "idempotency_key": "approved:job-42:exam-7:v1",
            "external_job_id": "42",
            "request_data": {"subject": "Math", "question_count": 1},
            "questions": [
                {
                    "type": "short_answer",
                    "content": "What is 1 + 1?",
                    "correct_answer": ["2"],
                }
            ],
            "metadata": {"exam_id": "7"},
        }
        headers = {
            "Authorization": "Bearer test-shared-secret",
            "Idempotency-Key": payload["idempotency_key"],
        }
        with patch("ai_agent.main.data_lake_configuration_status", return_value="configured"), patch(
            "ai_agent.main.archive_artifact.apply_async"
        ) as delay:
            first = self.client.post("/v1/datasets/approved", json=payload, headers=headers)
            second = self.client.post("/v1/datasets/approved", json=payload, headers=headers)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(first.json()["artifact_type"], "approved")
        self.assertEqual(delay.call_count, 1)

    def test_ml_dataset_snapshot_is_idempotent_and_queued(self) -> None:
        payload = {
            "name": "approved-system-v1",
            "include_private_opt_in": False,
            "min_quality_score": 0.8,
        }
        headers = {
            "Authorization": "Bearer test-shared-secret",
            "Idempotency-Key": "ml-dataset-0000000000000001",
        }
        with patch("ai_agent.main.export_training_dataset.apply_async") as delay:
            first = self.client.post("/v1/ml/datasets", json=payload, headers=headers)
            second = self.client.post("/v1/ml/datasets", json=payload, headers=headers)

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(first.json()["status"], "queued")
        delay.assert_called_once()

    def test_ml_dataset_snapshot_rejects_private_export_when_disabled(self) -> None:
        original_private_enabled = settings.ML_PRIVATE_OPT_IN_ENABLED
        settings.ML_PRIVATE_OPT_IN_ENABLED = False
        try:
            response = self.client.post(
                "/v1/ml/datasets",
                json={"name": "private-v1", "include_private_opt_in": True},
                headers={
                    "Authorization": "Bearer test-shared-secret",
                    "Idempotency-Key": "ml-private-0000000000000001",
                },
            )
        finally:
            settings.ML_PRIVATE_OPT_IN_ENABLED = original_private_enabled

        self.assertEqual(response.status_code, 403)

    def test_ml_dataset_snapshot_retries_dispatch_failure_idempotently(self) -> None:
        payload = {"name": "retry-system-v1"}
        headers = {
            "Authorization": "Bearer test-shared-secret",
            "Idempotency-Key": "ml-dataset-retry-000000000001",
        }
        with patch(
            "ai_agent.main.export_training_dataset.apply_async",
            side_effect=[RuntimeError("queue offline"), None],
        ) as delay:
            first = self.client.post("/v1/ml/datasets", json=payload, headers=headers)
            second = self.client.post("/v1/ml/datasets", json=payload, headers=headers)

        self.assertEqual(first.status_code, 503)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.json()["status"], "queued")
        self.assertEqual(delay.call_count, 2)


if __name__ == "__main__":
    unittest.main()
