import re
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal, engine
from app.core.security import generate_session_token, get_expiry, get_refresh_expiry, utc_now
from app.core.security import generate_refresh_token
from app.models.role import Role
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.oauth_provider import OAuthProvider
from app.models.oauth_account import OAuthAccount
from app.models.user_session import UserSession

PENDING_ROLE_NAME = "pending"
SELECTABLE_ROLE_NAMES = ("teacher", "student")


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


def bootstrap_auth_storage() -> None:
    UserProfile.__table__.create(bind=engine, checkfirst=True)

    db = SessionLocal()
    try:
        for role_name in (PENDING_ROLE_NAME, *SELECTABLE_ROLE_NAMES):
            get_or_create_role(db, role_name)
        db.commit()
    finally:
        db.close()


def get_or_create_role(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.name == role_name).first()
    if role:
        return role

    role = Role(name=role_name)
    db.add(role)
    db.flush()
    return role


def get_default_role(db: Session):
    return get_or_create_role(db, PENDING_ROLE_NAME)


def get_selectable_roles(db: Session) -> list[Role]:
    roles = []
    for role_name in SELECTABLE_ROLE_NAMES:
        roles.append(get_or_create_role(db, role_name))
    return roles


def serialize_role_option(role: Role) -> dict:
    required_fields = ["full_name", "date_of_birth", "gender"]
    if role.name == "student":
        required_fields.append("school_name")

    return {
        "id": role.id,
        "name": role.name,
        "display_name": "Teacher" if role.name == "teacher" else "Student",
        "required_fields": required_fields,
    }


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


def _calculate_age(date_of_birth: date) -> int:
    today = utc_now().date()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def get_user_profile(db: Session, user_id: int) -> UserProfile | None:
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def serialize_user_profile(profile: UserProfile | None) -> dict | None:
    if not profile:
        return None

    return {
        "date_of_birth": profile.date_of_birth,
        "age": _calculate_age(profile.date_of_birth),
        "gender": profile.gender,
        "school_name": profile.school_name,
        "onboarding_completed_at": profile.onboarding_completed_at,
    }


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


def serialize_user(user: User, profile: UserProfile | None = None) -> dict:
    role_name = user.role.name if user.role else None
    exposed_role_id = user.role_id
    exposed_role_name = role_name

    # Keep the internal "pending" role in DB, but expose it as null so FE
    # can drive the onboarding flow based on needs_onboarding.
    if role_name == PENDING_ROLE_NAME:
        exposed_role_id = None
        exposed_role_name = None

    return {
        "id": user.id,
        "role_id": exposed_role_id,
        "role_name": exposed_role_name,
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
        "needs_onboarding": role_name == PENDING_ROLE_NAME,
        "profile": serialize_user_profile(profile),
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


def build_user_payload(db: Session, user: User) -> dict:
    profile = get_user_profile(db, user.id)
    return serialize_user(user, profile)


def complete_user_onboarding(
    db: Session,
    user: User,
    role_name: str,
    full_name: str,
    date_of_birth: date,
    gender: str,
    school_name: str | None,
) -> dict:
    current_role_name = user.role.name if user.role else None
    if current_role_name and current_role_name != PENDING_ROLE_NAME:
        raise HTTPException(status_code=400, detail="Role has already been selected")

    if role_name not in SELECTABLE_ROLE_NAMES:
        raise HTTPException(status_code=400, detail="Invalid role selected")

    full_name = full_name.strip()
    school_name = school_name.strip() if school_name else None

    if not full_name:
        raise HTTPException(status_code=400, detail="full_name is required")

    if date_of_birth > utc_now().date():
        raise HTTPException(status_code=400, detail="date_of_birth cannot be in the future")

    if role_name == "student" and not school_name:
        raise HTTPException(status_code=400, detail="school_name is required for student")

    role = get_or_create_role(db, role_name)
    profile = get_user_profile(db, user.id)
    if not profile:
        profile = UserProfile(
            user_id=user.id,
            date_of_birth=date_of_birth,
            gender=gender,
            school_name=school_name if role_name == "student" else None,
            onboarding_completed_at=utc_now(),
        )
        db.add(profile)
    else:
        profile.date_of_birth = date_of_birth
        profile.gender = gender
        profile.school_name = school_name if role_name == "student" else None
        profile.onboarding_completed_at = utc_now()

    user.role_id = role.id
    user.full_name = full_name
    user.is_first_login = False
    user.updated_at = utc_now()

    db.commit()
    db.refresh(user)
    db.refresh(profile)

    return {
        "message": "Onboarding completed successfully",
        "user": serialize_user(user, profile),
    }


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
            "user": build_user_payload(db, user),
            "session": serialize_session(session),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Google login failed") from exc
