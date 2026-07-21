import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.ai_agent_client import archive_approved_ai_dataset
from app.services.ai_exam_service import AIAgentDispatchError, save_ai_exam_job_to_quiz


class ApprovedDatasetClientTests(unittest.TestCase):
    @patch("app.services.ai_agent_client.httpx.Client")
    def test_sends_approved_dataset_with_internal_auth_and_idempotency(self, client_class) -> None:
        response = MagicMock()
        response.json.return_value = {"id": "artifact-1"}
        response.raise_for_status.return_value = None
        client = client_class.return_value.__enter__.return_value
        client.post.return_value = response

        with patch.object(settings, "AI_AGENT_URL", "https://ai.example"), patch.object(
            settings, "AI_AGENT_SHARED_SECRET", "secret"
        ):
            artifact_id = archive_approved_ai_dataset(
                {
                    "idempotency_key": "approved:job-1:exam-2:v1",
                    "external_job_id": "1",
                    "request_data": {"question_count": 1},
                    "questions": [{"type": "essay", "content": "Explain gravity"}],
                    "metadata": {"exam_id": "2"},
                }
            )

        self.assertEqual(artifact_id, "artifact-1")
        _, kwargs = client.post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(
            kwargs["headers"]["Idempotency-Key"],
            "approved:job-1:exam-2:v1",
        )

    @patch("app.services.ai_exam_service.archive_approved_ai_dataset")
    @patch("app.services.ai_exam_service.build_question_payload_from_draft")
    @patch("app.services.ai_exam_service.build_teacher_exam_questions_from_drafts")
    @patch("app.services.ai_exam_service.create_teacher_exam")
    @patch("app.services.ai_exam_service.get_teacher_ai_exam_job")
    def test_archive_failure_does_not_rollback_saved_exam(
        self,
        get_job,
        create_exam,
        build_questions,
        build_payload,
        archive_dataset,
    ) -> None:
        draft = SimpleNamespace(order=1, is_approved=True)
        job = SimpleNamespace(
            id=7,
            status="completed",
            quiz_id=None,
            question_drafts=[draft],
            title="AI exam",
            description="Draft",
            grade="12",
            duration_minutes=45,
            provider="gemini",
            model="gemini-test",
            updated_at=None,
        )
        get_job.return_value = job
        build_questions.return_value = [{"question": "Q1"}]
        build_payload.return_value = {"type": "essay", "content": "Q1"}
        create_exam.return_value = {"exam": {"id": 99}}
        archive_dataset.side_effect = AIAgentDispatchError("Drive unavailable")
        db = MagicMock()

        with patch.object(settings, "AI_EXECUTION_MODE", "agent"), patch(
            "app.services.ai_exam_service._build_request_data_from_job",
            return_value={"question_count": 1},
        ):
            result = save_ai_exam_job_to_quiz(db, SimpleNamespace(id=1), 7, {})

        self.assertEqual(result["exam_id"], 99)
        self.assertEqual(job.status, "converted")
        self.assertEqual(job.quiz_id, 99)
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
