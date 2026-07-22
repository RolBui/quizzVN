import argparse
import hashlib
import json
import unittest
from pathlib import Path
from uuid import uuid4

from ai_agent.ml_training import (
    _parse_json_object,
    _structural_match,
    validate_dataset,
)


class MLTrainingValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset_dir = Path.cwd() / f".ml-dataset-{uuid4().hex}"
        self.dataset_dir.mkdir()

    def tearDown(self) -> None:
        for path in self.dataset_dir.glob("*"):
            path.unlink(missing_ok=True)
        self.dataset_dir.rmdir()

    def test_structural_match_supports_all_question_types(self) -> None:
        base = {
            "content": "Noi dung cau hoi hop le",
            "explanation": "Giai thich dap an ro rang",
            "difficulty": "medium",
            "topic": "Kiem thu",
        }
        candidates = [
            {
                **base,
                "type": "multiple_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
            },
            {**base, "type": "true_false", "options": [], "correct_answer": True},
            {**base, "type": "short_answer", "options": [], "correct_answer": "42"},
            {**base, "type": "essay", "options": [], "correct_answer": "Huong dan cham"},
        ]

        for candidate in candidates:
            with self.subTest(question_type=candidate["type"]):
                self.assertTrue(_structural_match(candidate, candidate))

    def test_structural_match_rejects_text_true_false_answer(self) -> None:
        candidate = {
            "type": "true_false",
            "content": "Noi dung cau hoi hop le",
            "options": [],
            "correct_answer": "dung",
            "explanation": "Giai thich dap an ro rang",
            "difficulty": "medium",
            "topic": "Kiem thu",
        }
        self.assertFalse(_structural_match(candidate, candidate))

    def test_parse_json_object_accepts_fenced_json(self) -> None:
        parsed = _parse_json_object('```json\n{"type":"true_false"}\n```')
        self.assertEqual(parsed, {"type": "true_false"})

    def test_validate_dataset_passes_clean_snapshot(self) -> None:
        self._write_snapshot()
        report = validate_dataset(
            argparse.Namespace(dataset_dir=str(self.dataset_dir), output_report=None)
        )

        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["training_allowed"])
        self.assertEqual(report["counts"]["train"], 1)

    def test_validate_dataset_rejects_cross_split_duplicate(self) -> None:
        row = self._row("a" * 64)
        self._write_snapshot(train=[row], validation=[row])
        report = validate_dataset(
            argparse.Namespace(dataset_dir=str(self.dataset_dir), output_report=None)
        )

        self.assertEqual(report["status"], "failed")
        self.assertFalse(report["training_allowed"])
        self.assertIn(
            "duplicate_content_hash",
            {failure["reason"] for failure in report["failures"]},
        )

    def test_validate_dataset_rejects_owner_identifier(self) -> None:
        row = self._row("b" * 64)
        row["metadata"]["teacher_id"] = 7
        self._write_snapshot(train=[row])
        report = validate_dataset(
            argparse.Namespace(dataset_dir=str(self.dataset_dir), output_report=None)
        )

        self.assertIn(
            "owner_identifier_present",
            {failure["reason"] for failure in report["failures"]},
        )

    def _write_snapshot(
        self,
        *,
        train: list[dict] | None = None,
        validation: list[dict] | None = None,
        test: list[dict] | None = None,
    ) -> None:
        rows_by_split = {
            "train": train if train is not None else [self._row("a" * 64)],
            "validation": validation or [],
            "test": test or [],
        }
        checksums = {}
        counts = {}
        for split, rows in rows_by_split.items():
            content = "".join(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                for row in rows
            )
            filename = f"{split}.jsonl"
            encoded = content.encode("utf-8")
            (self.dataset_dir / filename).write_bytes(encoded)
            checksums[filename] = hashlib.sha256(encoded).hexdigest()
            counts[split] = len(rows)
        manifest = {"checksums": checksums, "counts": counts}
        (self.dataset_dir / "manifest.json").write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

    @staticmethod
    def _row(content_hash: str) -> dict:
        answer = {
            "type": "multiple_choice",
            "content": "Noi dung cau hoi du dai va hop le",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Giai thich dap an ro rang",
            "difficulty": "medium",
            "topic": "Kiem thu",
        }
        return {
            "messages": [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "User"},
                {"role": "assistant", "content": json.dumps(answer)},
            ],
            "metadata": {"content_hash": content_hash},
        }


if __name__ == "__main__":
    unittest.main()
