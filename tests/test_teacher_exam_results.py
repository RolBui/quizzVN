import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.teacher_service import (
    _serialize_teacher_attempt_list_item,
    _serialize_teacher_attempt_result,
)


def _option(**overrides) -> SimpleNamespace:
    values = {
        "id": 1,
        "option_text": "Correct",
        "image_url": None,
        "is_correct": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _attempt() -> SimpleNamespace:
    submitted_at = datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc)
    correct_option = _option(id=10, option_text="A", is_correct=True)
    wrong_option = _option(id=11, option_text="B", is_correct=False)
    question = SimpleNamespace(
        id=100,
        question_type="single_choice",
        prompt="Question?",
        explanation="Because A is correct.",
        image_url=None,
        points=1.0,
        order_index=1,
        options=[correct_option, wrong_option],
    )
    answer = SimpleNamespace(
        question_id=question.id,
        selected_option=correct_option,
        answer_text=None,
    )
    exam = SimpleNamespace(
        id=20,
        title="History exam",
        questions=[question],
    )
    user = SimpleNamespace(
        id=5,
        full_name="Nguyen Van A",
        email="student@example.com",
        avatar_url=None,
    )
    return SimpleNamespace(
        id=30,
        exam_id=exam.id,
        exam=exam,
        user_id=user.id,
        user=user,
        status="submitted",
        score=1.0,
        total_points=1.0,
        correct_answers_count=1,
        answers=[answer],
        started_at=submitted_at,
        submitted_at=submitted_at,
        updated_at=submitted_at,
    )


class TeacherExamResultSerializerTest(unittest.TestCase):
    def test_serializes_teacher_attempt_list_item(self) -> None:
        item = _serialize_teacher_attempt_list_item(_attempt())

        self.assertEqual(item["attempt_id"], 30)
        self.assertEqual(item["student_id"], 5)
        self.assertEqual(item["student_name"], "Nguyen Van A")
        self.assertEqual(item["score_percent"], 100.0)
        self.assertTrue(item["is_passed"])

    def test_serializes_teacher_attempt_detail(self) -> None:
        result = _serialize_teacher_attempt_result(_attempt())

        self.assertEqual(result["attempt_id"], 30)
        self.assertEqual(result["exam_id"], 20)
        self.assertEqual(result["student_email"], "student@example.com")
        self.assertEqual(result["answers"][0]["selected_option_text"], "A")
        self.assertEqual(result["answers"][0]["correct_option_text"], "A")
        self.assertTrue(result["answers"][0]["is_correct"])
        self.assertEqual(result["answers"][0]["points_earned"], 1.0)


if __name__ == "__main__":
    unittest.main()
