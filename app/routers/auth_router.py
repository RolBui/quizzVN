from fastapi import APIRouter, Request, Depends, Response, status, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from app.core.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_session, get_current_user, get_refreshable_session
from app.schemas.auth import (
    AuthSessionResponse,
    CompleteOnboardingRequest,
    CompleteOnboardingResponse,
    LoginRequest,
    MeResponse,
    RefreshSessionResponse,
    RegisterRequest,
    RevokeSessionResponse,
    RoleListResponse,
    SessionListResponse,
    UpdateProfileRequest,
    UpdateProfileResponse,
    ProfileResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    AvatarListResponse,
    ProfileImageUploadResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import (
    build_user_payload,
    complete_user_onboarding,
    handle_google_callback,
    get_selectable_roles,
    list_user_sessions,
    login_local_user,
    logout_user_session,
    register_local_user,
    refresh_user_session,
    revoke_user_session_by_id,
    serialize_role_option,
    serialize_session,
    serialize_session_tokens,
    update_user_profile,
    change_user_password,
    update_user_avatar,
)
from app.services.email_verification_service import (
    build_frontend_email_verification_redirect_url,
    send_email_verification_email,
    verify_email_token,
)
from app.services.media_service import (
    delete_uploaded_avatars_except_url,
    save_avatar_image,
    list_uploaded_images,
)
from fastapi import UploadFile, File

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


def _frontend_auth_callback_target() -> str:
    return f"{settings.FRONTEND_URL}{settings.FRONTEND_AUTH_CALLBACK_PATH}"


def _google_login_responses() -> dict:
    return {
        302: {
            "description": (
                "Redirects the browser to Google OAuth, stores a temporary "
                f"`{settings.OAUTH_SESSION_COOKIE_NAME}` cookie for the OAuth handshake, "
                "and requests `prompt=select_account` so Google shows the account chooser "
                "when a Google session already exists."
            ),
            "headers": {
                "Location": {
                    "description": "Google OAuth authorization URL.",
                    "schema": {"type": "string"},
                },
                "Set-Cookie": {
                    "description": (
                        f"Temporary `{settings.OAUTH_SESSION_COOKIE_NAME}` cookie used "
                        "to validate the OAuth flow."
                    ),
                    "schema": {"type": "string"},
                },
            },
        }
    }


def _google_callback_responses() -> dict:
    frontend_callback = _frontend_auth_callback_target()
    return {
        302: {
            "description": (
                "Sets the auth cookies and redirects the browser back to the frontend "
                f"callback at `{frontend_callback}`. On success the redirect query string "
                "includes `provider=google` and `needs_onboarding=true|false`. On failure "
                "the redirect query string includes `error=<code>`."
            ),
            "headers": {
                "Location": {
                    "description": (
                        f"Frontend callback URL `{frontend_callback}`. Success query params: "
                        "`provider`, `needs_onboarding`. Error query param: `error`."
                    ),
                    "schema": {"type": "string"},
                },
                "Set-Cookie": {
                    "description": (
                        f"HTTP-only auth cookies `{settings.SESSION_COOKIE_NAME}` and "
                        f"`{settings.REFRESH_COOKIE_NAME}` are set before redirecting."
                    ),
                    "schema": {"type": "string"},
                },
            },
        }
    }


def _verify_email_responses() -> dict:
    frontend_target = f"{settings.FRONTEND_URL}{settings.FRONTEND_EMAIL_VERIFICATION_PATH}"
    return {
        302: {
            "description": (
                "Verifies the email token and redirects the browser to the frontend "
                f"verification page at `{frontend_target}` with a `status` query param. "
                "Possible values include `verified`, `already_verified`, "
                "`verification_token_invalid`, and `verification_token_expired`."
            ),
            "headers": {
                "Location": {
                    "description": (
                        f"Frontend verification page `{frontend_target}` with `status=<value>`."
                    ),
                    "schema": {"type": "string"},
                }
            },
        }
    }


def set_access_cookie(response: Response, tokens: dict) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=tokens["session_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.SESSION_EXPIRE_MINUTES * 60,
        path="/",
    )


def set_refresh_cookie(response: Response, tokens: dict) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.SESSION_REFRESH_DAYS * 24 * 60 * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
    )
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path="/",
    )
    response.delete_cookie(
        key=settings.OAUTH_SESSION_COOKIE_NAME,
        path="/",
    )


def set_auth_cookies(response: Response, tokens: dict) -> None:
    set_access_cookie(response, tokens)
    set_refresh_cookie(response, tokens)


def build_auth_session_response(result: dict) -> dict:
    tokens = result.get("tokens") or {}
    return {
        **result,
        "access_token": tokens.get("session_token"),
    }


def build_frontend_auth_redirect_url(**params: str | bool) -> str:
    base_url = f"{settings.FRONTEND_URL}{settings.FRONTEND_AUTH_CALLBACK_PATH}"
    query_params = {
        key: str(value).lower() if isinstance(value, bool) else value
        for key, value in params.items()
        if value is not None
    }
    if not query_params:
        return base_url
    return f"{base_url}?{urlencode(query_params)}"


