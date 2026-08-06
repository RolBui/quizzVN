import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import engine
from app.models.notification import Notification
from app.schemas.notification import NotificationSchema

logger = logging.getLogger(__name__)

def bootstrap_notifications_storage() -> None:
    Notification.__table__.create(bind=engine, checkfirst=True)

def format_relative_time(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "Vừa xong"
    minutes = seconds // 60
    if minutes < 60:
        return f"{int(minutes)} phút trước"
    hours = minutes // 60
    if hours < 24:
        return f"{int(hours)} giờ trước"
    days = hours // 24
    if days == 1:
        return "Hôm qua"
    if days < 7:
        return f"{int(days)} ngày trước"
    return dt.strftime("%d/%m/%Y")

def map_to_schema(notif: Notification) -> NotificationSchema:
    return NotificationSchema(
        id=str(notif.id),
        title=notif.title,
        description=notif.description,
        type=notif.type,
        unread=not notif.is_read,
        link_to=notif.link_to,
        time=format_relative_time(notif.created_at)
    )

async def create_notification(
    db: Session,
    user_id: int,
    title: str,
    description: str,
    type: str = "system",
    link_to: str | None = None
) -> Notification:
    notif = Notification(
        user_id=user_id,
        title=title,
        description=description,
        type=type,
        is_read=False,
        link_to=link_to
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Broadcast via WebSocket if user has active connections
    try:
        from app.routers.chat_router import manager
        schema_data = map_to_schema(notif)
        payload = {
            "type": "notification_created",
            "notification": schema_data.model_dump()
        }
        await manager.send_to_user(user_id, payload)
        logger.info("Real-time notification sent to user_id=%s", user_id)
    except Exception as exc:
        logger.error("Failed to broadcast real-time notification: %s", exc)

    return notif

def list_notifications(db: Session, user_id: int) -> list[NotificationSchema]:
    notifs = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return [map_to_schema(n) for n in notifs]

def mark_as_read(db: Session, user_id: int, notif_id: int) -> bool:
    notif = (
        db.query(Notification)
        .filter(Notification.id == notif_id, Notification.user_id == user_id)
        .first()
    )
    if notif:
        notif.is_read = True
        db.commit()
        return True
    return False

def mark_all_as_read(db: Session, user_id: int) -> None:
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()

def delete_notification(db: Session, user_id: int, notif_id: int) -> bool:
    notif = (
        db.query(Notification)
        .filter(Notification.id == notif_id, Notification.user_id == user_id)
        .first()
    )
    if notif:
        db.delete(notif)
        db.commit()
        return True
    return False

def delete_all_notifications(db: Session, user_id: int) -> None:
    db.query(Notification).filter(Notification.user_id == user_id).delete(synchronize_session=False)
    db.commit()


def run_coroutine_sync(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        loop.create_task(coro)
    else:
        loop.run_until_complete(coro)


def trigger_assignment_notification_sync(db: Session, exam_id: int, teacher_id: int):
    from app.models.exam import Exam
    from app.models.classroom import Classroom
    from app.models.classroom_membership import ClassroomMembership
    from app.models.user import User

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam or not exam.classroom_id:
        return

    classroom = db.query(Classroom).filter(Classroom.id == exam.classroom_id).first()
    if not classroom:
        return

    teacher = db.query(User).filter(User.id == teacher_id).first()
    teacher_name = teacher.full_name if teacher else "Giáo viên"

    members = db.query(ClassroomMembership).filter(ClassroomMembership.classroom_id == exam.classroom_id).all()

    for member in members:
        # Avoid duplicate assignment notifications
        link_to = f"/student/classes/{classroom.id}"
        title = "Đề thi mới được giao"
        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == member.user_id,
                Notification.link_to == link_to,
                Notification.title == title
            )
            .first()
        )
        if existing:
            continue

        description = f"Thầy/Cô {teacher_name} đã giao đề thi mới '{exam.title}' cho lớp '{classroom.name}'."
        coro = create_notification(db, member.user_id, title, description, "assignment", link_to)
        run_coroutine_sync(coro)

