import importlib
import pkgutil
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models as models_pkg
from app.database import Base, get_db
from app.dependencies.auth import get_current_teacher
from app.main import app
from app.models.classroom import Classroom
from app.models.role import Role
from app.models.user import User

for module in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{module.name}")


class TeacherExamAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(bind=self.engine)
        self.db = self.TestingSessionLocal()

        teacher_role = Role(name="teacher")
        self.db.add(teacher_role)
        self.db.flush()

        self.teacher = User(
            role_id=teacher_role.id,
            full_name="Giáo Viên A",
            username="teacher_a",
            email="teacher_a@example.com",
            status="active",
        )
        self.db.add(self.teacher)
        self.db.commit()

        self.classroom = Classroom(
            name="Lớp 12A1",
            description="Lớp toán 12A1",
            join_code="CLASS12A1",
            created_by_user_id=self.teacher.id,
        )
        self.db.add(self.classroom)
        self.db.commit()

        def _get_test_db():
            try:
                yield self.db
            finally:
                pass

        def _get_test_teacher():
            return self.teacher

        app.dependency_overrides[get_db] = _get_test_db
        app.dependency_overrides[get_current_teacher] = _get_test_teacher
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def _create_system_exam(self):
        payload = {
            "title": "Đề thi thử THPT Quốc Gia",
            "description": "Đề thi mẫu môn Toán",
            "grade": "Lớp 12",
            "duration_minutes": 90,
            "is_published": True,
            "is_active": True,
            "total_points": 10.0,
            "point_mode": "auto",
            "assignment_type": "exam",
            "questions": [
                {
                    "question_type": "single_choice",
                    "prompt": "Câu 1: 1 + 1 bằng bao nhiêu?",
                    "explanation": "1 + 1 = 2",
                    "order_index": 1,
                    "points": 5.0,
                    "options": [
                        {"option_key": "A", "option_text": "2", "is_correct": True},
                        {"option_key": "B", "option_text": "3", "is_correct": False},
                    ],
                },
                {
                    "question_type": "text",
                    "prompt": "Câu 2: Nhập tên thủ đô Việt Nam.",
                    "explanation": "Hà Nội",
                    "order_index": 2,
                    "points": 5.0,
                    "accepted_answers": ["Hà Nội", "ha noi"],
                },
            ],
        }
        resp = self.client.post("/teacher/system/exams", json=payload)
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()["exam"]

    def test_assign_exam_as_exam_with_duplicate(self):
        system_exam = self._create_system_exam()

        assign_payload = {
            "classroom_id": self.classroom.id,
            "assignment_type": "exam",
            "is_published": True,
            "duplicate": True,
        }
        res = self.client.post(f"/teacher/exams/{system_exam['id']}/assign", json=assign_payload)
        self.assertEqual(res.status_code, 200, res.text)
        assigned_data = res.json()["exam"]

        self.assertNotEqual(assigned_data["id"], system_exam["id"])
        self.assertEqual(assigned_data["scope"], "class")
        self.assertEqual(assigned_data["classroom_id"], self.classroom.id)
        self.assertEqual(assigned_data["assignment_type"], "exam")
        self.assertEqual(len(assigned_data["questions"]), 2)

        # Check original exam is unchanged
        sys_res = self.client.get(f"/teacher/exams/{system_exam['id']}")
        self.assertEqual(sys_res.status_code, 200)
        self.assertEqual(sys_res.json()["scope"], "system")

        # Check filtering by assignment_type=exam in classroom
        cls_exams_res = self.client.get(
            f"/teacher/classes/{self.classroom.id}/exams",
            params={"assignment_type": "exam"},
        )
        self.assertEqual(cls_exams_res.status_code, 200)
        items = cls_exams_res.json()["items"]
        self.assertTrue(any(item["id"] == assigned_data["id"] for item in items))

    def test_assign_exam_as_test_with_duplicate(self):
        system_exam = self._create_system_exam()

        assign_payload = {
            "classroom_id": self.classroom.id,
            "assignment_type": "test",
            "start_time": "2026-08-01T00:00:00Z",
            "end_time": "2026-08-31T23:59:59Z",
            "max_attempts": 1,
            "is_published": True,
            "duplicate": True,
        }
        res = self.client.post(f"/teacher/exams/{system_exam['id']}/assign", json=assign_payload)
        self.assertEqual(res.status_code, 200, res.text)
        assigned_data = res.json()["exam"]

        self.assertEqual(assigned_data["scope"], "class")
        self.assertEqual(assigned_data["classroom_id"], self.classroom.id)
        self.assertEqual(assigned_data["assignment_type"], "test")
        self.assertEqual(assigned_data["max_attempts"], 1)

        # Check filtering by assignment_type=test in classroom
        cls_tests_res = self.client.get(
            f"/teacher/classes/{self.classroom.id}/exams",
            params={"assignment_type": "test"},
        )
        self.assertEqual(cls_tests_res.status_code, 200)
        items = cls_tests_res.json()["items"]
        self.assertTrue(any(item["id"] == assigned_data["id"] for item in items))

    def test_assign_exam_without_duplicate(self):
        system_exam = self._create_system_exam()

        assign_payload = {
            "classroom_id": self.classroom.id,
            "assignment_type": "test",
            "start_time": "2026-08-01T00:00:00Z",
            "end_time": "2026-08-31T23:59:59Z",
            "duplicate": False,
        }
        res = self.client.post(f"/teacher/exams/{system_exam['id']}/assign", json=assign_payload)
        self.assertEqual(res.status_code, 200, res.text)
        assigned_data = res.json()["exam"]

        self.assertEqual(assigned_data["id"], system_exam["id"])
        self.assertEqual(assigned_data["scope"], "class")
        self.assertEqual(assigned_data["classroom_id"], self.classroom.id)
        self.assertEqual(assigned_data["assignment_type"], "test")