@router.post("/register", response_model=AuthSessionResponse)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    result = register_local_user(
        db=db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    set_auth_cookies(response, result["tokens"])
    return build_auth_session_response(result)


@router.post("/login", response_model=AuthSessionResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    result = login_local_user(
        db=db,
        email=payload.email,
        password=payload.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    set_auth_cookies(response, result["tokens"])
    return build_auth_session_response(result)


@router.get(
    "/google/login",
    response_model=None,
    status_code=status.HTTP_302_FOUND,
    responses=_google_login_responses(),
)
async def google_login(request: Request) -> RedirectResponse:
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    redirect_response = await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        prompt=settings.GOOGLE_OAUTH_PROMPT,
    )
    redirect_response.status_code = status.HTTP_302_FOUND
    return redirect_response


@router.get(
    "/google/callback",
    response_model=None,
    status_code=status.HTTP_302_FOUND,
    responses=_google_callback_responses(),
)
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info:
        user_info = await oauth.google.userinfo(token=token)

    if not user_info:
        return RedirectResponse(
            url=build_frontend_auth_redirect_url(error="google_user_info_not_found"),
            status_code=status.HTTP_302_FOUND,
        )

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    result = handle_google_callback(db, token, user_info, ip_address, user_agent)
    redirect_response = RedirectResponse(
        url=build_frontend_auth_redirect_url(
            provider="google",
            needs_onboarding=result["user"]["needs_onboarding"],
        ),
        status_code=status.HTTP_302_FOUND,
    )
    request.session.clear()
    set_auth_cookies(redirect_response, result["tokens"])
    return redirect_response


@router.get(
    "/verify-email",
    response_model=None,
    status_code=status.HTTP_302_FOUND,
    responses=_verify_email_responses(),
)
def verify_email(
    token: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        verification_status = verify_email_token(db, token)
    except HTTPException as exc:
        verification_status = str(exc.detail)

    return RedirectResponse(
        url=build_frontend_email_verification_redirect_url(verification_status),
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/email-verification/resend", response_model=MessageResponse)
def resend_email_verification(
    current_user=Depends(get_current_user),
) -> MessageResponse:
    if current_user.email_verified:
        return {"message": "Email is already verified"}

    send_email_verification_email(current_user)
    return {"message": "Verification email sent"}


@router.get("/me", response_model=MeResponse)
def get_me(
    db: Session = Depends(get_db),
    current_session=Depends(get_current_session),
    current_user=Depends(get_current_user),
) -> MeResponse:
    return {
        "user": build_user_payload(db, current_user),
        "session": serialize_session(current_session),
    }


@router.get("/roles", response_model=RoleListResponse)
def get_available_roles(db: Session = Depends(get_db)) -> RoleListResponse:
    roles = get_selectable_roles(db)
    return {
        "roles": [serialize_role_option(role) for role in roles],
    }


@router.post("/refresh", response_model=RefreshSessionResponse)
def refresh_session(
    response: Response,
    current_session=Depends(get_refreshable_session),
    db: Session = Depends(get_db),
) -> RefreshSessionResponse:
    refreshed_session = refresh_user_session(db, current_session)
    tokens = serialize_session_tokens(refreshed_session)
    set_auth_cookies(response, tokens)
    return {
        "message": "Session refreshed successfully",
        "session": serialize_session(refreshed_session),
        "access_token": tokens["session_token"],
    }


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    current_session=Depends(get_current_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    logout_user_session(db, current_session)
    request.session.clear()
    clear_auth_cookies(response)
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
        clear_auth_cookies(response)

    return {
        "message": "Session revoked successfully",
        "session": serialize_session(session),
    }


@router.post("/onboarding/complete", response_model=CompleteOnboardingResponse)
def complete_onboarding(
    payload: CompleteOnboardingRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CompleteOnboardingResponse:
    return complete_user_onboarding(
        db=db,
        user=current_user,
        role_name=payload.role,
        full_name=payload.full_name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        school_name=payload.school_name,
    )


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProfileResponse:
    return {"user": build_user_payload(db, current_user)}


@router.put("/profile", response_model=UpdateProfileResponse)
def update_profile(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> UpdateProfileResponse:
    return update_user_profile(
        db=db,
        user=current_user,
        full_name=payload.full_name,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        school_name=payload.school_name,
    )


@router.put("/password", response_model=ChangePasswordResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChangePasswordResponse:
    return change_user_password(
        db=db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        confirm_password=payload.confirm_password,
    )


@router.get("/profile/avatar", response_model=AvatarListResponse)
def get_avatars(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AvatarListResponse:
    items = list_uploaded_images(db, current_user.id, category="avatar")
    return {"items": items}


def _save_and_update_avatar(
    image: UploadFile,
    db: Session,
    current_user,
) -> ProfileImageUploadResponse:
    image_data = save_avatar_image(db, current_user.id, image)
    return update_user_avatar(db, current_user, image_data["url"])


def _replace_avatar(
    image: UploadFile,
    db: Session,
    current_user,
) -> ProfileImageUploadResponse:
    result = _save_and_update_avatar(image, db, current_user)
    delete_uploaded_avatars_except_url(db, current_user.id, result["avatar_url"])
    return result


@router.post("/profile/avatar", response_model=ProfileImageUploadResponse)
def upload_avatar(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProfileImageUploadResponse:
    return _save_and_update_avatar(image, db, current_user)


@router.put("/profile/avatar", response_model=ProfileImageUploadResponse)
def update_avatar(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProfileImageUploadResponse:
    return _replace_avatar(image, db, current_user)
