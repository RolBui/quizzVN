import unittest

from pydantic import ValidationError

from app.schemas.ai_exam import GenerateExamRequest


class GenerateExamRequestTest(unittest.TestCase):
    def test_accepts_difficulty_distribution_as_question_counts(self) -> None:
        payload = GenerateExamRequest(
            subject="Lich Su",
            grade="10",
            topic="Lich Su Viet Nam",
            duration_minutes=45,
            question_count=35,
            question_types=["multiple_choice"],
            difficulty_distribution={
                "easy": 20,
                "normal": 10,
                "hard": 5,
            },
        )

        self.assertEqual(
            payload.difficulty_distribution,
            {
                "easy": 20,
                "medium": 10,
                "hard": 5,
            },
        )

    def test_accepts_difficulty_distribution_as_percentages(self) -> None:
        payload = GenerateExamRequest(
            subject="Tin hoc",
            grade="10",
            topic="Python",
            duration_minutes=15,
            question_count=10,
            question_types=["multiple_choice"],
            difficulty_distribution={
                "easy": 40,
                "medium": 40,
                "hard": 20,
            },
        )

        self.assertEqual(payload.difficulty_distribution["medium"], 40)

    def test_rejects_distribution_that_is_not_counts_or_percentages(self) -> None:
        with self.assertRaises(ValidationError):
            GenerateExamRequest(
                subject="Tin hoc",
                grade="10",
                topic="Python",
                duration_minutes=15,
                question_count=35,
                question_types=["multiple_choice"],
                difficulty_distribution={
                    "easy": 20,
                    "medium": 10,
                    "hard": 10,
                },
            )


if __name__ == "__main__":
    unittest.main()
