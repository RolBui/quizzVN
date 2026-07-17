import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ai_agent.config import settings
from ai_agent.database import Base, get_db
from ai_agent.main import app


class AgentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_secret = settings.SHARED_SECRET
        settings.SHARED_SECRET = "test-shared-secret"
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
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


if __name__ == "__main__":
    unittest.main()
