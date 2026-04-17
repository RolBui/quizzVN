import re
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.security import generate_session_token, get_expiry, get_refresh_expiry, utc_now
from app.core.security import generate_refresh_token
from app.models.role import Role
from app.models.user import User
from app.models.oauth_provider import OAuthProvider
from app.models.oauth_account import OAuthAccount
from app.models.user_session import UserSession


def _resolve_token_expires_at(token: dict):
    expires_at = token.get("expires_at")
    if isinstance(expires_at, datetime):
        return expires_at

    if isinstance(expires_at, (int, float)):
        return datetime.fromtimestamp(expires_at, tz=timezone.utc)

    expires_in = token.get("expires_in")
    if expires_in:
        return utc_now() + timedelta(seconds=int(expires_in))

    return None


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def get_default_role(db: Session):
    role = db.query(Role).filter(Role.name == "student").first()
    if role:
        return role

    role = Role(name="student")
    db.add(role)
    db.flush()
    return role


def build_username_from_email(db: Session, email: str) -> str:
    base = email.split("@")[0].lower()
    base = re.sub(r"[^a-z0-9_]+", "_", base).strip("_")

    if not base:
        base = "user"

    username = base
    counter = 1

    while db.query(User).filter(User.username == username).first():
        username = f"{base}_{counter}"
        counter += 1

    return username


def find_or_create_user_from_google(db: Session, user_info: dict):
    email = user_info.get("email")
    google_sub = user_info.get("sub")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    if not google_sub:
        raise HTTPException(status_code=400, detail="Google user id not found")

    user = db.query(User).filter(User.email == email).first()
    if user:
        if not user.full_name and user_info.get("name"):
            user.full_name = user_info.get("name")

        if user_info.get("picture"):
            user.avatar_url = user_info.get("picture")

        user.email_verified = True
        if user.auth_type == "local":
            user.auth_type = "mixed"
        elif not user.auth_type:
            user.auth_type = "oauth"

        return user, False

    default_role = get_default_role(db)

    user = User(
        role_id=default_role.id,
        full_name=user_info.get("name") or email.split("@")[0],
        username=build_username_from_email(db, email),
        email=email,
        avatar_url=user_info.get("picture"),
        auth_type="oauth",
        email_verified=True,
        status="active",
        is_first_login=True,
        max_exam_create=50,
        max_document_create=50,
        last_login_at=utc_now(),
    )

    db.add(user)
    db.flush()

    return user, True


def upsert_google_oauth_account(db: Session, user, provider, token: dict, user_info: dict):
    provider_user_id = user_info.get("sub")
    provider_email = user_info.get("email")
    provider_username = user_info.get("name") or provider_email

    oauth_account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider_id == provider.id,
            or_(
                OAuthAccount.provider_user_id == provider_user_id,
                OAuthAccount.user_id == user.id,
            ),
        )
        .first()
    )

    if not oauth_account:
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider_id=provider.id,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            provider_username=provider_username,
            access_token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            token_expires_at=_resolve_token_expires_at(token),
        )
        db.add(oauth_account)
        db.flush()
        return oauth_account

    oauth_account.user_id = user.id
    oauth_account.provider_user_id = provider_user_id
    oauth_account.provider_email = provider_email
    oauth_account.provider_username = provider_username
    oauth_account.access_token = token.get("access_token")
    oauth_account.refresh_token = token.get("refresh_token")
    oauth_account.token_expires_at = _resolve_token_expires_at(token)

    return oauth_account


def create_user_session(
    db: Session,
    user,
    login_method: str,
    ip_address: str | None,
    user_agent: str | None,
):
    session = UserSession(
        user_id=user.id,
        login_method=login_method,
        ip_address=ip_address,
        user_agent=user_agent,
        is_revoked=False,
        expires_at=get_expiry(),
        refresh_expires_at=get_refresh_expiry(),
        created_at=utc_now(),
        last_used_at=utc_now(),
        session_token=generate_session_token(),
        refresh_token=generate_refresh_token(),
    )

    db.add(session)
    db.flush()

    return session


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "role_id": user.role_id,
        "role_name": user.role.name if user.role else None,
        "full_name": user.full_name,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "auth_type": user.auth_type,
        "email_verified": user.email_verified,
        "status": user.status,
        "is_first_login": user.is_first_login,
        "max_exam_create": user.max_exam_create,
        "max_document_create": user.max_document_create,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def serialize_session(session: UserSession) -> dict:
    return {
        "id": session.id,
        "login_method": session.login_method,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "is_revoked": session.is_revoked,
        "expires_at": session.expires_at,
        "refresh_expires_at": session.refresh_expires_at,
        "created_at": session.created_at,
        "last_used_at": session.last_used_at,
        "session_token": session.session_token,
    }


def _get_session_query(db: Session):
    return db.query(UserSession).options(
        joinedload(UserSession.user).joinedload(User.role)
    )


def get_session_by_token(db: Session, session_token: str):
    return (
        _get_session_query(db)
        .filter(UserSession.session_token == session_token)
        .first()
    )


def require_active_session(session: UserSession | None) -> UserSession:
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found",
        )

    if session.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
        )

    expires_at = _normalize_datetime(session.expires_at)
    if expires_at is not None and expires_at <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired",
        )

    return session


def require_refreshable_session(session: UserSession | None) -> UserSession:
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found",
        )

    if session.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked",
        )

    refresh_expires_at = _normalize_datetime(session.refresh_expires_at)
    if refresh_expires_at is not None and refresh_expires_at <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh window has expired",
        )

    return session


def touch_user_session(db: Session, session: UserSession) -> UserSession:
    session.last_used_at = utc_now()
    db.commit()
    db.refresh(session)
    return session


def refresh_user_session(db: Session, session: UserSession) -> UserSession:
    require_refreshable_session(session)
    session.expires_at = get_expiry()
    session.last_used_at = utc_now()
    db.commit()
    db.refresh(session)
    return session


def logout_user_session(db: Session, session: UserSession) -> None:
    session.is_revoked = True
    session.last_used_at = utc_now()
    db.commit()


def list_user_sessions(db: Session, user_id: int) -> list[UserSession]:
    return (
        _get_session_query(db)
        .filter(UserSession.user_id == user_id)
        .order_by(UserSession.created_at.desc())
        .all()
    )


def revoke_user_session_by_id(db: Session, current_user_id: int, session_id: int) -> UserSession:
    session = (
        _get_session_query(db)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == current_user_id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_revoked = True
    session.last_used_at = utc_now()
    db.commit()
    db.refresh(session)
    return session


def handle_google_callback(
    db: Session,
    token: dict,
    user_info: dict,
    ip_address: str | None,
    user_agent: str | None,
):
    try:
        provider = (
            db.query(OAuthProvider)
            .filter(OAuthProvider.provider_name == "google")
            .first()
        )

        if not provider:
            provider = OAuthProvider(
                provider_name="google",
                is_active=True,
                created_at=utc_now(),
            )
            db.add(provider)
            db.flush()

        if not provider.is_active:
            raise HTTPException(status_code=400, detail="Google login is disabled")

        user, is_new_user = find_or_create_user_from_google(db, user_info)

        upsert_google_oauth_account(db, user, provider, token, user_info)
        session = create_user_session(db, user, "google", ip_address, user_agent)

        user.last_login_at = utc_now()
        if not is_new_user:
            user.is_first_login = False

        db.commit()
        db.refresh(user)
        db.refresh(session)

        return {
            "message": "Google login success",
            "is_new_user": is_new_user,
            "user": serialize_user(user),
            "session": serialize_session(session),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Google login failed") from exc
