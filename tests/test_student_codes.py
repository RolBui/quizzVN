import importlib
import pkgutil
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.database import Base
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import _next_student_code, assign_student_code
from app.services.teacher_service import _serialize_teacher_student_user


for module in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{module.name}")


class StudentCodeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        role = Role(name="student")
        self.db.add(role)
        self.db.flush()
        self.student_role = role

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _create_student(self, number: int) -> User:
        student = User(
            role_id=self.student_role.id,
            full_name=f"Student {number}",
            username=f"student-{number}",
            email=f"student-{number}@example.com",
        )
        self.db.add(student)
        self.db.flush()
        return student

    def test_first_code_in_2026_is_26001(self):
        self.assertEqual(_next_student_code([], 26), "26001")

    def test_sequence_uses_highest_valid_code_for_year(self):
        existing_codes = [
            "25099",
            "26001",
            "26007",
            "26ABC",
            "2601",
        ]

        self.assertEqual(_next_student_code(existing_codes, 26), "26008")

    def test_assigns_unique_stable_codes(self):
        issued_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
        first_student = self._create_student(1)
        second_student = self._create_student(2)

        first_code = assign_student_code(self.db, first_student, issued_at)
        second_code = assign_student_code(self.db, second_student, issued_at)
        repeated_code = assign_student_code(self.db, first_student, issued_at)

        self.assertEqual(first_code, "26001")
        self.assertEqual(second_code, "26002")
        self.assertEqual(repeated_code, "26001")

    def test_teacher_student_response_includes_code(self):
        issued_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
        student = self._create_student(1)
        assign_student_code(self.db, student, issued_at)
        self.db.commit()
        self.db.refresh(student)

        payload = _serialize_teacher_student_user(student)

        self.assertEqual(payload["student_code"], "26001")


if __name__ == "__main__":
    unittest.main()
