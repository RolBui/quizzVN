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
from app.dependencies.auth import get_current_admin
from app.main import app
from app.models.classroom import Classroom
from app.models.exam_attempt import ExamAttempt
from app.models.role import Role
from app.models.user import User
from app.services.exam_cover_service import DEFAULT_EXAM_COVER_FILENAMES

for module in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{module.name}")


def _is_default_exam_cover_url(value: str | None) -> bool:
    return bool(value) and any(
        value.endswith(f"/assets/{filename}") for filename in DEFAULT_EXAM_COVER_FILENAMES
    )


class AdminExamTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(bind=self.engine)
        self.db = self.TestingSessionLocal()

        admin_role = Role(name="admin")
        self.db.add(admin_role)
        self.db.flush()

        self.admin = User(
            role_id=admin_role.id,
            full_name="Quản Trị Viên A",
            username="admin_a",
            email="admin_a@example.com",
            status="active",
        )
        self.db.add(self.admin)
        self.db.commit()

        self.classroom = Classroom(
            name="Lớp 12A1",
            description="Lớp toán 12A1",
            join_code="CLASS12A1",
            created_by_user_id=self.admin.id,
        )
        self.db.add(self.classroom)
        self.db.commit()

        def _get_test_db():
            try:
                yield self.db
            finally:
                pass

        def _get_test_admin():
            return self.admin

        app.dependency_overrides[get_db] = _get_test_db
        app.dependency_overrides[get_current_admin] = _get_test_admin
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_admin_exam_crud_and_lifecycle(self):
        # 1. Create system exam
        payload = {
            "title": "Đề thi thử THPT Quốc Gia",
            "description": "Đề thi mẫu môn Toán",
            "grade": "Lớp 12",
            "duration_minutes": 90,
            "is_published": False,
            "is_active": True,
            "total_points": 10.0,
            "point_mode": "auto",
            "assignment_type": "exam",
            "max_attempts": 2,
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
                    "options": [],
                    "accepted_answers": ["Hà Nội", "Hanoi"],
                },
            ],
        }

        resp = self.client.post("/admin/exams", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        exam_id = data["exam"]["id"]
        self.assertEqual(data["exam"]["title"], "Đề thi thử THPT Quốc Gia")
        self.assertEqual(data["exam"]["assignment_type"], "exam")
        self.assertEqual(data["exam"]["max_attempts"], 2)
        self.assertTrue(_is_default_exam_cover_url(data["exam"]["image_url"]))

        # 2. Get detail
        resp = self.client.get(f"/admin/exams/{exam_id}")
        self.assertEqual(resp.status_code, 200)
        detail_data = resp.json()
        self.assertEqual(len(detail_data["questions"]), 2)
        self.assertEqual(detail_data["image_url"], data["exam"]["image_url"])

        resp = self.client.get("/admin/exams")
        self.assertEqual(resp.status_code, 200)
        overview_exam = next(item for item in resp.json()["items"] if item["id"] == exam_id)
        self.assertEqual(overview_exam["image_url"], data["exam"]["image_url"])

        # 3. Update exam
        update_payload = {
            "title": "Đề thi thử THPT Quốc Gia (Cập nhật)",
            "max_attempts": 5,
        }
        resp = self.client.put(f"/admin/exams/{exam_id}", json=update_payload)
        self.assertEqual(resp.status_code, 200)
        update_data = resp.json()
        self.assertEqual(update_data["exam"]["title"], "Đề thi thử THPT Quốc Gia (Cập nhật)")
        self.assertEqual(update_data["exam"]["max_attempts"], 5)

        # 4. Publish exam
        resp = self.client.post(f"/admin/exams/{exam_id}/publish")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["exam"]["is_published"])

        # 5. Private exam
        resp = self.client.post(f"/admin/exams/{exam_id}/private")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["exam"]["is_published"])

        # 6. Assign exam to class
        assign_payload = {
            "classroom_id": self.classroom.id,
            "assignment_type": "exam",
            "duplicate": True,
        }
        resp = self.client.post(f"/admin/exams/{exam_id}/assign", json=assign_payload)
        self.assertEqual(resp.status_code, 200)
        assign_data = resp.json()
        self.assertEqual(assign_data["exam"]["classroom_id"], self.classroom.id)
        self.assertEqual(assign_data["exam"]["assignment_type"], "exam")
        self.assertEqual(assign_data["exam"]["scope"], "class")
        self.assertTrue(_is_default_exam_cover_url(assign_data["exam"]["image_url"]))


    def test_update_exam_metadata_after_attempt_started_without_replacing_questions(self):
        payload = {
            "title": "Đề đã có lượt làm",
            "description": "Đề kiểm tra update metadata",
            "grade": "Lớp 12",
            "duration_minutes": 45,
            "is_published": True,
            "is_active": True,
            "questions": [
                {
                    "question_type": "single_choice",
                    "prompt": "1 + 1 bằng bao nhiêu?",
                    "explanation": "1 + 1 = 2",
                    "order_index": 1,
                    "points": 10.0,
                    "options": [
                        {"option_key": "A", "option_text": "2", "is_correct": True},
                        {"option_key": "B", "option_text": "3", "is_correct": False},
                    ],
                }
            ],
        }
        resp = self.client.post("/admin/exams", json=payload)
        self.assertEqual(resp.status_code, 200)
        exam_id = resp.json()["exam"]["id"]

        self.db.add(
            ExamAttempt(
                exam_id=exam_id,
                user_id=self.admin.id,
                status="in_progress",
                total_points=10.0,
            )
        )
        self.db.commit()

        resp = self.client.put(
            f"/admin/exams/{exam_id}",
            json={"title": "Đề đã cập nhật metadata", "duration_minutes": 60},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["exam"]
        self.assertEqual(data["title"], "Đề đã cập nhật metadata")
        self.assertEqual(data["duration_minutes"], 60)
        self.assertEqual(len(data["questions"]), 1)

        resp = self.client.put(
            f"/admin/exams/{exam_id}",
            json={
                "questions": [
                    {
                        "question_type": "single_choice",
                        "prompt": "2 + 2 bằng bao nhiêu?",
                        "explanation": "2 + 2 = 4",
                        "order_index": 1,
                        "points": 10.0,
                        "options": [
                            {"option_key": "A", "option_text": "4", "is_correct": True},
                            {"option_key": "B", "option_text": "5", "is_correct": False},
                        ],
                    }
                ]
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["detail"],
            "Cannot replace questions after students have started attempts",
        )
if __name__ == "__main__":
    unittest.main()
