from fastapi import APIRouter, Request, Depends, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_session, get_current_user, get_refreshable_session
from app.schemas.auth import (
    GoogleCallbackResponse,
    MeResponse,
    RefreshSessionResponse,
    RevokeSessionResponse,
    SessionListResponse,
)
from app.schemas.common import MessageResponse
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


def set_session_cookie(response: Response, session_token: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.SESSION_REFRESH_DAYS * 24 * 60 * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
    )


@router.get(
    "/google/login",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={307: {"description": "Redirect to Google OAuth"}},
)
async def google_login(request: Request) -> RedirectResponse:
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=GoogleCallbackResponse)
async def google_callback(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> GoogleCallbackResponse | JSONResponse:
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
    set_session_cookie(response, result["session"]["session_token"])
    return result


@router.get("/me", response_model=MeResponse)
def get_me(
    current_session=Depends(get_current_session),
    current_user=Depends(get_current_user),
) -> MeResponse:
    return {
        "user": serialize_user(current_user),
        "session": serialize_session(current_session),
    }


@router.post("/refresh", response_model=RefreshSessionResponse)
def refresh_session(
    response: Response,
    current_session=Depends(get_refreshable_session),
    db: Session = Depends(get_db),
) -> RefreshSessionResponse:
    refreshed_session = refresh_user_session(db, current_session)
    set_session_cookie(response, refreshed_session.session_token)
    return {
        "message": "Session refreshed successfully",
        "session": serialize_session(refreshed_session),
    }


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    current_session=Depends(get_current_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    logout_user_session(db, current_session)
    clear_session_cookie(response)
    return {"message": "Logout successful"}


@router.get("/sessions", response_model=SessionListResponse)
def get_my_sessions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    sessions = list_user_sessions(db, current_user.id)
    return {
        "sessions": [serialize_session(session) for session in sessions],
    }


@router.delete("/sessions/{session_id}", response_model=RevokeSessionResponse)
def revoke_session(
    session_id: int,
    response: Response,
    current_session=Depends(get_current_session),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RevokeSessionResponse:
    session = revoke_user_session_by_id(db, current_user.id, session_id)

    if session.id == current_session.id:
        clear_session_cookie(response)

    return {
        "message": "Session revoked successfully",
        "session": serialize_session(session),
    }
