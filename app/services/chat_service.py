from datetime import timedelta

from sqlalchemy import and_, func, inspect, or_, text
from sqlalchemy.orm import Session, aliased, joinedload

from fastapi import HTTPException, UploadFile, status

from app.core.security import utc_now
from app.database import engine
from app.models.chat import ChatConversation, ChatMessage, ChatParticipant
from app.models.role import Role
from app.models.user import User
from app.models.user_session import UserSession
from app.services.auth_service import (
    ADMINISTRATOR_ROLE_NAME,
    ADMIN_ROLE_NAME,
    normalize_admin_permissions,
)
from app.services.media_service import upload_chat_file


CHAT_MESSAGE_ATTACHMENT_COLUMNS = {
    "attachment_url": "VARCHAR",
    "attachment_filename": "VARCHAR",
    "attachment_content_type": "VARCHAR",
    "attachment_size_bytes": "INTEGER",
}
USER_ACTIVITY_WINDOW = timedelta(hours=1)


def _ensure_chat_message_attachment_columns() -> None:
    inspector = inspect(engine)
    existing_columns = {
        column["name"]
        for column in inspector.get_columns(ChatMessage.__tablename__)
    }
    missing_columns = [
        (name, column_type)
        for name, column_type in CHAT_MESSAGE_ATTACHMENT_COLUMNS.items()
        if name not in existing_columns
    ]
    if not missing_columns:
        return

    with engine.begin() as connection:
        for name, column_type in missing_columns:
            connection.execute(
                text(f"ALTER TABLE {ChatMessage.__tablename__} ADD COLUMN {name} {column_type}")
            )


def bootstrap_chat_storage() -> None:
    ChatConversation.__table__.create(bind=engine, checkfirst=True)
    ChatMessage.__table__.create(bind=engine, checkfirst=True)
    ChatParticipant.__table__.create(bind=engine, checkfirst=True)
    _ensure_chat_message_attachment_columns()


def _active_session_user_ids(db: Session) -> set[int]:
    active_after = utc_now() - USER_ACTIVITY_WINDOW
    return {
        user_id
        for (user_id,) in db.query(UserSession.user_id)
        .filter(
            UserSession.is_revoked.is_(False),
            func.coalesce(UserSession.last_used_at, UserSession.created_at) >= active_after,
        )
        .all()
    }


def _serialize_user(user: User, online_user_ids: set[int] | None = None) -> dict:
    profile = user.profile
    role = user.role
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "role_name": role.name if role else None,
        "school_name": profile.school_name if profile else None,
        "is_online": bool(online_user_ids and user.id in online_user_ids),
    }



def _role_name(user: User) -> str | None:
    return user.role.name if user.role else None


def _admin_visible_contact_role_names(current_user: User) -> set[str] | None:
    role_name = _role_name(current_user)
    if role_name == ADMINISTRATOR_ROLE_NAME:
        return None
    if role_name != ADMIN_ROLE_NAME:
        return None

    permissions = set(normalize_admin_permissions(current_user.admin_permissions))
    visible_role_names = {ADMINISTRATOR_ROLE_NAME}
    if "admins" in permissions:
        visible_role_names.add(ADMIN_ROLE_NAME)
    if "teachers" in permissions:
        visible_role_names.add("teacher")
    if "students" in permissions:
        visible_role_names.add("student")
    return visible_role_names


def _apply_contact_scope(users_query, current_user: User):
    visible_role_names = _admin_visible_contact_role_names(current_user)
    if visible_role_names is None:
        return users_query
    return users_query.filter(User.role.has(Role.name.in_(visible_role_names)))


def _can_start_direct_conversation(current_user: User, participant_user: User) -> bool:
    visible_role_names = _admin_visible_contact_role_names(current_user)
    if visible_role_names is None:
        return True
    return _role_name(participant_user) in visible_role_names


def _serialize_message(message: ChatMessage, current_user_id: int) -> dict:
    sender = message.sender
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_id": message.sender_id,
        "sender_name": sender.full_name if sender else "Unknown",
        "sender_avatar_url": sender.avatar_url if sender else None,
        "body": message.body,
        "attachment_url": message.attachment_url,
        "attachment_filename": message.attachment_filename,
        "attachment_content_type": message.attachment_content_type,
        "attachment_size_bytes": message.attachment_size_bytes,
        "created_at": message.created_at,
        "is_own": message.sender_id == current_user_id,
    }


