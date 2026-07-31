import importlib
import pkgutil
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models as models_pkg
from app.database import Base, get_db
from app.dependencies.auth import get_current_student
from app.main import app
from app.models.classroom import Classroom
from app.models.classroom_membership import ClassroomMembership
from app.models.exam import Exam
from app.models.exam_attempt import ExamAttempt
from app.models.role import Role
from app.models.user import User

for module in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{module.name}")


class StudentDashboardApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(bind=self.engine)
        self.db = self.TestingSessionLocal()

        # Create role & student user
        student_role = Role(name="student")
        self.db.add(student_role)
        self.db.flush()

        self.student = User(
            role_id=student_role.id,
            full_name="Nguyễn Văn A",
            username="student_a",
            email="student_a@example.com",
            status="active",
        )
        self.db.add(self.student)
        self.db.commit()
        self.db.refresh(self.student)

        # Create dummy classroom and exam
        self.classroom = Classroom(
            name="Toán 9A - Cô Lan",
            description="Lớp toán 9",
            join_code="GLQ2R6",
            created_by_user_id=self.student.id,
        )
        self.db.add(self.classroom)
        self.db.commit()

        membership = ClassroomMembership(
            classroom_id=self.classroom.id,
            user_id=self.student.id,
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(membership)

        self.exam = Exam(
            title="Phương trình bậc hai và hệ thức Vi-ét",
            description="Đề thi thử toán",
            grade="Toán 9",
            scope="system",
            duration_minutes=45,
            is_published=True,
            is_active=True,
        )
        self.db.add(self.exam)
        self.db.commit()

        # Override dependencies
        def _get_test_db():
            try:
                yield self.db
            finally:
                pass

        def _get_test_student():
            return self.student

        app.dependency_overrides[get_db] = _get_test_db
        app.dependency_overrides[get_current_student] = _get_test_student
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_get_dashboard_in_progress_none(self):
        res = self.client.get("/student/dashboard/in-progress")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json())

    def test_get_dashboard_in_progress_existing(self):
        attempt = ExamAttempt(
            exam_id=self.exam.id,
            user_id=self.student.id,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(attempt)
        self.db.commit()

        res = self.client.get("/student/dashboard/in-progress")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNotNone(data)
        self.assertEqual(data["title"], "Phương trình bậc hai và hệ thức Vi-ét")
        self.assertEqual(data["subject_name"], "Toán 9")

    def test_get_dashboard_metrics(self):
        res = self.client.get("/student/dashboard/metrics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("pending_exams_count", data)
        self.assertIn("average_score", data)
        self.assertIn("study_time_seconds", data)
        self.assertIn("streak_days", data)

    def test_get_dashboard_activity_chart(self):
        res = self.client.get("/student/dashboard/activity-chart")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("daily_activities", data)
        self.assertEqual(len(data["daily_activities"]), 7)

    def test_get_dashboard_subject_progress(self):
        res = self.client.get("/student/dashboard/subject-progress")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertIn("subject_id", data[0])
        self.assertIn("progress", data[0])

    def test_get_dashboard_classes(self):
        res = self.client.get("/student/dashboard/classes?limit=6")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Toán 9A - Cô Lan")

    def test_post_join_class(self):
        res = self.client.post("/student/classes/join", json={"join_code": "GLQ2R6"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("class_info", data)
        self.assertEqual(data["class_info"]["name"], "Toán 9A - Cô Lan")

    def test_get_dashboard_recommended_exams(self):
        res = self.client.get("/student/dashboard/recommended-exams?limit=3")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertEqual(data[0]["title"], "Phương trình bậc hai và hệ thức Vi-ét")

    def test_get_dashboard_recent_activities(self):
        res = self.client.get("/student/dashboard/recent-activities?limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
