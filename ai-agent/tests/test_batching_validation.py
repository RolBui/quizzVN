import unittest

from ai_agent.batching import aggregate_batch_payloads, build_batch_specs
from ai_agent.validation import validate_exam_payload


def _question(index: int, question_type: str, difficulty: str = "easy") -> dict:
    options = ["A", "B", "C", "D"] if question_type == "multiple_choice" else []
    answer = "A" if question_type == "multiple_choice" else True
    if question_type == "short_answer":
        answer = "Answer"
    if question_type == "essay":
        answer = None
    return {
        "type": question_type,
        "content": f"Question {index}",
        "options": options,
        "correct_answer": answer,
        "explanation": "Explanation",
        "difficulty": difficulty,
        "points": 1,
        "topic": "Topic",
    }


def _payload(questions: list[dict]) -> dict:
    return {
        "title": "Exam",
        "description": "Draft",
        "subject": "Math",
        "grade": "12",
        "duration_minutes": 45,
        "total_points": len(questions),
        "questions": questions,
    }


class AgentBatchingTests(unittest.TestCase):
    def test_splits_two_selected_types_and_preserves_exact_counts(self) -> None:
        request_data = {
            "question_count": 30,
            "question_types": ["multiple_choice", "true_false"],
            "question_type_distribution": {
                "multiple_choice": 20,
                "true_false": 10,
            },
            "difficulty_distribution": {"easy": 12, "medium": 12, "hard": 6},
        }

        batches = build_batch_specs(request_data, 10)

        self.assertEqual(
            [batch["question_type_distribution"] for batch in batches],
            [
                {"multiple_choice": 10},
                {"multiple_choice": 10},
                {"true_false": 10},
            ],
        )

    def test_splits_25_questions_into_10_10_5_and_preserves_distribution(self) -> None:
        request_data = {
            "question_count": 25,
            "question_types": ["multiple_choice", "true_false", "short_answer", "essay"],
            "question_type_distribution": {
                "multiple_choice": 10,
                "true_false": 8,
                "short_answer": 4,
                "essay": 3,
            },
            "difficulty_distribution": {"easy": 10, "medium": 10, "hard": 5},
        }

        batches = build_batch_specs(request_data, 10)

        self.assertEqual([batch["question_count"] for batch in batches], [10, 10, 5])
        merged_types: dict[str, int] = {}
        merged_difficulties: dict[str, int] = {}
        for batch in batches:
            for key, value in batch["question_type_distribution"].items():
                merged_types[key] = merged_types.get(key, 0) + value
            for key, value in batch["difficulty_distribution"].items():
                merged_difficulties[key] = merged_difficulties.get(key, 0) + value
        self.assertEqual(merged_types, request_data["question_type_distribution"])
        self.assertEqual(merged_difficulties, request_data["difficulty_distribution"])

    def test_aggregates_questions_and_recalculates_points(self) -> None:
        combined = aggregate_batch_payloads(
            [
                _payload([_question(1, "multiple_choice")]),
                _payload([_question(2, "true_false")]),
            ]
        )

        self.assertEqual(len(combined["questions"]), 2)
        self.assertEqual(combined["total_points"], 2)


class AgentValidationTests(unittest.TestCase):
    def test_rejects_duration_that_conflicts_with_structured_request(self) -> None:
        request_data = {
            "duration_minutes": 45,
            "question_count": 1,
            "question_types": ["multiple_choice"],
            "question_type_distribution": {"multiple_choice": 1},
            "difficulty_distribution": {"easy": 1},
        }
        payload = _payload([_question(1, "multiple_choice")])
        payload["duration_minutes"] = 15

        _, errors = validate_exam_payload(payload, request_data)

        self.assertIn("Expected duration_minutes 45, got 15", errors)

    def test_accepts_all_four_supported_question_types(self) -> None:
        request_data = {
            "question_count": 4,
            "question_types": ["multiple_choice", "true_false", "short_answer", "essay"],
            "question_type_distribution": {
                "multiple_choice": 1,
                "true_false": 1,
                "short_answer": 1,
                "essay": 1,
            },
            "difficulty_distribution": {"easy": 4},
        }

        _, errors = validate_exam_payload(
            _payload(
                [
                    _question(1, "multiple_choice"),
                    _question(2, "true_false"),
                    _question(3, "short_answer"),
                    _question(4, "essay"),
                ]
            ),
            request_data,
        )

        self.assertEqual(errors, [])

    def test_normalizes_real_vietnamese_true_answer(self) -> None:
        request_data = {
            "question_count": 1,
            "question_types": ["true_false"],
            "question_type_distribution": {"true_false": 1},
            "difficulty_distribution": {"easy": 1},
        }
        question = _question(1, "true_false")
        question["correct_answer"] = "\u0110\u00fang"

        normalized, errors = validate_exam_payload(_payload([question]), request_data)

        self.assertEqual(errors, [])
        self.assertIs(normalized["questions"][0]["correct_answer"], True)

    def test_rejects_duplicate_against_previous_batch(self) -> None:
        request_data = {
            "question_count": 1,
            "question_types": ["multiple_choice"],
            "question_type_distribution": {"multiple_choice": 1},
            "difficulty_distribution": {"easy": 1},
        }

        _, errors = validate_exam_payload(
            _payload([_question(1, "multiple_choice")]),
            request_data,
            existing_questions=[_question(1, "multiple_choice")],
        )

        self.assertIn("Question 1: duplicate content", errors)


if __name__ == "__main__":
    unittest.main()
