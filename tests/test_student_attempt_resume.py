import importlib
import pkgutil
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models as models_pkg
from app.database import Base, get_db
from app.dependencies.auth import get_current_student
from app.main import app
from app.models.exam import Exam
from app.models.exam_attempt import ExamAttempt
from app.models.exam_attempt_answer import ExamAttemptAnswer
from app.models.exam_question import ExamQuestion
from app.models.exam_question_option import ExamQuestionOption
from app.models.role import Role
from app.models.user import User

for module in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{module.name}")


class StudentAttemptResumeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        student_role = Role(name="student")
        self.db.add(student_role)
        self.db.flush()

        self.student = User(
            role_id=student_role.id,
            full_name="Student Resume",
            username="student_resume",
            email="student-resume@example.com",
            status="active",
        )
        self.db.add(self.student)
        self.db.flush()

        self.exam = Exam(
            title="Resume capable exam",
            description="Autosave test",
            grade="Math",
            scope="system",
            duration_minutes=45,
            is_published=True,
            is_active=True,
            assignment_type="exam",
            total_points=1,
        )
        self.db.add(self.exam)
        self.db.flush()

        self.question = ExamQuestion(
            exam_id=self.exam.id,
            question_type="single_choice",
            prompt="1 + 1 = ?",
            explanation="",
            order_index=1,
            points=1,
        )
        self.db.add(self.question)
        self.db.flush()

        self.correct_option = ExamQuestionOption(
            question_id=self.question.id,
            option_key="A",
            option_text="2",
            is_correct=True,
        )
        self.wrong_option = ExamQuestionOption(
            question_id=self.question.id,
            option_key="B",
            option_text="3",
            is_correct=False,
        )
        self.db.add_all([self.correct_option, self.wrong_option])
        self.db.commit()

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

    def test_autosaved_answer_can_resume_from_another_device(self):
        start_response = self.client.post(f"/student/exams/{self.exam.id}/attempts")
        self.assertEqual(start_response.status_code, 200)
        start_data = start_response.json()["attempt"]
        attempt_id = start_data["id"]
        self.assertEqual(start_data["answers"], [])
        self.assertEqual(start_data["exam"]["id"], self.exam.id)
        self.assertIsNotNone(start_data["expires_at"])
        self.assertGreater(start_data["remaining_seconds"], 0)

        save_response = self.client.put(
            f"/student/attempts/{attempt_id}/answers",
            json={
                "answers": [
                    {
                        "question_id": self.question.id,
                        "selected_option_id": self.correct_option.id,
                    }
                ]
            },
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertIsNotNone(save_response.json()["saved_at"])

        resume_response = self.client.get(f"/student/attempts/{attempt_id}")
        self.assertEqual(resume_response.status_code, 200)
        resume_attempt = resume_response.json()["attempt"]
        self.assertEqual(resume_attempt["status"], "in_progress")
        self.assertEqual(resume_attempt["answered_count"], 1)
        self.assertEqual(resume_attempt["answers"][0]["question_id"], self.question.id)
        self.assertEqual(resume_attempt["answers"][0]["selected_option_id"], self.correct_option.id)

        active_response = self.client.get(f"/student/exams/{self.exam.id}/attempts/active")
        self.assertEqual(active_response.status_code, 200)
        active_attempt = active_response.json()["attempt"]
        self.assertEqual(active_attempt["id"], attempt_id)
        self.assertEqual(active_attempt["answers"][0]["selected_option_id"], self.correct_option.id)

    def test_resume_auto_submits_expired_attempt(self):
        attempt = ExamAttempt(
            exam_id=self.exam.id,
            user_id=self.student.id,
            status="in_progress",
            total_points=1,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=60),
        )
        self.db.add(attempt)
        self.db.flush()
        self.db.add(
            ExamAttemptAnswer(
                attempt_id=attempt.id,
                question_id=self.question.id,
                selected_option_id=self.correct_option.id,
                answer_text=None,
                answered_at=datetime.now(timezone.utc) - timedelta(minutes=59),
            )
        )
        self.db.commit()

        response = self.client.get(f"/student/attempts/{attempt.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()["attempt"]
        self.assertEqual(data["status"], "submitted")
        self.assertEqual(data["score"], 1.0)
        self.assertEqual(data["remaining_seconds"], 0)


if __name__ == "__main__":
    unittest.main()