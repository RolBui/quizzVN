from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.routers.admin_router import _admin_invitation_accept_html
from app.services.email_templates import render_action_email, render_otp_email

router = APIRouter(prefix="/dev", tags=["Dev"])


def _is_local_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def _require_email_preview_enabled() -> None:
    if settings.DEBUG or _is_local_url(settings.BACKEND_URL):
        return
    raise HTTPException(status_code=404, detail="Not found")


def _build_preview_invitation_url(email: str) -> str:
    query_string = urlencode({"token": "preview-token", "email": email})
    return f"{settings.ADMIN_INVITATION_BASE_URL}{settings.FRONTEND_ADMIN_INVITATION_PATH}?{query_string}"


@router.get("/email-preview/admin-invitation", response_class=HTMLResponse, include_in_schema=False)
def preview_admin_invitation_email(
    email: str = Query("th1boyz123@gmail.com"),
    name: str = Query("Thanh"),
) -> HTMLResponse:
    _require_email_preview_enabled()
    rendered = render_action_email(
        app_name=settings.EMAIL_FROM_NAME or settings.APP_NAME,
        recipient_name=name,
        recipient_email=email,
        subject=f"Mời xác thực tài khoản quản trị {settings.APP_NAME}",
        title="Mời xác thực tài khoản quản trị",
        intro_lines=[
            f"Bạn được mời gửi yêu cầu tài khoản quản trị cho {settings.APP_NAME}.",
            "Bấm nút bên dưới để điền thông tin và xác thực OTP.",
        ],
        button_label="Mở form xác thực",
        button_url=_build_preview_invitation_url(email),
        brand_logo_url=settings.EMAIL_BRAND_LOGO_URL,
    )
    return HTMLResponse(rendered.html_body)


@router.get("/email-preview/admin-invitation-otp", response_class=HTMLResponse, include_in_schema=False)
def preview_admin_invitation_otp_email(
    email: str = Query("th1boyz123@gmail.com"),
    name: str = Query("Thanh Nhân Bùi"),
    otp: str = Query("095215"),
) -> HTMLResponse:
    _require_email_preview_enabled()
    rendered = render_otp_email(
        app_name=settings.EMAIL_FROM_NAME or settings.APP_NAME,
        recipient_name=name,
        recipient_email=email,
        subject=f"Mã OTP quản trị {settings.APP_NAME}",
        title="Mã OTP quản trị",
        intro="Sử dụng mã OTP bên dưới để xác thực yêu cầu tài khoản quản trị.",
        otp_code=otp,
        expires_minutes=settings.ADMIN_INVITATION_OTP_EXPIRE_MINUTES,
        brand_logo_url=settings.EMAIL_BRAND_LOGO_URL,
    )
    return HTMLResponse(rendered.html_body)


@router.get("/form-preview/admin-invitation", response_class=HTMLResponse, include_in_schema=False)
def preview_admin_invitation_form(
    email: str = Query("th1boyz123@gmail.com"),
    name: str = Query("Thanh"),
) -> HTMLResponse:
    _require_email_preview_enabled()
    return HTMLResponse(
        _admin_invitation_accept_html(
            "preview-token",
            email,
            full_name=name,
            phone="0901234567",
            date_of_birth="2000-01-01",
            gender="male",
        )
    )


@router.get("/form-preview/admin-invitation-otp", response_class=HTMLResponse, include_in_schema=False)
def preview_admin_invitation_otp_form(
    email: str = Query("th1boyz123@gmail.com"),
    name: str = Query("Thanh"),
    invalid_otp: bool = Query(False),
) -> HTMLResponse:
    _require_email_preview_enabled()
    return HTMLResponse(
        _admin_invitation_accept_html(
            "preview-token",
            email,
            step="otp",
            error="Mã opt không đúng , vui lòng nhập lại!" if invalid_otp else "",
            full_name=name,
            phone="0901234567",
            date_of_birth="2000-01-01",
            gender="male",
        )
    )


@router.get("/form-preview/admin-invitation-success", response_class=HTMLResponse, include_in_schema=False)
def preview_admin_invitation_success_form(
    email: str = Query("th1boyz123@gmail.com"),
) -> HTMLResponse:
    _require_email_preview_enabled()
    return HTMLResponse(
        _admin_invitation_accept_html(
            "preview-token",
            email,
            step="success",
            success="Đã xác thực OTP. Yêu cầu của bạn đang chờ Administrator duyệt.",
        )
    )
