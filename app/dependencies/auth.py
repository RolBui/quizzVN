from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth_service import (
    get_session_by_token,
    get_session_by_refresh_token,
    require_active_session,
    require_refreshable_session,
    touch_user_session,
)


def get_access_token_from_request(request: Request) -> str:
    cookie_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token:
            return token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def get_refresh_token_from_request(request: Request) -> str:
    cookie_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token not found",
    )


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
):
    session_token = get_access_token_from_request(request)
    session = get_session_by_token(db, session_token)
    session = require_active_session(session)
    return touch_user_session(db, session)


def get_refreshable_session(
    request: Request,
    db: Session = Depends(get_db),
):
    refresh_token = get_refresh_token_from_request(request)
    session = get_session_by_refresh_token(db, refresh_token)
    return require_refreshable_session(session)


def get_current_user(session=Depends(get_current_session)):
    return session.user


def get_current_student(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.id == current_user.id)
        .first()
    )
    if not user or not user.role or user.role.name != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student role is required",
        )
    return user


def get_current_teacher(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.profile))
        .filter(User.id == current_user.id)
        .first()
    )
    if not user or not user.role or user.role.name != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher role is required",
        )
    return user
