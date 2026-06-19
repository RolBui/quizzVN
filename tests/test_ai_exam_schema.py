import unittest

from pydantic import ValidationError

from app.schemas.ai_exam import GenerateExamRequest, GenerateMoreQuestionsRequest


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


class GenerateMoreQuestionsRequestTest(unittest.TestCase):
    def test_accepts_count_alias_and_distribution_counts(self) -> None:
        payload = GenerateMoreQuestionsRequest(
            count=5,
            question_types=["multiple_choice", "multiple_choice"],
            difficulty_distribution={
                "easy": 2,
                "normal": 2,
                "hard": 1,
            },
            additional_instructions="Them cau thay the.",
        )

        self.assertEqual(payload.question_count, 5)
        self.assertEqual(payload.question_types, ["multiple_choice"])
        self.assertEqual(
            payload.difficulty_distribution,
            {
                "easy": 2,
                "medium": 2,
                "hard": 1,
            },
        )

    def test_accepts_question_count_field_name(self) -> None:
        payload = GenerateMoreQuestionsRequest(question_count=3)

        self.assertEqual(payload.question_count, 3)
        self.assertIsNone(payload.question_types)

    def test_rejects_more_distribution_that_is_not_counts_or_percentages(self) -> None:
        with self.assertRaises(ValidationError):
            GenerateMoreQuestionsRequest(
                count=5,
                difficulty_distribution={
                    "easy": 2,
                    "medium": 2,
                    "hard": 2,
                },
            )


if __name__ == "__main__":
    unittest.main()
