from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.admin_router import router as admin_router
from app.routers.analytics_router import router as analytics_router
from app.routers.ai_exam_router import router as ai_exam_router
from app.routers.ai_agent_router import router as ai_agent_router
from app.routers.auth_router import router as auth_router
from app.routers.billing_router import router as billing_router
from app.routers.chat_router import router as chat_router
from app.routers.dev_router import router as dev_router
from app.routers.student_router import router as student_router
from app.routers.teacher_router import router as teacher_router
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.database import test_db_connection
from app.schemas.common import DbCheckResponse, HealthResponse, RootResponse
from app.services.auth_service import bootstrap_auth_storage
from app.services.analytics_service import bootstrap_web_analytics_storage
from app.services.chat_service import bootstrap_chat_storage
from app.services.ai_exam_service import bootstrap_ai_exam_storage
from app.services.billing_service import bootstrap_billing_storage
from app.services.media_service import bootstrap_media_storage
from app.services.student_service import bootstrap_student_learning_storage
import asyncio
from pathlib import Path

from fastapi.responses import FileResponse
from app.routers.chat_router import INSTANCE_ID, manager
from app.services.realtime_broker import broker

BASE_DIR = Path(__file__).resolve().parents[1]
FAVICON_PATH = BASE_DIR / "admin-web" / "src" / "assets" / "logoquizzsmall.png"
EMAIL_LOGO_PATH = BASE_DIR / "admin-web" / "src" / "assets" / "logo quizzvn.png"

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="Backend API cho quizz vn",
    swagger_ui_parameters={
        "withCredentials": True,
    },
)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(FAVICON_PATH, media_type="image/png")


@app.get("/assets/email-logo.png", include_in_schema=False)
def email_logo() -> FileResponse:
    return FileResponse(EMAIL_LOGO_PATH, media_type="image/png")


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
    https_only=settings.COOKIE_SECURE,
    session_cookie=settings.OAUTH_SESSION_COOKIE_NAME,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_bootstrap() -> None:
    bootstrap_auth_storage()
    bootstrap_web_analytics_storage()
    bootstrap_student_learning_storage()
    bootstrap_media_storage()
    bootstrap_chat_storage()
    bootstrap_ai_exam_storage()
    bootstrap_billing_storage()

# @app.get("/", response_model=RootResponse)
# def root() -> RootResponse:
#     return {
#         "message": "Quiz VN API "
#     }


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return {
        "status": "ok"
    }


async def handle_chat_event(payload: dict):
    if payload.get("type") == "message_created":
        if payload.get("origin_instance_id") == INSTANCE_ID:
            return
        await manager.broadcast_to_users(
            payload["recipient_ids"],
            {
                "type": "message_created",
                "message": payload["message"],
            },
        )
    elif payload.get("type") == "message_deleted":
        if payload.get("origin_instance_id") == INSTANCE_ID:
            return
        await manager.broadcast_to_users(
            payload["recipient_ids"],
            {
                "type": "message_deleted",
                "conversation_id": payload["conversation_id"],
                "message_id": payload["message_id"],
            },
        )

@app.on_event("startup")
async def startup_realtime():
    app.state.chat_broker_task = asyncio.create_task(
        broker.listen(handle_chat_event)
    )

# @app.get("/db-check", response_model=DbCheckResponse)
# def db_check() -> DbCheckResponse:
#     result = test_db_connection()
#     return {
#         "database": "connected" if result else "failed"
#     }

app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(admin_router)
app.include_router(student_router)
app.include_router(teacher_router)
app.include_router(chat_router)
app.include_router(ai_exam_router)
app.include_router(ai_agent_router)
app.include_router(billing_router)
app.include_router(dev_router)
