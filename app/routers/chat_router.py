from collections import defaultdict
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketState

from app.core.config import settings
from app.database import SessionLocal, get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ChatContactListResponse,
    ChatConversationListResponse,
    ChatConversationResponse,
    ChatMessageListResponse,
    ChatMessageResponse,
    CreateChatConversationRequest,
    CreateChatMessageRequest,
    ShareChatMessageRequest,
)
from app.schemas.common import MessageResponse
from app.services.chat_service import (
    create_chat_attachment_message,
    create_chat_message,
    create_or_get_direct_conversation,
    delete_chat_conversation,
    delete_chat_message,
    get_chat_user_by_session_token,
    list_chat_contacts,
    list_chat_conversations,
    list_chat_messages,
    mark_conversation_read,
    share_chat_attachment_message,
)
from app.services.realtime_broker import broker

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)
INSTANCE_ID = uuid4().hex


class ChatConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    def active_user_ids(self) -> list[int]:
        return sorted(self._connections.keys())

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)
        logger.info("Chat WebSocket connected for user_id=%s", user_id)
        await websocket.send_json(
            {"type": "presence_snapshot", "user_ids": self.active_user_ids()}
        )
        await self.broadcast_presence(user_id, True)

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)
            await self.broadcast_presence(user_id, False)

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        sockets = list(self._connections.get(user_id, set()))
        stale_sockets: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                stale_sockets.append(socket)
        for socket in stale_sockets:
            self._connections[user_id].discard(socket)
        if user_id in self._connections and not self._connections[user_id]:
            self._connections.pop(user_id, None)

    async def broadcast_to_users(self, user_ids: list[int], payload: dict) -> None:
        for user_id in set(user_ids):
            await self.send_to_user(user_id, payload)

    async def broadcast_presence(self, user_id: int, is_online: bool) -> None:
        payload = {"type": "presence_changed", "user_id": user_id, "is_online": is_online}
        for target_user_id in list(self._connections.keys()):
            await self.send_to_user(target_user_id, payload)


manager = ChatConnectionManager()


async def dispatch_message_created(
    participant_ids: list[int],
    message: dict,
) -> None:
    payload = {"type": "message_created", "message": message}
    await manager.broadcast_to_users(participant_ids, payload)
    published = await broker.publish(
        {
            "type": "message_created",
            "origin_instance_id": INSTANCE_ID,
            "recipient_ids": participant_ids,
            "message": message,
        }
    )
    if not published:
        logger.info("Chat message_created sent by local WebSocket manager only.")


async def dispatch_message_deleted(
    participant_ids: list[int],
    conversation_id: int,
    message_id: int,
) -> None:
    payload = {
        "type": "message_deleted",
        "conversation_id": conversation_id,
        "message_id": message_id,
    }
    await manager.broadcast_to_users(participant_ids, payload)
    published = await broker.publish(
        {
            **payload,
            "origin_instance_id": INSTANCE_ID,
            "recipient_ids": participant_ids,
        }
    )
    if not published:
        logger.info("Chat message_deleted sent by local WebSocket manager only.")


@router.get("/contacts", response_model=ChatContactListResponse)
def get_chat_contacts(
    query: str = Query("", max_length=100),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatContactListResponse:
    return list_chat_contacts(db, current_user, query=query, limit=limit)


@router.get("/conversations", response_model=ChatConversationListResponse)
def get_chat_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatConversationListResponse:
    return list_chat_conversations(db, current_user)


@router.post("/conversations", response_model=ChatConversationResponse)
def post_chat_conversation(
    payload: CreateChatConversationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatConversationResponse:
    return create_or_get_direct_conversation(db, current_user, payload.participant_id)


@router.delete("/conversations/{conversation_id}", response_model=MessageResponse)
def delete_chat_conversation_route(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    return delete_chat_conversation(db, current_user, conversation_id)


@router.get("/conversations/{conversation_id}/messages", response_model=ChatMessageListResponse)
def get_chat_conversation_messages(
    conversation_id: int,
    limit: int = Query(100, ge=1, le=200),
    before_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageListResponse:
    return list_chat_messages(db, current_user, conversation_id, limit=limit, before_id=before_id)


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageResponse)
async def post_chat_conversation_message(
    conversation_id: int,
    payload: CreateChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    message, participant_ids = create_chat_message(db, current_user, conversation_id, payload.body)
    await dispatch_message_created(participant_ids, message)
    return {"message": message}


@router.post("/conversations/{conversation_id}/attachments", response_model=ChatMessageResponse)
async def post_chat_conversation_attachment(
    conversation_id: int,
    file: UploadFile = File(...),
    body: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    message, participant_ids = create_chat_attachment_message(
        db,
        current_user,
        conversation_id,
        file,
        body,
    )
    await dispatch_message_created(participant_ids, message)
    return {"message": message}


@router.delete("/messages/{message_id}", response_model=MessageResponse)
async def delete_chat_message_route(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    response, participant_ids, conversation_id, deleted_message_id = delete_chat_message(
        db,
        current_user,
        message_id,
    )
    await dispatch_message_deleted(participant_ids, conversation_id, deleted_message_id)
    return response


@router.post("/messages/{message_id}/share", response_model=ChatMessageResponse)
async def post_chat_message_share(
    message_id: int,
    payload: ShareChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    message, participant_ids = share_chat_attachment_message(
        db,
        current_user,
        message_id,
        payload.participant_id,
        payload.body,
    )
    await dispatch_message_created(participant_ids, message)
    return {"message": message}


async def _authenticate_websocket(websocket: WebSocket) -> User | None:
    session_token = websocket.cookies.get(settings.SESSION_COOKIE_NAME)
    if not session_token:
        session_token = websocket.query_params.get("token")
    if not session_token:
        logger.warning("Chat WebSocket rejected: missing session token")
        return None

    db = SessionLocal()
    try:
        return get_chat_user_by_session_token(db, session_token)
    except Exception as exc:
        logger.warning("Chat WebSocket rejected: %s", exc)
        return None
    finally:
        db.close()


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket) -> None:
    current_user = await _authenticate_websocket(websocket)
    if not current_user:
        await websocket.close(code=1008)
        return

    await manager.connect(current_user.id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            event_type = payload.get("type")
            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            db = SessionLocal()
            try:
                if event_type == "send_message":
                    conversation_id = int(payload.get("conversation_id") or 0)
                    body = str(payload.get("body") or "")
                    message, participant_ids = create_chat_message(
                        db,
                        current_user,
                        conversation_id,
                        body,
                    )
                    await dispatch_message_created(participant_ids, message)
                elif event_type == "mark_read":
                    conversation_id = int(payload.get("conversation_id") or 0)
                    mark_conversation_read(db, current_user, conversation_id)
                else:
                    await websocket.send_json(
                        {"type": "error", "detail": "Unsupported chat event"}
                    )
            except Exception as exc:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json({"type": "error", "detail": str(exc)})
            finally:
                db.close()
    except WebSocketDisconnect:
        await manager.disconnect(current_user.id, websocket)
    finally:
        await manager.disconnect(current_user.id, websocket)
