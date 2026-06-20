import unittest

from app.services.ai_exam_validator import sanitize_ai_exam_payload, validate_ai_exam_payload


REQUEST_DATA = {
    "question_count": 2,
    "question_types": ["multiple_choice"],
}


def _question(content: str = "Question 1") -> dict:
    return {
        "type": "multiple_choice",
        "content": content,
        "options": ["A", "B", "C", "D"],
        "correct_answer": "A",
        "explanation": "A is correct.",
        "difficulty": "easy",
        "points": 1,
        "topic": "Python",
    }


def _payload(questions: list[dict]) -> dict:
    return {
        "title": "Python exam",
        "description": "Draft exam",
        "subject": "Tin hoc",
        "grade": "10",
        "duration_minutes": 15,
        "total_points": len(questions),
        "questions": questions,
    }


class AIExamValidatorTest(unittest.TestCase):
    def test_valid_multiple_choice_payload(self) -> None:
        payload = _payload(
            [
                _question("Question 1"),
                _question("Question 2"),
            ]
        )

        valid, errors = validate_ai_exam_payload(payload, REQUEST_DATA)

        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_rejects_wrong_question_count(self) -> None:
        payload = _payload(
            [
                _question("Question 1"),
            ]
        )

        valid, errors = validate_ai_exam_payload(payload, REQUEST_DATA)

        self.assertFalse(valid)
        self.assertIn("Expected 2 questions, got 1", errors)

    def test_rejects_multiple_choice_answer_outside_options(self) -> None:
        invalid_question = _question("Question 1")
        invalid_question["correct_answer"] = "Z"
        payload = _payload(
            [
                invalid_question,
                _question("Question 2"),
            ]
        )

        valid, errors = validate_ai_exam_payload(payload, REQUEST_DATA)

        self.assertFalse(valid)
        self.assertIn("Question 1: correct_answer is not in options", errors)

    def test_rejects_duplicate_question_content(self) -> None:
        payload = _payload(
            [
                _question("Same question"),
                _question("Same question"),
            ]
        )

        valid, errors = validate_ai_exam_payload(payload, REQUEST_DATA)

        self.assertFalse(valid)
        self.assertIn("Question 2: duplicate content", errors)

    def test_sanitizes_artificial_underline_markers_in_options(self) -> None:
        payload = _payload(
            [
                {
                    **_question("Choose the word whose underlined part is pronounced differently."),
                    "options": ["h_o_pe", "h_o_me", "c_o_me", "n_o_te"],
                    "correct_answer": "c_o_me",
                },
                _question("Question 2"),
            ]
        )

        sanitized = sanitize_ai_exam_payload(payload)
        valid, errors = validate_ai_exam_payload(sanitized, REQUEST_DATA)

        self.assertTrue(valid)
        self.assertEqual(sanitized["questions"][0]["options"], ["hope", "home", "come", "note"])
        self.assertEqual(sanitized["questions"][0]["correct_answer"], "come")
        self.assertEqual(errors, [])

    def test_rejects_duplicate_options_after_sanitizing(self) -> None:
        payload = _payload(
            [
                {
                    **_question("Question 1"),
                    "options": ["h_o_pe", "hope", "home", "come"],
                    "correct_answer": "hope",
                },
                _question("Question 2"),
            ]
        )

        sanitized = sanitize_ai_exam_payload(payload)
        valid, errors = validate_ai_exam_payload(sanitized, REQUEST_DATA)

        self.assertFalse(valid)
        self.assertIn("Question 1: options must be unique", errors)


if __name__ == "__main__":
    unittest.main()
