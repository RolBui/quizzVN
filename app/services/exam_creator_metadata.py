from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.ai_exam import AIExamGenerationJob
from app.models.user import User

CREATOR_TYPE_SYSTEM = "system"
CREATOR_TYPE_TEACHER = "teacher"
CREATOR_TYPE_ADMIN = "administrator"

SOURCE_SYSTEM = "system"
SOURCE_TEACHER = "teacher"

SOURCE_LABELS = {
    SOURCE_SYSTEM: "Hệ thống tạo",
    SOURCE_TEACHER: "Giáo viên tạo",
}


def get_ai_generated_exam_ids(db: Session, exam_ids: Iterable[int | None]) -> set[int]:
    normalized_ids = {int(exam_id) for exam_id in exam_ids if exam_id is not None}
    if not normalized_ids:
        return set()

    rows = (
        db.query(AIExamGenerationJob.quiz_id)
        .filter(AIExamGenerationJob.quiz_id.in_(normalized_ids))
        .all()
    )
    return {int(row.quiz_id) for row in rows if row.quiz_id is not None}


def build_exam_creator_metadata(
    creator: User | None = None,
    *,
    creator_id: int | None = None,
    creator_name: str | None = None,
    creator_role_name: str | None = None,
    is_ai_generated: bool = False,
) -> dict:
    if creator is not None:
        creator_id = creator.id
        creator_name = creator.full_name
        creator_role_name = creator.role.name if creator.role else creator_role_name

    normalized_role = (creator_role_name or "").strip().lower()
    if creator_id is None:
        creator_type = CREATOR_TYPE_SYSTEM
        resolved_creator_name = "Hệ thống"
    elif normalized_role in {"admin", "administrator"}:
        creator_type = CREATOR_TYPE_ADMIN
        resolved_creator_name = creator_name or "Administrator"
    else:
        creator_type = CREATOR_TYPE_TEACHER
        resolved_creator_name = creator_name or "Giáo viên"

    source = (
        SOURCE_TEACHER
        if creator_type == CREATOR_TYPE_TEACHER and not is_ai_generated
        else SOURCE_SYSTEM
    )
    return {
        "creator_id": creator_id,
        "creator_name": resolved_creator_name,
        "creator_type": creator_type,
        "source": source,
        "source_label": SOURCE_LABELS[source],
        "is_ai_generated": is_ai_generated,
    }
