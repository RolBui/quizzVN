import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx

from ai_agent.provider import ProviderResult
from ai_agent.tasks import (
    CallbackValidationError,
    _callback_validation_errors,
    _deliver_with_semantic_repair,
    _generate_job_payload,
    _shadow_metrics,
)


class AgentCallbackTests(unittest.TestCase):
    def test_extracts_structured_semantic_validation_errors(self) -> None:
        response = httpx.Response(
            422,
            json={
                "detail": {
                    "code": "semantic_validation_failed",
                    "errors": ["Question 1 is invalid"],
                }
            },
        )

        self.assertEqual(
            _callback_validation_errors(response),
            ["Question 1 is invalid"],
        )

    @patch("ai_agent.tasks.get_provider")
    @patch("ai_agent.tasks._deliver_callback")
    def test_repairs_once_after_backend_semantic_rejection(
        self,
        deliver_callback: MagicMock,
        get_provider: MagicMock,
    ) -> None:
        deliver_callback.side_effect = [
            CallbackValidationError(["Question 1 is invalid"]),
            None,
        ]
        repaired_payload = {
            "questions": [
                {"type": "true_false", "correct_answer": True}
            ]
        }
        get_provider.return_value.generate.return_value = ProviderResult(
            payload=repaired_payload,
            raw_response={"repaired": True},
            attempts=1,
        )
        job = SimpleNamespace(
            prompt="original prompt",
            result_payload={
                "questions": [
                    {"type": "true_false", "correct_answer": "unknown"}
                ]
            },
            raw_response={"initial": True},
            error_message="",
            status="callback_pending",
            attempt_count=1,
        )
        db = MagicMock()

        _deliver_with_semantic_repair(db, job)

        self.assertEqual(deliver_callback.call_count, 2)
        self.assertEqual(job.result_payload, repaired_payload)
        self.assertEqual(job.error_message, "")
        db.commit.assert_called_once()

    @patch("ai_agent.tasks.get_provider")
    @patch("ai_agent.tasks._deliver_callback")
    def test_reports_failure_when_repaired_payload_is_still_invalid(
        self,
        deliver_callback: MagicMock,
        get_provider: MagicMock,
    ) -> None:
        deliver_callback.side_effect = [
            CallbackValidationError(["Question 1 is invalid"]),
            CallbackValidationError(["Question 1 is still invalid"]),
            None,
        ]
        get_provider.return_value.generate.return_value = ProviderResult(
            payload={"questions": [{"type": "true_false", "correct_answer": "unknown"}]},
            raw_response={"repaired": True},
            attempts=1,
        )
        job = SimpleNamespace(
            prompt="original prompt",
            result_payload={
                "questions": [{"type": "true_false", "correct_answer": "unknown"}]
            },
            raw_response={"initial": True},
            error_message="",
            status="callback_pending",
            attempt_count=1,
        )
        db = MagicMock()

        _deliver_with_semantic_repair(db, job)

        self.assertEqual(deliver_callback.call_count, 3)
        self.assertIsNone(job.result_payload)
        self.assertIn("after repair", job.error_message)
        self.assertEqual(db.commit.call_count, 2)


class AgentGenerationTests(unittest.TestCase):
    def test_shadow_metrics_compare_count_and_question_type_distribution(self) -> None:
        primary = {
            "questions": [
                {"type": "multiple_choice"},
                {"type": "true_false"},
            ]
        }
        shadow = {
            "questions": [
                {"type": "multiple_choice"},
                {"type": "short_answer"},
            ]
        }

        score, metrics = _shadow_metrics(primary, shadow)

        self.assertEqual(score, 0.5)
        self.assertTrue(metrics["count_match"])
        self.assertFalse(metrics["type_distribution_match"])

    @patch("ai_agent.tasks._set_progress")
    @patch("ai_agent.tasks.get_provider")
    def test_generates_large_job_in_multiple_batches(
        self,
        get_provider: MagicMock,
        set_progress: MagicMock,
    ) -> None:
        def payload(start: int, count: int) -> dict:
            return {
                "title": "Exam",
                "description": "Draft",
                "subject": "Math",
                "grade": "12",
                "duration_minutes": 45,
                "total_points": count,
                "questions": [
                    {
                        "type": "multiple_choice",
                        "content": f"Question {index}",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "Explanation",
                        "difficulty": "easy",
                        "points": 1,
                        "topic": "Topic",
                    }
                    for index in range(start, start + count)
                ],
            }

        get_provider.return_value.generate.side_effect = [
            ProviderResult(payload(1, 10), {"batch": 1}, 1),
            ProviderResult(payload(11, 5), {"batch": 2}, 1),
        ]
        job = SimpleNamespace(
            id="job-1",
            prompt="Create an exam",
            request_data={
                "question_count": 15,
                "question_types": ["multiple_choice"],
                "question_type_distribution": {"multiple_choice": 15},
                "difficulty_distribution": {"easy": 100, "medium": 0, "hard": 0},
            },
            attempt_count=0,
        )
        db = MagicMock()

        result, raw = _generate_job_payload(db, job)

        self.assertEqual(len(result["questions"]), 15)
        self.assertEqual(len(raw["batches"]), 2)
        self.assertEqual(get_provider.return_value.generate.call_count, 2)
        self.assertTrue(any(call.args[4] == 15 for call in set_progress.call_args_list))


if __name__ == "__main__":
    unittest.main()
