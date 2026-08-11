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
from app.models.learning_document import LearningDocument
from app.models.role import Role
from app.models.user import User
from app.services.exam_cover_service import DEFAULT_EXAM_COVER_FILENAMES

for module in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{module.name}")


def _is_default_exam_cover_url(value: str | None) -> bool:
    return bool(value) and any(
        value.endswith(f"/assets/{filename}") for filename in DEFAULT_EXAM_COVER_FILENAMES
    )


class StudentExamDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.TestingSessionLocal = sessionmaker(bind=self.engine)
        self.db = self.TestingSessionLocal()

        # Setup student role and user
        student_role = Role(name="student")
        self.db.add(student_role)
        self.db.flush()

        self.student = User(
            role_id=student_role.id,
            full_name="Học Sinh Test",
            username="student_test",
            email="student_test@example.com",
            status="active",
        )
        self.db.add(self.student)
        self.db.commit()

        # Classrooms
        self.joined_class = Classroom(
            name="Lớp Toán 12A1",
            join_code="MATH12A1",
            created_by_user_id=1,
        )
        self.other_class = Classroom(
            name="Lớp Lý 12A2",
            join_code="PHYS12A2",
            created_by_user_id=1,
        )
        self.db.add(self.joined_class)
        self.db.add(self.other_class)
        self.db.commit()

        # Membership for joined class
        membership = ClassroomMembership(
            classroom_id=self.joined_class.id,
            user_id=self.student.id,
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(membership)
        self.db.commit()

        # Exams setup
        # 1. System published exam (visible)
        self.exam_sys_pub = Exam(
            title="Đề thi thử THPT Toán 2026",
            description="Đề luyện thi môn Toán cho lớp 12",
            grade="Lớp 12",
            scope="system",
            duration_minutes=90,
            is_published=True,
            is_active=True,
            assignment_type="exam",
        )
        # 2. System published test (visible)
        self.exam_sys_test = Exam(
            title="Bài kiểm tra 15 phút Anh Văn",
            description="Luyện từ vựng tiếng Anh",
            grade="Lớp 10",
            scope="system",
            duration_minutes=15,
            is_published=True,
            is_active=True,
            assignment_type="test",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        # 3. System unpublished exam (invisible)
        self.exam_sys_unpub = Exam(
            title="Đề ôn tập Hóa Học nháp",
            description="Chưa công khai",
            grade="Lớp 12",
            scope="system",
            duration_minutes=45,
            is_published=False,
            is_active=True,
            assignment_type="exam",
        )
        # 4. Class exam (explore endpoint only returns system scope for discovery)
        self.exam_class = Exam(
            title="Đề kiểm tra 1 tiết Toán 12A1",
            scope="class",
            classroom_id=self.joined_class.id,
            duration_minutes=45,
            is_published=True,
            is_active=True,
            assignment_type="test",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )

        self.db.add_all([self.exam_sys_pub, self.exam_sys_test, self.exam_sys_unpub, self.exam_class])
        self.db.commit()

        # Learning Documents setup
        # 1. System Document
        self.doc_sys = LearningDocument(
            title="Tài liệu tự học Đại Số 12",
            summary="Các bài toán giải phương trình",
            content="Nội dung tự học...",
            scope="system",
            is_published=True,
        )
        # 2. Joined Class Document
        self.doc_class_joined = LearningDocument(
            title="Đề cương ôn tập Toán 12A1",
            summary="Đề cương học kỳ 1",
            content="Nội dung đề cương...",
            scope="class",
            classroom_id=self.joined_class.id,
            is_published=True,
        )
        # 3. Other Class Document (invisible)
        self.doc_class_other = LearningDocument(
            title="Tài liệu Vật Lý 12A2",
            summary="Bài tập điện xoay chiều",
            content="Nội dung điện...",
            scope="class",
            classroom_id=self.other_class.id,
            is_published=True,
        )

        self.db.add_all([self.doc_sys, self.doc_class_joined, self.doc_class_other])
        self.db.commit()

        # Setup test client dependencies
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

    def test_explore_exams_all(self):
        # 1. Explore all public exams without filters
        resp = self.client.get("/student/exams/explore")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 2)  # Should return self.exam_sys_pub and self.exam_sys_test
        items = data["items"]
        titles = [x["title"] for x in items]
        self.assertIn("Đề thi thử THPT Toán 2026", titles)
        self.assertIn("Bài kiểm tra 15 phút Anh Văn", titles)
        self.assertNotIn("Đề ôn tập Hóa Học nháp", titles)
        self.assertNotIn("Đề kiểm tra 1 tiết Toán 12A1", titles)
        self.assertTrue(all(_is_default_exam_cover_url(item["image_url"]) for item in items))

    def test_explore_exams_with_filters(self):
        # 2. Filter by search query
        resp = self.client.get("/student/exams/explore", params={"search": "THPT"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["title"], "Đề thi thử THPT Toán 2026")

        # 3. Filter by grade
        resp = self.client.get("/student/exams/explore", params={"grade": "Lớp 10"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["title"], "Bài kiểm tra 15 phút Anh Văn")

        # 4. Filter by assignment_type
        resp = self.client.get("/student/exams/explore", params={"assignment_type": "test"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["title"], "Bài kiểm tra 15 phút Anh Văn")

    def test_get_student_documents_all(self):
        # 1. Get all documents (system + joined class documents)
        resp = self.client.get("/student/documents")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data["items"]
        self.assertEqual(len(items), 2)  # doc_sys and doc_class_joined
        titles = [x["title"] for x in items]
        self.assertIn("Tài liệu tự học Đại Số 12", titles)
        self.assertIn("Đề cương ôn tập Toán 12A1", titles)
        self.assertNotIn("Tài liệu Vật Lý 12A2", titles)

    def test_get_student_documents_filtered_by_class(self):
        # 2. Get documents filtered by classroom_id
        resp = self.client.get("/student/documents", params={"classroom_id": self.joined_class.id})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Đề cương ôn tập Toán 12A1")

        # 3. Requesting documents for other classroom should return 403 Forbidden
        resp = self.client.get("/student/documents", params={"classroom_id": self.other_class.id})
        self.assertEqual(resp.status_code, 403)

    def test_get_student_documents_search(self):
        # 4. Search document by keyword
        resp = self.client.get("/student/documents", params={"search": "Đại Số"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Tài liệu tự học Đại Số 12")
