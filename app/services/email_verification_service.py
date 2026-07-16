import logging
import secrets
import smtplib
import string
from datetime import timedelta
from email.message import EmailMessage
from urllib.parse import urlencode

from fastapi import HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, utc_now, verify_password
from app.models.email_verification_otp import EmailVerificationOtp
from app.models.user import User
from app.services.email_templates import render_action_email, render_otp_email

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


def _build_email_message_content(
    recipient_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> EmailMessage:
    message = EmailMessage()
    from_name = settings.EMAIL_FROM_NAME
    from_address = settings.EMAIL_FROM_ADDRESS or "no-reply@example.com"
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_address}>"
    message["To"] = recipient_email
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")
    return message


def _build_plain_email_message(recipient_email: str, subject: str, text_body: str) -> EmailMessage:
    return _build_email_message_content(recipient_email, subject, text_body)


def _build_email_message(recipient_email: str, recipient_name: str, verify_url: str) -> EmailMessage:
    app_name = settings.APP_NAME
    rendered = render_action_email(
        app_name=settings.EMAIL_FROM_NAME or app_name,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        subject=f"Xác thực email cho {app_name}",
        title="Xác thực email",
        intro_lines=[
            f"Vui lòng xác thực địa chỉ email đăng ký tại {app_name}.",
            "Bấm nút bên dưới để hoàn tất xác thực.",
        ],
        button_label="Xác thực email",
        button_url=verify_url,
        expires_minutes=settings.EMAIL_VERIFICATION_EXPIRE_HOURS * 60,
        brand_logo_url=settings.EMAIL_BRAND_LOGO_URL,
    )
    return _build_email_message_content(
        recipient_email,
        rendered.subject,
        rendered.text_body,
        rendered.html_body,
    )


def _generate_email_verification_otp() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


def _build_email_otp_message(recipient_email: str, recipient_name: str, otp_code: str) -> EmailMessage:
    app_name = settings.APP_NAME
    rendered = render_otp_email(
        app_name=settings.EMAIL_FROM_NAME or app_name,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        subject=f"Mã xác thực email {app_name}",
        title="Mã xác thực email",
        intro=f"Sử dụng mã OTP bên dưới để xác thực email tại {app_name}.",
        otp_code=otp_code,
        expires_minutes=settings.EMAIL_VERIFICATION_OTP_EXPIRE_MINUTES,
        brand_logo_url=settings.EMAIL_BRAND_LOGO_URL,
    )
    return _build_email_message_content(
        recipient_email,
        rendered.subject,
        rendered.text_body,
        rendered.html_body,
    )


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
    send_email(recipient_email, subject, text_body)


def send_email(
    recipient_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    message = _build_email_message_content(recipient_email, subject, text_body, html_body)

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


def send_email_verification_otp(db: Session, user: User) -> None:
    if user.email_verified:
        return

    otp_code = _generate_email_verification_otp()
    now = utc_now()
    verification_otp = (
        db.query(EmailVerificationOtp)
        .filter(EmailVerificationOtp.user_id == user.id)
        .first()
    )

    if verification_otp:
        verification_otp.otp_hash = hash_password(otp_code)
        verification_otp.expires_at = now + timedelta(minutes=settings.EMAIL_VERIFICATION_OTP_EXPIRE_MINUTES)
        verification_otp.attempt_count = 0
        verification_otp.consumed_at = None
        verification_otp.updated_at = now
    else:
        verification_otp = EmailVerificationOtp(
            user_id=user.id,
            otp_hash=hash_password(otp_code),
            expires_at=now + timedelta(minutes=settings.EMAIL_VERIFICATION_OTP_EXPIRE_MINUTES),
            attempt_count=0,
            created_at=now,
            updated_at=now,
        )
        db.add(verification_otp)

    db.commit()

    message = _build_email_otp_message(user.email, user.full_name, otp_code)
    if settings.EMAIL_DELIVERY_MODE == "smtp":
        _send_via_smtp(message)
        logger.info("Email verification OTP sent to %s", user.email)
        return

    logger.info("EMAIL_DELIVERY_MODE=%s", settings.EMAIL_DELIVERY_MODE)
    logger.info("Email verification OTP sent to %s", user.email)
    plain_part = message.get_body(preferencelist=("plain",))
    logger.info(
        "Email to %s subject=%s\n%s",
        user.email,
        message["Subject"],
        plain_part.get_content() if plain_part else "",
    )


def verify_email_otp(db: Session, user: User, otp_code: str) -> dict:
    if user.email_verified:
        return {"message": "Email is already verified", "user": user}

    normalized_otp_code = otp_code.strip()
    if not normalized_otp_code.isdigit() or len(normalized_otp_code) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_otp_invalid",
        )

    verification_otp = (
        db.query(EmailVerificationOtp)
        .filter(EmailVerificationOtp.user_id == user.id)
        .first()
    )

    if not verification_otp or verification_otp.consumed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_otp_not_sent",
        )

    expires_at = verification_otp.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=utc_now().tzinfo)

    if expires_at <= utc_now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_otp_expired",
        )

    if verification_otp.attempt_count >= settings.EMAIL_VERIFICATION_OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_otp_attempt_limit_exceeded",
        )

    if not verify_password(normalized_otp_code, verification_otp.otp_hash):
        verification_otp.attempt_count += 1
        verification_otp.updated_at = utc_now()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="verification_otp_invalid",
        )

    now = utc_now()
    user.email_verified = True
    user.updated_at = now
    verification_otp.consumed_at = now
    verification_otp.updated_at = now
    db.commit()
    db.refresh(user)
    from app.services.billing_service import grant_teacher_welcome_qc

    grant_teacher_welcome_qc(db, user)
    return {"message": "Email verified successfully", "user": user}


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
    from app.services.billing_service import grant_teacher_welcome_qc

    grant_teacher_welcome_qc(db, user)
    return "verified"
