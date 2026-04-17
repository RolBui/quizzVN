from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.services.auth_service import (
    get_session_by_token,
    require_active_session,
    require_refreshable_session,
    touch_user_session,
)


def get_session_token_from_request(request: Request) -> str:
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


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
):
    session_token = get_session_token_from_request(request)
    session = get_session_by_token(db, session_token)
    session = require_active_session(session)
    return touch_user_session(db, session)


def get_refreshable_session(
    request: Request,
    db: Session = Depends(get_db),
):
    session_token = get_session_token_from_request(request)
    session = get_session_by_token(db, session_token)
    return require_refreshable_session(session)


def get_current_user(session=Depends(get_current_session)):
    return session.user
