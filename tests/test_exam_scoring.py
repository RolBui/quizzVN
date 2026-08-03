import unittest
from decimal import Decimal

from fastapi import HTTPException

from app.services.exam_scoring import apply_exam_scoring


def _questions(count: int, points: float = 1.0) -> list[dict]:
    return [
        {"order_index": index, "points": points}
        for index in range(1, count + 1)
    ]


class ExamScoringTests(unittest.TestCase):
    def test_auto_distributes_exactly_ten_points(self):
        for count in (1, 3, 10, 53):
            with self.subTest(count=count):
                questions = _questions(count, points=99)
                total = apply_exam_scoring(
                    questions,
                    total_points=10,
                    point_mode="auto",
                )

                self.assertEqual(total, Decimal("10"))
                self.assertEqual(
                    sum(Decimal(str(question["points"])) for question in questions),
                    Decimal("10"),
                )
                self.assertTrue(
                    all(
                        Decimal(str(question["points"])) > 0
                        for question in questions
                    )
                )

        questions_53 = _questions(53)
        apply_exam_scoring(questions_53, total_points=10, point_mode="auto")
        point_values = [question["points"] for question in questions_53]
        self.assertEqual(point_values.count(Decimal("0.19")), 46)
        self.assertEqual(point_values.count(Decimal("0.18")), 7)

    def test_manual_accepts_totals_at_or_below_target(self):
        questions_98 = _questions(49, points=0.2)
        total_98 = apply_exam_scoring(
            questions_98,
            total_points=10,
            point_mode="manual",
        )
        self.assertEqual(total_98, Decimal("9.8"))

        questions_10 = _questions(4, points=2.5)
        total_10 = apply_exam_scoring(
            questions_10,
            total_points=10,
            point_mode="manual",
        )
        self.assertEqual(total_10, Decimal("10"))

    def test_manual_rejects_total_above_target(self):
        with self.assertRaises(HTTPException) as context:
            apply_exam_scoring(
                _questions(3, points=4),
                total_points=10,
                point_mode="manual",
            )

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("exceeds", context.exception.detail)

    def test_rejects_target_above_ten(self):
        with self.assertRaises(HTTPException) as context:
            apply_exam_scoring(
                _questions(2),
                total_points=10.01,
                point_mode="auto",
            )

        self.assertEqual(context.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
