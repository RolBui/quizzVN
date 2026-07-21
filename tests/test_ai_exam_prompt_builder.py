import unittest

from app.services.ai_exam_prompt_builder import build_exam_generation_prompt


class AIExamPromptBuilderTests(unittest.TestCase):
    def test_includes_only_selected_question_type_formats(self) -> None:
        prompt = build_exam_generation_prompt(
            {
                "subject": "Địa lý",
                "grade": "12",
                "topic": "Luyện thi THPTQG",
                "duration_minutes": 45,
                "question_count": 30,
                "question_types": ["multiple_choice", "true_false"],
                "question_type_distribution": {
                    "multiple_choice": 20,
                    "true_false": 10,
                },
                "difficulty_distribution": {"easy": 40, "medium": 40, "hard": 20},
                "language": "Vietnamese",
                "additional_instructions": "",
            }
        )

        self.assertIn('"multiple_choice": {', prompt)
        self.assertIn('"true_false": {', prompt)
        self.assertNotIn('"short_answer": {', prompt)
        self.assertNotIn('"essay": {', prompt)
        self.assertIn('"multiple_choice": 20', prompt)
        self.assertIn('"true_false": 10', prompt)
        self.assertIn("structured Exam requirements above are authoritative", prompt)
        self.assertIn("conflicting duration", prompt)

    def test_documents_all_four_question_type_contracts(self) -> None:
        prompt = build_exam_generation_prompt(
            {
                "subject": "Toán",
                "grade": "12",
                "topic": "Tích phân",
                "duration_minutes": 45,
                "question_count": 4,
                "question_types": ["multiple_choice", "true_false", "short_answer", "essay"],
                "question_type_distribution": {
                    "multiple_choice": 1,
                    "true_false": 1,
                    "short_answer": 1,
                    "essay": 1,
                },
                "difficulty_distribution": {"easy": 1, "medium": 2, "hard": 1},
                "language": "Vietnamese",
                "additional_instructions": "",
            }
        )

        for question_type in ("multiple_choice", "true_false", "short_answer", "essay"):
            self.assertIn(f'"{question_type}": {{', prompt)


if __name__ == "__main__":
    unittest.main()
