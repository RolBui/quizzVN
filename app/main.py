from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.auth_router import router as auth_router
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.database import test_db_connection
from app.schemas.common import DbCheckResponse, HealthResponse, RootResponse
from app.services.auth_service import bootstrap_auth_storage

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="Backend API cho quizz vn",
    swagger_ui_parameters={
        "withCredentials": True,
    },
)
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

@app.get("/", response_model=RootResponse)
def root() -> RootResponse:
    return {
        "message": "Quiz VN API "
    }


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return {
        "status": "ok"
    }


@app.get("/db-check", response_model=DbCheckResponse)
def db_check() -> DbCheckResponse:
    result = test_db_connection()
    return {
        "database": "connected" if result else "failed"
    }

app.include_router(auth_router)
