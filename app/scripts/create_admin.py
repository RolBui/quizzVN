import argparse
import getpass

from app.core.security import hash_password, utc_now
from app.database import SessionLocal
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import (
    ADMIN_ROLE_NAME,
    ADMINISTRATOR_ROLE_NAME,
    build_username_from_email,
    get_or_create_role,
)


def _load_models() -> None:
    import app.models.classroom  # noqa: F401
    import app.models.classroom_membership  # noqa: F401
    import app.models.exam  # noqa: F401
    import app.models.exam_attempt  # noqa: F401
    import app.models.exam_attempt_answer  # noqa: F401
    import app.models.exam_question  # noqa: F401
    import app.models.exam_question_option  # noqa: F401
    import app.models.learning_document  # noqa: F401
    import app.models.oauth_account  # noqa: F401
    import app.models.oauth_provider  # noqa: F401
    import app.models.user_profile  # noqa: F401
    import app.models.user_session  # noqa: F401


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a local admin/administrator account.")
    parser.add_argument("--email", required=True, help="Admin login email.")
    parser.add_argument("--full-name", default="Administrator", help="Admin display name.")
    parser.add_argument("--password", help="Admin password. If omitted, the script prompts securely.")
    parser.add_argument(
        "--role",
        choices=[ADMINISTRATOR_ROLE_NAME, ADMIN_ROLE_NAME],
        default=ADMINISTRATOR_ROLE_NAME,
        help="Use administrator for the owner account, admin for a delegated admin.",
    )
    return parser.parse_args()


def main() -> None:
    _load_models()
    args = _parse_args()
    email = args.email.strip().lower()
    full_name = args.full_name.strip() or "Administrator"
    password = args.password or getpass.getpass("Admin password: ")

    if not email:
        raise SystemExit("email is required")

    if len(password) < 6:
        raise SystemExit("password must be at least 6 characters")

    db = SessionLocal()
    try:
        Role.__table__.create(bind=db.get_bind(), checkfirst=True)
        User.__table__.create(bind=db.get_bind(), checkfirst=True)

        admin_role = get_or_create_role(db, args.role)
        user = db.query(User).filter(User.email == email).first()
        created = user is None

        if user is None:
            user = User(
                role_id=admin_role.id,
                full_name=full_name,
                username=build_username_from_email(db, email),
                email=email,
                password_hash=hash_password(password),
                auth_type="local",
                email_verified=True,
                status="active",
                is_first_login=False,
                max_exam_create=50,
                max_document_create=50,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            db.add(user)
        else:
            user.role_id = admin_role.id
            user.full_name = full_name
            user.password_hash = hash_password(password)
            user.auth_type = "mixed" if user.auth_type == "oauth" else "local"
            user.email_verified = True
            user.status = "active"
            user.is_first_login = False
            user.updated_at = utc_now()

        db.commit()
        db.refresh(user)

        action = "created" if created else "updated"
        print(f"Admin {action}: {user.email} (user_id={user.id}, role={args.role})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
