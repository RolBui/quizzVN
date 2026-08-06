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
from app.dependencies.auth import get_current_teacher
from app.main import app
from app.models.classroom import Classroom
from app.models.exam import Exam
from app.models.role import Role
from app.models.user import User

for module in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{module.name}")


class TeacherExamDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(bind=self.engine)
        self.db = self.TestingSessionLocal()

        # Setup teacher role and users
        teacher_role = Role(name="teacher")
        self.db.add(teacher_role)
        self.db.flush()

        # Currently logged in teacher
        self.teacher_a = User(
            role_id=teacher_role.id,
            full_name="Giáo Viên A",
            username="teacher_a",
            email="teacher_a@example.com",
            status="active",
        )
        # Another teacher
        self.teacher_b = User(
            role_id=teacher_role.id,
            full_name="Giáo Viên B",
            username="teacher_b",
            email="teacher_b@example.com",
            status="active",
        )
        self.db.add_all([self.teacher_a, self.teacher_b])
        self.db.commit()

        # Exams setup
        # 1. Published system exam created by teacher_a
        self.exam_a_pub = Exam(
            title="Đề thi thử Toán A",
            description="Đề do A tạo",
            grade="Lớp 12",
            scope="system",
            duration_minutes=90,
            is_published=True,
            is_active=True,
            assignment_type="exam",
            created_by_user_id=self.teacher_a.id,
        )
        # 2. Published system exam created by teacher_b (should be visible to teacher_a)
        self.exam_b_pub = Exam(
            title="Đề thi thử Toán B",
            description="Đề do B tạo",
            grade="Lớp 12",
            scope="system",
            duration_minutes=90,
            is_published=True,
            is_active=True,
            assignment_type="exam",
            created_by_user_id=self.teacher_b.id,
        )
        # 3. Unpublished system exam created by teacher_b (invisible)
        self.exam_b_unpub = Exam(
            title="Đề Toán nháp B",
            description="Chưa công khai",
            grade="Lớp 12",
            scope="system",
            duration_minutes=45,
            is_published=False,
            is_active=True,
            assignment_type="exam",
            created_by_user_id=self.teacher_b.id,
        )
        # 4. Class exam created by teacher_b (invisible)
        self.exam_b_class = Exam(
            title="Đề lớp học B",
            description="Lớp toán",
            grade="Lớp 12",
            scope="class",
            duration_minutes=45,
            is_published=True,
            is_active=True,
            assignment_type="exam",
            created_by_user_id=self.teacher_b.id,
        )

        self.db.add_all([self.exam_a_pub, self.exam_b_pub, self.exam_b_unpub, self.exam_b_class])
        self.db.commit()

        # Setup test client dependencies
        def _get_test_db():
            try:
                yield self.db
            finally:
                pass

        def _get_test_teacher():
            return self.teacher_a

        app.dependency_overrides[get_db] = _get_test_db
        app.dependency_overrides[get_current_teacher] = _get_test_teacher
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_explore_exams_all_for_teacher(self):
        resp = self.client.get("/teacher/exams/explore")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 2)  # Should return exam_a_pub and exam_b_pub
        items = data["items"]
        titles = [x["title"] for x in items]
        self.assertIn("Đề thi thử Toán A", titles)
        self.assertIn("Đề thi thử Toán B", titles)
        self.assertNotIn("Đề Toán nháp B", titles)
        self.assertNotIn("Đề lớp học B", titles)

    def test_explore_exams_filtered_for_teacher(self):
        # Filter by search
        resp = self.client.get("/teacher/exams/explore", params={"search": "Toán B"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["title"], "Đề thi thử Toán B")


if __name__ == "__main__":
    unittest.main()