def _participant_for_user(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> ChatParticipant | None:
    return (
        db.query(ChatParticipant)
        .filter(
            ChatParticipant.conversation_id == conversation_id,
            ChatParticipant.user_id == user_id,
        )
        .first()
    )


def _require_participant(
    db: Session,
    conversation_id: int,
    user_id: int,
) -> ChatParticipant:
    participant = _participant_for_user(db, conversation_id, user_id)
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return participant


def _conversation_participant_ids(db: Session, conversation_id: int) -> list[int]:
    return [
        user_id
        for (user_id,) in db.query(ChatParticipant.user_id)
        .filter(ChatParticipant.conversation_id == conversation_id)
        .all()
    ]


def _conversation_visible_to_user(db: Session, conversation_id: int, current_user: User) -> bool:
    visible_role_names = _admin_visible_contact_role_names(current_user)
    if visible_role_names is None:
        return True

    participants = (
        db.query(ChatParticipant)
        .options(joinedload(ChatParticipant.user).joinedload(User.role))
        .filter(
            ChatParticipant.conversation_id == conversation_id,
            ChatParticipant.user_id != current_user.id,
        )
        .all()
    )
    return all(
        participant.user and _role_name(participant.user) in visible_role_names
        for participant in participants
    )


def _require_visible_conversation(db: Session, conversation_id: int, current_user: User) -> None:
    if not _conversation_visible_to_user(db, conversation_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

def _serialize_conversation(
    db: Session,
    conversation: ChatConversation,
    current_user_id: int,
    online_user_ids: set[int] | None = None,
) -> dict:
    participants = (
        db.query(ChatParticipant)
        .options(
            joinedload(ChatParticipant.user).joinedload(User.role),
            joinedload(ChatParticipant.user).joinedload(User.profile),
        )
        .filter(ChatParticipant.conversation_id == conversation.id)
        .all()
    )
    current_participant = next(
        (participant for participant in participants if participant.user_id == current_user_id),
        None,
    )
    last_message = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .first()
    )
    unread_query = db.query(func.count(ChatMessage.id)).filter(
        ChatMessage.conversation_id == conversation.id,
        ChatMessage.sender_id != current_user_id,
    )
    if current_participant and current_participant.last_read_message_id:
        unread_query = unread_query.filter(ChatMessage.id > current_participant.last_read_message_id)

    return {
        "id": conversation.id,
        "title": conversation.title,
        "is_group": conversation.is_group,
        "participants": [
            _serialize_user(participant.user, online_user_ids)
            for participant in participants
            if participant.user
        ],
        "last_message": _serialize_message(last_message, current_user_id) if last_message else None,
        "unread_count": int(unread_query.scalar() or 0),
        "updated_at": conversation.updated_at or conversation.created_at,
    }


def list_chat_contacts(db: Session, current_user: User, query: str = "", limit: int = 50) -> dict:
    normalized_query = query.strip()
    users_query = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.id != current_user.id, User.status == "active")
    )
    users_query = _apply_contact_scope(users_query, current_user)

    if normalized_query:
        pattern = f"%{normalized_query}%"
        users_query = users_query.filter(
            or_(User.full_name.ilike(pattern), User.email.ilike(pattern), User.username.ilike(pattern))
        )

    online_user_ids = _active_session_user_ids(db)
    users = users_query.order_by(User.full_name.asc(), User.id.asc()).limit(limit).all()
    return {"items": [_serialize_user(user, online_user_ids) for user in users]}


def list_chat_conversations(db: Session, current_user: User) -> dict:
    conversations = (
        db.query(ChatConversation)
        .join(ChatParticipant, ChatParticipant.conversation_id == ChatConversation.id)
        .filter(ChatParticipant.user_id == current_user.id)
        .order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc())
        .all()
    )
    visible_conversations = [
        conversation
        for conversation in conversations
        if _conversation_visible_to_user(db, conversation.id, current_user)
    ]
    online_user_ids = _active_session_user_ids(db)
    return {
        "items": [
            _serialize_conversation(db, conversation, current_user.id, online_user_ids)
            for conversation in visible_conversations
        ]
    }


