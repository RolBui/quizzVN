# 📑 Đặc tả 7 API cho Trang Tổng quan Học sinh (Student Dashboard)

Tài liệu này tổng hợp đặc tả cấu trúc dữ liệu và phản hồi (Response Payload) cho **7 API** phục vụ tích hợp giao diện **Trang tổng quan học sinh (Student Dashboard)**.

---

## 1. 📖 API Bài học / Bài thi đang dang dở (Thẻ "Tiếp tục học")

- **Mục đích**: Lấy thông tin bài thi hoặc bài học gần nhất mà học sinh chưa hoàn thành để làm tiếp.
- **Request Parameters**: Không có (lấy theo `user_id` từ Token).
- **Response Structure (JSON)**:

```json
{
  "attempt_id": "att-102",
  "exam_id": "exam-45",
  "title": "Phương trình bậc hai và hệ thức Vi-ét",
  "subject_name": "Toán 9",
  "chapter_name": "Chương 3",
  "completed_questions": 12,
  "total_questions": 20,
  "progress_percentage": 60
}
```

---

## 2. 📊 API 4 Chỉ số Thống kê Tổng quan (4 Metric Cards)

- **Mục đích**: Cung cấp dữ liệu tổng hợp 4 ô chỉ số hàng đầu trên Dashboard.
- **Request Parameters**: Không có.
- **Response Structure (JSON)**:

```json
{
  "pending_exams_count": 8,
  "pending_exams_diff": "+2 so với tuần trước",
  "average_score": 7.8,
  "score_diff": "+0.6 điểm",
  "study_time_seconds": 9000,
  "study_time_display": "2h 30m",
  "study_time_diff": "+45m so với tuần trước",
  "streak_days": 5,
  "streak_text": "Ngày liên tiếp"
}
```

---

## 3. 📈 API Biểu đồ Hoạt động học tập 7 ngày (7-day Activity Chart)

- **Mục đích**: Cung cấp dữ liệu thống kê số bài đã làm và số phút học cho 7 ngày gần nhất (Thứ 2 đến Chủ nhật).
- **Request Parameters**: `?start_date=YYYY-MM-DD` (Tùy chọn).
- **Response Structure (JSON)**:

```json
{
  "daily_activities": [
    {
      "day": "Thứ 2",
      "date": "2026-07-27",
      "tests_completed": 4,
      "study_minutes": 25
    },
    {
      "day": "Thứ 3",
      "date": "2026-07-28",
      "tests_completed": 5,
      "study_minutes": 35
    },
    {
      "day": "Thứ 4",
      "date": "2026-07-29",
      "tests_completed": 4,
      "study_minutes": 40
    },
    {
      "day": "Thứ 5",
      "date": "2026-07-30",
      "tests_completed": 3,
      "study_minutes": 45,
      "is_highlight": true
    },
    {
      "day": "Thứ 6",
      "date": "2026-07-31",
      "tests_completed": 4,
      "study_minutes": 20
    },
    {
      "day": "Thứ 7",
      "date": "2026-08-01",
      "tests_completed": 5,
      "study_minutes": 30
    },
    {
      "day": "CN",
      "date": "2026-08-02",
      "tests_completed": 4,
      "study_minutes": 60
    }
  ],
  "comparison_note": "Hôm nay bạn đã làm nhiều hơn 20% so với trung bình tuần."
}
```

---

## 4. 🎯 API Tiến độ theo môn học (Subject Progress)

- **Mục đích**: Cung cấp % tiến độ hoàn thành kiến thức theo từng môn học của học sinh.
- **Request Parameters**: Không có.
- **Response Structure (JSON)**:

```json
[
  { "subject_id": "sub-1", "name": "Toán", "progress": 72, "color": "#8B5CF6" },
  {
    "subject_id": "sub-2",
    "name": "Ngữ văn",
    "progress": 54,
    "color": "#FF5E84"
  },
  {
    "subject_id": "sub-3",
    "name": "Tiếng Anh",
    "progress": 81,
    "color": "#F59E0B"
  },
  {
    "subject_id": "sub-4",
    "name": "Vật lý",
    "progress": 36,
    "color": "#10B981"
  },
  {
    "subject_id": "sub-5",
    "name": "Hóa học",
    "progress": 62,
    "color": "#3B82F6"
  }
]
```

---

## 5. 🏫 API Lớp học của tôi & Tham gia lớp bằng mã

### 5.1. Lấy danh sách lớp đã tham gia

- **Request Parameters**: `?limit=6`
- **Response Structure (JSON)**:

```json
[
  {
    "id": "cls-1",
    "name": "Toán 9A - Cô Lan",
    "academic_year": "Năm học 2024 - 2025",
    "member_count": 18,
    "status": "Đang học"
  },
  {
    "id": "cls-2",
    "name": "Vật lý 9A - Thầy Minh",
    "academic_year": "Năm học 2024 - 2025",
    "member_count": 22,
    "status": "Đang học"
  }
]
```

### 5.2. Tham gia lớp bằng mã

- **Request Body (JSON)**:

```json
{
  "join_code": "GLQ2R6"
}
```

- **Response Structure (JSON)**:

```json
{
  "message": "Tham gia lớp học thành công",
  "class_info": {
    "id": "cls-1",
    "name": "Toán 9A - Cô Lan",
    "member_count": 19,
    "status": "Đang học"
  }
}
```

---

## 6. 📝 API Đề thi đề xuất cho bạn (Recommended Exams)

- **Mục đích**: Gợi ý danh sách đề thi phù hợp nhất với khối lớp và môn học của học sinh.
- **Request Parameters**: `?limit=3`
- **Response Structure (JSON)**:

```json
[
  {
    "id": "exam-101",
    "title": "Đề kiểm tra 15 phút - Đại số 9",
    "subject_name": "Toán 9",
    "question_count": 15,
    "difficulty": "Dễ"
  },
  {
    "id": "exam-102",
    "title": "Đề thi học kỳ I - Toán 9",
    "subject_name": "Toán 9",
    "question_count": 40,
    "difficulty": "Trung bình"
  }
]
```

---

## 7. 🔔 API Nhật ký Hoạt động gần đây (Recent Activities Log)

- **Mục đích**: Trả về 4-5 hoạt động gần nhất của học sinh (nộp bài thi, vào lớp, mở tài liệu, đạt điểm cao).
- **Request Parameters**: `?limit=5`
- **Response Structure (JSON)**:

```json
[
  {
    "id": "act-1",
    "action_type": "exam_submit",
    "title": "Bạn đã làm đề \"Đề kiểm tra 15 phút - Đại số 9\"",
    "time_ago": "5 phút trước",
    "created_at": "2026-07-31T18:35:00Z"
  },
  {
    "id": "act-2",
    "action_type": "class_join",
    "title": "Bạn đã tham gia lớp \"Toán 9A - Cô Lan\"",
    "time_ago": "1 giờ trước",
    "created_at": "2026-07-31T17:40:00Z"
  },
  {
    "id": "act-3",
    "action_type": "document_open",
    "title": "Bạn đã mở tài liệu \"Tóm tắt công thức Hình học\"",
    "time_ago": "Hôm qua",
    "created_at": "2026-07-30T10:15:00Z"
  },
  {
    "id": "act-4",
    "action_type": "score_achieved",
    "title": "Bạn đã đạt 8.5 điểm trong đề \"Đề thi học kỳ I - Toán 9\"",
    "time_ago": "2 ngày trước",
    "created_at": "2026-07-29T14:20:00Z"
  }
]
```
