from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text_body: str
    html_body: str


def _safe_text(value: str | None, fallback: str = "") -> str:
    normalized = (value or "").strip()
    return normalized or fallback


def _minute_label(minutes: int) -> str:
    if minutes <= 1:
        return "1 phút"
    return f"{minutes} phút"


def _render_detail_rows(details: list[tuple[str, str]] | None) -> str:
    if not details:
        return ""

    rows = []
    for label, value in details:
        rows.append(
            """
            <tr>
              <td style="padding:10px 0;color:#6b7280;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;">{label}</td>
              <td style="padding:10px 0;color:#111827;font-size:15px;font-weight:700;text-align:right;">{value}</td>
            </tr>
            """.format(
                label=escape(label),
                value=escape(value),
            )
        )
    return (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        'style="margin-top:18px;border-top:1px solid #e5e7eb;border-bottom:1px solid #e5e7eb;">'
        + "".join(rows)
        + "</table>"
    )


def _render_base(
    *,
    app_name: str,
    preheader: str,
    title: str,
    content_html: str,
    footer_note: str,
    brand_logo_url: str | None = None,
) -> str:
    safe_app_name = escape(_safe_text(app_name, "QuizzVN"))
    safe_logo_url = _safe_text(brand_logo_url)
    brand_html = (
        '<img src="{url}" width="150" alt="{alt}" '
        'style="display:block;width:150px;max-width:62%;height:auto;margin:0 auto 5px;border:0;outline:none;text-decoration:none;" />'
    ).format(
        url=escape(safe_logo_url, quote=True),
        alt=safe_app_name,
    ) if safe_logo_url else (
        '<div style="margin:0 auto 12px;color:#1a73e8;font-size:24px;font-weight:600;line-height:1.2;">'
        f"{safe_app_name}</div>"
    )
    return f"""<!doctype html>
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{escape(title)}</title>
  </head>
  <body style="margin:0;padding:0;background:#ffffff;font-family:'Google Sans',Roboto,Arial,Helvetica,sans-serif;color:#202124;">
    <div style="display:none;max-height:0;overflow:hidden;color:transparent;opacity:0;">{escape(preheader)}</div>
    <div style="padding:46px 16px 28px;background:#ffffff;">
      <div style="max-width:500px;margin:0 auto;">
        <div style="background:#ffffff;border:1px solid #dadce0;border-radius:8px;padding:24px 20px 40px;text-align:center;">
          {brand_html}
          <h1 style="margin:0 0 8px;color:#202124;font-size:24px;line-height:1.32;font-weight:400;text-align:center;">{escape(title)}</h1>
          {content_html}
        </div>
        <div style="max-width:430px;margin:22px auto 0;color:#9aa0a6;font-size:12px;line-height:1.55;text-align:center;">
          {escape(footer_note)}
        </div>
      </div>
    </div>
  </body>
</html>"""


def render_otp_email(
    *,
    app_name: str,
    recipient_name: str | None,
    recipient_email: str,
    subject: str,
    title: str,
    intro: str,
    otp_code: str,
    expires_minutes: int,
    brand_logo_url: str | None = None,
) -> RenderedEmail:
    safe_name = _safe_text(recipient_name, recipient_email)
    expires_label = _minute_label(expires_minutes)
    footer_note = "Nếu bạn không thực hiện yêu cầu này, hãy bỏ qua email này."
    text_body = "\n".join(
        [
            f"Chào {safe_name},",
            "",
            intro,
            "",
            f"Mã OTP: {otp_code}",
            f"Mã này có hiệu lực trong {expires_label}.",
            "",
            footer_note,
        ]
    )
    content_html = f"""
      <p style="margin:0 0 12px;color:#3c4043;font-size:16px;line-height:1.6;text-align:center;">Chào <strong>{escape(safe_name)}</strong>,</p>
      <p style="margin:0 0 24px;color:#3c4043;font-size:16px;line-height:1.6;text-align:center;">{escape(intro)}</p>
      <div style="margin:0 auto 22px;padding:18px 20px;background:#ffffff;border:1px solid #dadce0;border-radius:14px;text-align:center;">
        <div style="color:#5f6368;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;">Mã OTP</div>
        <div style="margin-top:8px;color:#202124;font-size:32px;line-height:1;font-weight:700;letter-spacing:.20em;">{escape(otp_code)}</div>
      </div>
      <div style="margin:0 0 4px;color:#5f6368;font-size:14px;line-height:1.6;text-align:center;">
        Mã này có hiệu lực trong <strong>{escape(expires_label)}</strong>.
      </div>
    """
    html_body = _render_base(
        app_name=app_name,
        preheader=f"Mã OTP của bạn là {otp_code}",
        title=title,
        content_html=content_html,
        footer_note=footer_note,
        brand_logo_url=brand_logo_url,
    )
    return RenderedEmail(subject=subject, text_body=text_body, html_body=html_body)


