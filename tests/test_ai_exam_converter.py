import unittest
from types import SimpleNamespace

from app.services.ai_exam_service import build_teacher_exam_questions_from_drafts


def _draft(**overrides) -> SimpleNamespace:
    values = {
        "question_type": "multiple_choice",
        "content": "What is Python?",
        "options": ["Language", "Snake", "Car", "Food"],
        "correct_answer": "Language",
        "explanation": "Python is a programming language.",
        "difficulty": "easy",
        "points": 1,
        "topic": "Python",
        "order": 1,
        "is_approved": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class AIExamConverterTest(unittest.TestCase):
    def test_maps_multiple_choice_to_single_choice(self) -> None:
        questions = build_teacher_exam_questions_from_drafts([_draft()])

        self.assertEqual(questions[0]["question_type"], "single_choice")
        self.assertEqual(len(questions[0]["options"]), 4)
        self.assertEqual(questions[0]["options"][0]["option_key"], "A")
        self.assertTrue(questions[0]["options"][0]["is_correct"])
        self.assertEqual(questions[0]["explanation"], "Python is a programming language.")

    def test_maps_true_false_to_true_false(self) -> None:
        questions = build_teacher_exam_questions_from_drafts(
            [
                _draft(
                    question_type="true_false",
                    options=[],
                    correct_answer=False,
                )
            ]
        )

        self.assertEqual(questions[0]["question_type"], "true_false")
        self.assertEqual(questions[0]["options"][0]["option_text"], "Đúng")
        self.assertFalse(questions[0]["options"][0]["is_correct"])
        self.assertTrue(questions[0]["options"][1]["is_correct"])

    def test_maps_short_answer_to_short_answer(self) -> None:
        questions = build_teacher_exam_questions_from_drafts(
            [
                _draft(
                    question_type="short_answer",
                    options=[],
                    correct_answer=["Python", "python"],
                )
            ]
        )

        self.assertEqual(questions[0]["question_type"], "short_answer")
        self.assertEqual(questions[0]["accepted_answers"], ["Python", "python"])

    def test_maps_essay_rubric_into_prompt(self) -> None:
        questions = build_teacher_exam_questions_from_drafts(
            [
                _draft(
                    question_type="essay",
                    content="Analyze the poem.",
                    options=[],
                    correct_answer=None,
                    explanation="Grade clarity and textual evidence.",
                )
            ]
        )

        self.assertEqual(questions[0]["question_type"], "text")
        self.assertIn("Hướng dẫn chấm", questions[0]["prompt"])
        self.assertEqual(questions[0]["accepted_answers"], ["Grade clarity and textual evidence."])
        self.assertEqual(questions[0]["explanation"], "Grade clarity and textual evidence.")


if __name__ == "__main__":
    unittest.main()
