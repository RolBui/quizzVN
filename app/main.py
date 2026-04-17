from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.routers.auth_router import router as auth_router
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.database import get_db, test_db_connection

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="Backend API cho hệ thống thi online"
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY
)

@app.get("/")
def root():
    return {
        "message": "Quiz Online API is running"
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }

@app.get("/db-check")
def db_check():
    result = test_db_connection()
    return {
        "database": "connected" if result == 1 else "failed"
    }
app.include_router(auth_router)