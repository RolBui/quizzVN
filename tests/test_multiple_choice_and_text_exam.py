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
from app.dependencies.auth import get_current_student, get_current_teacher
from app.main import app
from app.models.role import Role
from app.models.user import User

for module in pkgutil.iter_modules(models_pkg.__path__):
    importlib.import_module(f"app.models.{module.name}")


class MultipleChoiceAndTextExamTests(unittest.TestCase):
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
        student_role = Role(name="student")
        self.db.add(teacher_role)
        self.db.add(student_role)
        self.db.flush()

        self.teacher = User(
            role_id=teacher_role.id,
            full_name="Giáo Viên A",
            username="teacher_a",
            email="teacher_a@example.com",
            status="active",
        )
        self.student = User(
            role_id=student_role.id,
            full_name="Học Sinh B",
            username="student_b",
            email="student_b@example.com",
            status="active",
        )
        self.db.add(self.teacher)
        self.db.add(self.student)
        self.db.commit()

        def _get_test_db():
            try:
                yield self.db
            finally:
                pass

        def _get_test_teacher():
            return self.teacher

        def _get_test_student():
            return self.student

        app.dependency_overrides[get_db] = _get_test_db
        app.dependency_overrides[get_current_teacher] = _get_test_teacher
        app.dependency_overrides[get_current_student] = _get_test_student
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_create_system_exam_with_all_4_question_types(self):
        payload = {
            "title": "Đề thi Soạn văn bản Ôn tập Tiếng Anh",
            "description": "Đề thi kiểm thử 4 dạng câu hỏi",
            "grade": "Tiếng Anh 9",
            "duration_minutes": 45,
            "is_published": True,
            "is_active": True,
            "questions": [
                # 1. Single choice (Dạng 1 đáp án)
                {
                    "prompt": "When we went back to the bookstore, the bookseller _ the book we wanted.",
                    "question_type": "single_choice",
                    "points": 10,
                    "order_index": 1,
                    "options": [
                        {"option_key": "A", "option_text": "sold", "is_correct": False},
                        {"option_key": "B", "option_text": "had sold", "is_correct": True},
                        {"option_key": "C", "option_text": "sells", "is_correct": False},
                        {"option_key": "D", "option_text": "has sold", "is_correct": False},
                    ],
                },
                # 2. Multiple choice (Dạng nhiều đáp án)
                {
                    "prompt": "She speaks English as _ as I do.",
                    "question_type": "multiple_choice",
                    "points": 10,
                    "order_index": 2,
                    "options": [
                        {"option_key": "A", "option_text": "good", "is_correct": False},
                        {"option_key": "B", "option_text": "fluently", "is_correct": True},
                        {"option_key": "C", "option_text": "very good", "is_correct": False},
                        {"option_key": "D", "option_text": "well", "is_correct": True},
                    ],
                },
                # 3. Fill in blank (Dạng điền từ)
                {
                    "prompt": "[FILL] Background, in relation to computers...",
                    "question_type": "fill_in_blank",
                    "points": 10,
                    "order_index": 3,
                    "accepted_answers": ["For example", "for example"],
                },
                # 4. Reading comprehension (Dạng đọc hiểu)
                {
                    "prompt": "[READ-5] Read the following passage...<br/>We get great pleasure from reading...",
                    "question_type": "single_choice",
                    "points": 10,
                    "order_index": 4,
                    "options": [
                        {"option_key": "A", "option_text": "pleasure", "is_correct": True},
                        {"option_key": "B", "option_text": "pain", "is_correct": False},
                    ],
                },
                # 5. Short answer (Dạng câu trả lời ngắn)
                {
                    "prompt": "Thủ đô của Việt Nam là gì?",
                    "question_type": "short_answer",
                    "points": 10,
                    "order_index": 5,
                    "accepted_answers": ["Hà Nội", "Ha Noi"],
                },
            ],
        }

        res = self.client.post("/teacher/system/exams", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["exam"]["title"], "Đề thi Soạn văn bản Ôn tập Tiếng Anh")
        self.assertEqual(len(data["exam"]["questions"]), 5)

        exam_id = data["exam"]["id"]

        # Student starts attempt
        res_start = self.client.post(f"/student/exams/{exam_id}/attempts")
        self.assertEqual(res_start.status_code, 200)
        attempt_id = res_start.json()["attempt"]["id"]

        q1 = data["exam"]["questions"][0]
        q2 = data["exam"]["questions"][1]
        q3 = data["exam"]["questions"][2]
        q4 = data["exam"]["questions"][3]
        q5 = data["exam"]["questions"][4]

        self.assertEqual(q3["question_type"], "fill_in_blank")
        self.assertEqual(q5["question_type"], "short_answer")

        q1_correct_opt = [o["id"] for o in q1["options"] if o["is_correct"]][0]
        q2_correct_opts = [o["id"] for o in q2["options"] if o["is_correct"]]
        q4_correct_opt = [o["id"] for o in q4["options"] if o["is_correct"]][0]

        # Student saves answers
        save_payload = {
            "answers": [
                # Q1: Single choice
                {"question_id": q1["id"], "selected_option_id": q1_correct_opt},
                # Q2: Multiple choice (Student selects both correct options: fluently, well)
                {"question_id": q2["id"], "selected_option_ids": q2_correct_opts},
                # Q3: Fill-in blank
                {"question_id": q3["id"], "answer_text": "For example"},
                # Q4: Reading comp single choice
                {"question_id": q4["id"], "selected_option_id": q4_correct_opt},
                # Q5: Short answer
                {"question_id": q5["id"], "answer_text": "Hà Nội"},
            ]
        }

        res_save = self.client.put(f"/student/attempts/{attempt_id}/answers", json=save_payload)
        self.assertEqual(res_save.status_code, 200)

        # Student submits attempt
        res_submit = self.client.post(f"/student/attempts/{attempt_id}/submit")
        self.assertEqual(res_submit.status_code, 200)
        result_data = res_submit.json()["result"]

        self.assertEqual(result_data["score"], 50.0)
        self.assertEqual(result_data["correct_answers_count"], 5)


if __name__ == "__main__":
    unittest.main()