def _find_direct_conversation(db: Session, user_id: int, participant_id: int) -> ChatConversation | None:
    first_alias = aliased(ChatParticipant)
    second_alias = aliased(ChatParticipant)
    return (
        db.query(ChatConversation)
        .join(first_alias, first_alias.conversation_id == ChatConversation.id)
        .join(
            second_alias,
            and_(
                second_alias.conversation_id == ChatConversation.id,
                second_alias.user_id == participant_id,
            ),
        )
        .filter(
            ChatConversation.is_group.is_(False),
            first_alias.user_id == user_id,
        )
        .first()
    )


def create_or_get_direct_conversation(
    db: Session,
    current_user: User,
    participant_id: int,
) -> dict:
    if participant_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot chat with yourself")

    participant_user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.id == participant_id, User.status == "active")
        .first()
    )
    if not participant_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not _can_start_direct_conversation(current_user, participant_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    conversation = _find_direct_conversation(db, current_user.id, participant_id)
    if not conversation:
        now = utc_now()
        conversation = ChatConversation(
            is_group=False,
            created_by_user_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(conversation)
        db.flush()
        db.add_all(
            [
                ChatParticipant(conversation_id=conversation.id, user_id=current_user.id),
                ChatParticipant(conversation_id=conversation.id, user_id=participant_id),
            ]
        )
        db.commit()
        db.refresh(conversation)

    online_user_ids = _active_session_user_ids(db)
    return {
        "conversation": _serialize_conversation(db, conversation, current_user.id, online_user_ids)
    }


def list_chat_messages(
    db: Session,
    current_user: User,
    conversation_id: int,
    limit: int = 100,
    before_id: int | None = None,
) -> dict:
    participant = _require_participant(db, conversation_id, current_user.id)
    _require_visible_conversation(db, conversation_id, current_user)
    query = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.conversation_id == conversation_id)
    )
    if before_id is not None:
        query = query.filter(ChatMessage.id < before_id)

    messages = query.order_by(ChatMessage.id.desc()).limit(limit).all()
    messages.reverse()
    if messages:
        participant.last_read_message_id = messages[-1].id
        db.commit()

    return {"items": [_serialize_message(message, current_user.id) for message in messages]}


def create_chat_message(
    db: Session,
    current_user: User,
    conversation_id: int,
    body: str,
) -> tuple[dict, list[int]]:
    normalized_body = body.strip()
    if not normalized_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty")

    participant = _require_participant(db, conversation_id, current_user.id)
    _require_visible_conversation(db, conversation_id, current_user)
    now = utc_now()
    message = ChatMessage(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=normalized_body,
        created_at=now,
    )
    db.add(message)

    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = now
    db.flush()
    participant.last_read_message_id = message.id
    db.commit()
    db.refresh(message)
    message = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.id == message.id)
        .first()
    )
    participant_ids = _conversation_participant_ids(db, conversation_id)
    return _serialize_message(message, current_user.id), participant_ids


def create_chat_attachment_message(
    db: Session,
    current_user: User,
    conversation_id: int,
    upload: UploadFile,
    body: str | None = None,
) -> tuple[dict, list[int]]:
    participant = _require_participant(db, conversation_id, current_user.id)
    _require_visible_conversation(db, conversation_id, current_user)
    attachment = upload_chat_file(upload)
    normalized_body = (body or "").strip() or attachment["filename"]
    now = utc_now()
    message = ChatMessage(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        body=normalized_body,
        attachment_url=attachment["url"],
        attachment_filename=attachment["filename"],
        attachment_content_type=attachment["content_type"],
        attachment_size_bytes=attachment["size_bytes"],
        created_at=now,
    )
    db.add(message)

    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = now
    db.flush()
    participant.last_read_message_id = message.id
    db.commit()
    db.refresh(message)
    message = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.id == message.id)
        .first()
    )
    participant_ids = _conversation_participant_ids(db, conversation_id)
    return _serialize_message(message, current_user.id), participant_ids