def render_action_email(
    *,
    app_name: str,
    recipient_name: str | None,
    recipient_email: str,
    subject: str,
    title: str,
    intro_lines: list[str],
    button_label: str,
    button_url: str,
    expires_minutes: int | None = None,
    details: list[tuple[str, str]] | None = None,
    brand_logo_url: str | None = None,
) -> RenderedEmail:
    safe_name = _safe_text(recipient_name, recipient_email)
    avatar_initial = escape((_safe_text(safe_name, recipient_email)[:1] or "?").upper())
    safe_recipient_email = escape(recipient_email)
    footer_note = "Nếu bạn không thực hiện yêu cầu này, hãy bỏ qua email này."
    expires_line = (
        f"Liên kết này có hiệu lực trong {_minute_label(expires_minutes)}."
        if expires_minutes
        else ""
    )
    text_lines = [f"Chào {safe_name},", "", *intro_lines, ""]
    if details:
        text_lines.extend([f"{label}: {value}" for label, value in details])
        text_lines.append("")
    if expires_line:
        text_lines.extend([expires_line, ""])
    text_lines.extend([f"Mở liên kết: {button_url}", "", footer_note])
    intro_html = "".join(
        f'<p style="margin:0 0 12px;color:#3c4043;font-size:16px;line-height:1.6;text-align:center;">{escape(line)}</p>'
        for line in intro_lines
    )
    expires_html = (
        f"""
        <div style="margin:20px 0 0;color:#5f6368;font-size:13px;line-height:1.6;text-align:center;">
          Liên kết này có hiệu lực trong <strong>{escape(_minute_label(expires_minutes or 0))}</strong>.
        </div>
        """
        if expires_minutes
        else ""
    )
    content_html = f"""
      <div style="margin:0 0 26px;text-align:center;">
        <span style="display:inline-block;width:20px;height:20px;margin-right:5px;background:#2e7d32;border-radius:50%;color:#ffffff;font-size:12px;line-height:20px;font-weight:700;text-align:center;vertical-align:middle;">{avatar_initial}</span>
        <span style="display:inline-block;color:#3c4043;font-size:14px;line-height:20px;vertical-align:middle;">{safe_recipient_email}</span>
      </div>
      <div style="height:1px;background:#dadce0;margin:0 0 22px;"></div>
      {intro_html}
      {_render_detail_rows(details)}
      <div style="margin:28px 0 2px;text-align:center;">
        <a href="{escape(button_url, quote=True)}" style="display:inline-block;min-width:150px;padding:14px 28px;background:#0b57d0;border-radius:24px;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;">{escape(button_label)}</a>
      </div>
      {expires_html}
    """
    html_body = _render_base(
        app_name=app_name,
        preheader=title,
        title=title,
        content_html=content_html,
        footer_note=footer_note,
        brand_logo_url=brand_logo_url,
    )
    return RenderedEmail(subject=subject, text_body="\n".join(text_lines), html_body=html_body)


def render_notice_email(
    *,
    app_name: str,
    recipient_name: str | None,
    recipient_email: str,
    subject: str,
    title: str,
    intro_lines: list[str],
    details: list[tuple[str, str]] | None = None,
    brand_logo_url: str | None = None,
) -> RenderedEmail:
    safe_name = _safe_text(recipient_name, recipient_email)
    text_lines = [f"Chào {safe_name},", "", *intro_lines, ""]
    if details:
        text_lines.extend([f"{label}: {value}" for label, value in details])
        text_lines.append("")
    text_lines.append("Vui lòng mở trang quản trị để xử lý.")
    content_html = "".join(
        f'<p style="margin:0 0 12px;color:#3c4043;font-size:16px;line-height:1.6;text-align:center;">{escape(line)}</p>'
        for line in intro_lines
    )
    content_html = f"""
      <p style="margin:0 0 12px;color:#3c4043;font-size:16px;line-height:1.6;text-align:center;">Chào <strong>{escape(safe_name)}</strong>,</p>
      {content_html}
      {_render_detail_rows(details)}
    """
    html_body = _render_base(
        app_name=app_name,
        preheader=title,
        title=title,
        content_html=content_html,
        footer_note="Email thông báo từ hệ thống quản trị QuizzVN.",
        brand_logo_url=brand_logo_url,
    )
    return RenderedEmail(subject=subject, text_body="\n".join(text_lines), html_body=html_body)
