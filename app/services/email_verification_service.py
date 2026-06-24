import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

from fastapi import HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)
EMAIL_VERIFICATION_SALT = "email-verification"


def _verification_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.EMAIL_VERIFICATION_SECRET)


def build_email_verification_token(user: User) -> str:
    serializer = _verification_serializer()
    return serializer.dumps(
        {
            "purpose": EMAIL_VERIFICATION_SALT,
            "user_id": user.id,
            "email": user.email,
        },
        salt=EMAIL_VERIFICATION_SALT,
    )


def build_backend_email_verification_url(token: str) -> str:
    query_string = urlencode({"token": token})
    return f"{settings.BACKEND_URL}/auth/verify-email?{query_string}"


def build_frontend_email_verification_redirect_url(status_value: str) -> str:
    query_string = urlencode({"status": status_value})
    return f"{settings.FRONTEND_URL}{settings.FRONTEND_EMAIL_VERIFICATION_PATH}?{query_string}"


def _build_plain_email_message(recipient_email: str, subject: str, text_body: str) -> EmailMessage:
    message = EmailMessage()
    from_name = settings.EMAIL_FROM_NAME
    from_address = settings.EMAIL_FROM_ADDRESS or "no-reply@example.com"
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_address}>"
    message["To"] = recipient_email
    message.set_content(text_body)
    return message


def _build_email_message(recipient_email: str, recipient_name: str, verify_url: str) -> EmailMessage:
    app_name = settings.APP_NAME
    subject = f"Verify your email for {app_name}"
    safe_name = recipient_name.strip() or recipient_email
    text_body = (
        f"Hi {safe_name},\n\n"
        f"Please verify your email address for {app_name} by opening the link below:\n\n"
        f"{verify_url}\n\n"
        f"This link expires in {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hour(s).\n\n"
        "If you did not create this account, you can ignore this email."
    )
    return _build_plain_email_message(recipient_email, subject, text_body)


def _send_via_smtp(message: EmailMessage) -> None:
    if not settings.SMTP_HOST or not settings.EMAIL_FROM_ADDRESS:
        raise RuntimeError("SMTP email delivery is not fully configured")

    if settings.SMTP_USE_SSL:
        with smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        ) as smtp:
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    ) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)


def send_plain_email(recipient_email: str, subject: str, text_body: str) -> None:
    message = _build_plain_email_message(recipient_email, subject, text_body)

    if settings.EMAIL_DELIVERY_MODE == "smtp":
        _send_via_smtp(message)
        logger.info("Email sent to %s with subject %s", recipient_email, subject)
        return

    logger.info("EMAIL_DELIVERY_MODE=%s", settings.EMAIL_DELIVERY_MODE)
    logger.info("Email to %s subject=%s\n%s", recipient_email, subject, text_body)


def send_email_verification_email(user: User) -> str:
    token = build_email_verification_token(user)
    verify_url = build_backend_email_verification_url(token)
    message = _build_email_message(user.email, user.full_name, verify_url)

    if settings.EMAIL_DELIVERY_MODE == "smtp":
        _send_via_smtp(message)
        logger.info("Verification email sent to %s", user.email)
        return verify_url

    logger.info("EMAIL_DELIVERY_MODE=%s", settings.EMAIL_DELIVERY_MODE)
    logger.info("Email verification link for %s: %s", user.email, verify_url)
    return verify_url


def verify_email_token(db: Session, token: str) -> str:
    serializer = _verification_serializer()

    try:
        payload = serializer.loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=settings.EMAIL_VERIFICATION_EXPIRE_HOURS * 60 * 60,
        )
    except SignatureExpired as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_token_expired",
        ) from exc
    except BadSignature as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_token_invalid",
        ) from exc

    if payload.get("purpose") != EMAIL_VERIFICATION_SALT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_token_invalid",
        )

    user_id = payload.get("user_id")
    email = payload.get("email")
    user = db.query(User).filter(User.id == user_id).first()

    if not user or user.email != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_token_invalid",
        )

    if user.email_verified:
        return "already_verified"

    user.email_verified = True
    db.commit()
    db.refresh(user)
    return "verified"
