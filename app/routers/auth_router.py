from fastapi import APIRouter, Request, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_session, get_current_user, get_refreshable_session
from app.services.auth_service import (
    handle_google_callback,
    list_user_sessions,
    logout_user_session,
    refresh_user_session,
    revoke_user_session_by_id,
    serialize_session,
    serialize_user,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    },
)


def set_session_cookie(response: JSONResponse, session_token: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.SESSION_REFRESH_DAYS * 24 * 60 * 60,
        path="/",
    )


def clear_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
    )


@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info:
        user_info = await oauth.google.userinfo(token=token)

    if not user_info:
        return JSONResponse(
            status_code=400,
            content={"message": "Google user info not found"}
        )

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = handle_google_callback(db, token, user_info, ip_address, user_agent)
    response = JSONResponse(content=jsonable_encoder(result))
    set_session_cookie(response, result["session"]["session_token"])
    return response


@router.get("/me")
def get_me(
    current_session=Depends(get_current_session),
    current_user=Depends(get_current_user),
):
    return {
        "user": serialize_user(current_user),
        "session": serialize_session(current_session),
    }


@router.post("/refresh")
def refresh_session(current_session=Depends(get_refreshable_session), db: Session = Depends(get_db)):
    refreshed_session = refresh_user_session(db, current_session)
    response = JSONResponse(
        content=jsonable_encoder(
            {
                "message": "Session refreshed successfully",
                "session": serialize_session(refreshed_session),
            }
        )
    )
    set_session_cookie(response, refreshed_session.session_token)
    return response


@router.post("/logout")
def logout(current_session=Depends(get_current_session), db: Session = Depends(get_db)):
    logout_user_session(db, current_session)
    response = JSONResponse(content={"message": "Logout successful"})
    clear_session_cookie(response)
    return response


@router.get("/sessions")
def get_my_sessions(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = list_user_sessions(db, current_user.id)
    return {
        "sessions": [serialize_session(session) for session in sessions],
    }


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: int,
    current_session=Depends(get_current_session),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = revoke_user_session_by_id(db, current_user.id, session_id)
    response = JSONResponse(
        content=jsonable_encoder(
            {
                "message": "Session revoked successfully",
                "session": serialize_session(session),
            }
        )
    )

    if session.id == current_session.id:
        clear_session_cookie(response)

    return response