def share_chat_attachment_message(
    db: Session,
    current_user: User,
    message_id: int,
    participant_id: int,
    body: str | None = None,
) -> tuple[dict, list[int]]:
    original_message = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.id == message_id)
        .first()
    )
    if not original_message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    _require_participant(db, original_message.conversation_id, current_user.id)
    _require_visible_conversation(db, original_message.conversation_id, current_user)

    conversation_response = create_or_get_direct_conversation(
        db,
        current_user,
        participant_id,
    )
    target_conversation_id = conversation_response["conversation"]["id"]
    participant = _require_participant(db, target_conversation_id, current_user.id)
    normalized_body = (body or "").strip() or original_message.body
    now = utc_now()
    message = ChatMessage(
        conversation_id=target_conversation_id,
        sender_id=current_user.id,
        body=normalized_body,
        attachment_url=original_message.attachment_url,
        attachment_filename=original_message.attachment_filename,
        attachment_content_type=original_message.attachment_content_type,
        attachment_size_bytes=original_message.attachment_size_bytes,
        created_at=now,
    )
    db.add(message)

    conversation = (
        db.query(ChatConversation)
        .filter(ChatConversation.id == target_conversation_id)
        .first()
    )
    if conversation:
        conversation.updated_at = now
    db.flush()
    participant.last_read_message_id = message.id
    db.commit()
    db.refresh(message)
    message = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.id == message.id)
        .first()
    )
    participant_ids = _conversation_participant_ids(db, target_conversation_id)
    return _serialize_message(message, current_user.id), participant_ids


def mark_conversation_read(db: Session, current_user: User, conversation_id: int) -> None:
    participant = _require_participant(db, conversation_id, current_user.id)
    _require_visible_conversation(db, conversation_id, current_user)
    latest_message_id = (
        db.query(func.max(ChatMessage.id))
        .filter(ChatMessage.conversation_id == conversation_id)
        .scalar()
    )
    if latest_message_id:
        participant.last_read_message_id = latest_message_id
        db.commit()


def delete_chat_message(
    db: Session,
    current_user: User,
    message_id: int,
) -> tuple[dict, list[int], int, int]:
    message = (
        db.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter(ChatMessage.id == message_id)
        .first()
    )
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    _require_participant(db, message.conversation_id, current_user.id)
    _require_visible_conversation(db, message.conversation_id, current_user)
    role_name = current_user.role.name if current_user.role else None
    can_delete = message.sender_id == current_user.id or role_name in {"admin", "administrator"}
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender can delete this message",
        )

    conversation_id = message.conversation_id
    participant_ids = _conversation_participant_ids(db, conversation_id)
    previous_message_id = (
        db.query(func.max(ChatMessage.id))
        .filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.id < message_id,
        )
        .scalar()
    )
    db.query(ChatParticipant).filter(
        ChatParticipant.last_read_message_id == message_id
    ).update(
        {ChatParticipant.last_read_message_id: previous_message_id},
        synchronize_session=False,
    )
    db.delete(message)
    db.flush()

    latest_message_created_at = (
        db.query(func.max(ChatMessage.created_at))
        .filter(ChatMessage.conversation_id == conversation_id)
        .scalar()
    )
    conversation = db.query(ChatConversation).filter(ChatConversation.id == conversation_id).first()
    if conversation:
        conversation.updated_at = latest_message_created_at or utc_now()

    db.commit()
    return {"message": "Message deleted successfully"}, participant_ids, conversation_id, message_id


def delete_chat_conversation(db: Session, current_user: User, conversation_id: int) -> dict:
    participant = _participant_for_user(db, conversation_id, current_user.id)
    if not participant:
        return {"message": "Conversation deleted successfully"}

    _require_visible_conversation(db, conversation_id, current_user)

    db.query(ChatParticipant).filter(
        ChatParticipant.conversation_id == conversation_id
    ).delete(synchronize_session=False)
    db.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).delete(
        synchronize_session=False,
    )
    db.query(ChatConversation).filter(ChatConversation.id == conversation_id).delete(
        synchronize_session=False,
    )

    db.commit()
    return {"message": "Conversation deleted successfully"}


def get_chat_user_by_session_token(db: Session, session_token: str) -> User | None:
    from app.services.auth_service import get_session_by_token, require_active_session

    session = require_active_session(get_session_by_token(db, session_token))
    return (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.id == session.user_id, User.status == "active")
        .first()
    )
