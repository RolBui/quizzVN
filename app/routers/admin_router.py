from html import escape

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_administrator
from app.schemas.admin import (
    AdminAccountListResponse,
    AdminAccountResponse,
    AdminClassOverviewResponse,
    AdminCrmOverviewResponse,
    AdminDocumentOverviewResponse,
    AdminDocumentResponse,
    AdminExamOverviewResponse,
    AdminInvitationListResponse,
    AdminInvitationResponse,
    AdminStudentDetailResponse,
    AdminStudentOverviewResponse,
    AdminTeacherDetailResponse,
    AdminTeacherOverviewResponse,
    ApproveAdminInvitationRequest,
    ApproveAdminInvitationResponse,
    CreateAdminAccountRequest,
    CreateAdminInvitationRequest,
    RejectAdminInvitationRequest,
    ResetAdminUserPasswordRequest,
    SendAdminInvitationOtpRequest,
    UpdateAdminPermissionsRequest,
    UpdateAdminUserProfileRequest,
    VerifyAdminInvitationOtpRequest,
)
from app.schemas.analytics import AdminWebRealtimeResponse, AdminWebTrafficOverviewResponse
from app.schemas.common import MessageResponse
from app.services.admin_service import (
    create_admin_account,
    create_admin_invitation,
    create_admin_uploaded_document,
    delete_admin_account,
    delete_admin_exam,
    delete_admin_student,
    delete_admin_teacher,
    approve_admin_invitation,
    get_admin_classes_overview,
    get_admin_crm_overview,
    get_admin_documents_overview,
    get_admin_exams_overview,
    get_admin_student_detail,
    get_admin_students_overview,
    get_admin_teacher_detail,
    get_admin_teachers_overview,
    list_admin_invitations,
    list_admin_accounts,
    reject_admin_invitation,
    reset_admin_student_password,
    reset_admin_teacher_password,
    send_admin_invitation_otp,
    submit_admin_invitation_otp,
    update_admin_permissions,
    update_admin_student_profile,
    update_admin_teacher_profile,
)
from app.services.analytics_service import get_web_realtime_overview, get_web_traffic_overview

router = APIRouter(prefix="/admin", tags=["Admin"])


def _admin_invitation_accept_html(
    token: str,
    email: str,
    *,
    step: str = "profile",
    error: str | None = None,
    success: str | None = None,
    notice: str | None = None,
    full_name: str = "",
    phone: str = "",
    date_of_birth: str = "",
    gender: str = "",
) -> str:
    safe_token = escape(token or "", quote=True)
    safe_email = escape(email or "", quote=True)
    safe_full_name = escape(full_name or "", quote=True)
    safe_phone = escape(phone or "", quote=True)
    safe_date_of_birth = escape(date_of_birth or "", quote=True)
    safe_gender = escape(gender or "", quote=True)
    error_html = (
        f'<div class="alert alert-error">{escape(error)}</div>'
        if error
        else ""
    )
    success_html = (
        f'<div class="alert alert-success">{escape(success)}</div>'
        if success
        else ""
    )
    notice_html = (
        f'<div class="alert alert-info">{escape(notice)}</div>'
        if notice
        else ""
    )
    form_html = ""
    step_title = "Thông tin người được mời"
    step_description = "Điền thông tin cá nhân để gửi yêu cầu cấp quyền quản trị viên."

    if success:
        step_title = "Yêu cầu đã được gửi"
        step_description = "Administrator sẽ kiểm tra và duyệt tài khoản của bạn."
    elif step == "otp":
        step_title = "Xác thực mã OTP"
        step_description = "Bấm Gửi mã để nhận OTP, sau đó nhập 6 chữ số trong email để hoàn tất gửi yêu cầu."
        form_html = f"""
        <form method="post" action="/admin/invitations/accept">
          <input type="hidden" name="token" value="{safe_token}" />
          <input type="hidden" name="email" value="{safe_email}" />
          <input type="hidden" name="full_name" value="{safe_full_name}" />
          <input type="hidden" name="phone" value="{safe_phone}" />
          <input type="hidden" name="date_of_birth" value="{safe_date_of_birth}" />
          <input type="hidden" name="gender" value="{safe_gender}" />
          <div class="email-action">
            <div>
              <span>Email</span>
              <strong>{safe_email}</strong>
            </div>
            <button class="send-code-button" type="submit" formaction="/admin/invitations/accept/send-code" formnovalidate>Gửi mã</button>
          </div>
          <div class="otp-row" aria-label="Nhập mã OTP gồm 6 số">
            <input name="otp_digit_1" inputmode="numeric" pattern="[0-9]" maxlength="1" autocomplete="one-time-code" required data-otp-input />
            <input name="otp_digit_2" inputmode="numeric" pattern="[0-9]" maxlength="1" required data-otp-input />
            <input name="otp_digit_3" inputmode="numeric" pattern="[0-9]" maxlength="1" required data-otp-input />
            <input name="otp_digit_4" inputmode="numeric" pattern="[0-9]" maxlength="1" required data-otp-input />
            <input name="otp_digit_5" inputmode="numeric" pattern="[0-9]" maxlength="1" required data-otp-input />
            <input name="otp_digit_6" inputmode="numeric" pattern="[0-9]" maxlength="1" required data-otp-input />
          </div>
          <button type="submit">Xác thực OTP</button>
          <button class="button-secondary" type="submit" formaction="/admin/invitations/accept/edit-profile" formnovalidate>Quay lại chỉnh thông tin</button>
        </form>
        """
    else:
        gender_options = "".join(
            f'<option value="{value}" {"selected" if safe_gender == value else ""}>{label}</option>'
            for value, label in (
                ("", "Chọn giới tính"),
                ("male", "Nam"),
                ("female", "Nữ"),
                ("other", "Khác"),
            )
        )
        form_html = f"""
        <form method="post" action="/admin/invitations/accept/profile">
          <input type="hidden" name="token" value="{safe_token}" />
          <input type="hidden" name="email" value="{safe_email}" />
          <label>
            Email
            <input name="display_email" value="{safe_email}" disabled />
          </label>
          <label>
            Họ tên
            <input name="full_name" value="{safe_full_name}" placeholder="Nhập họ tên đầy đủ" required />
          </label>
          <label>
            Số điện thoại
            <input name="phone" value="{safe_phone}" inputmode="tel" placeholder="Ví dụ: 0901234567" required />
          </label>
          <label>
            Ngày sinh
            <input name="date_of_birth" value="{safe_date_of_birth}" type="date" required />
          </label>
          <label>
            Giới tính
            <select name="gender" required>
              {gender_options}
            </select>
          </label>
          <button type="submit">Tiếp tục</button>
        </form>
        """

    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/png" href="/favicon.ico" />
  <title>Lời mời quản trị viên</title>
  <style>
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f4f7fb;
      color: #111827;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      padding: 20px;
    }}
    main {{
      width: min(480px, 100%);
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 3px;
      padding: 24px;
      box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      line-height: 1.15;
    }}
    p {{
      margin: 0 0 16px;
      color: #64748b;
      font-size: 14px;
      line-height: 1.5;
    }}
    label {{
      display: block;
      margin-top: 10px;
      font-weight: 700;
      font-size: 13px;
    }}
    input,
    select {{
      width: 100%;
      height: 42px;
      margin-top: 6px;
      border: 1px solid #cbd5e1;
      border-radius: 3px;
      padding: 0 10px;
      font-size: 14px;
      background: white;
      color: #0f172a;
      outline: none;
      transition: border-color 0.18s ease, box-shadow 0.18s ease;
    }}
    input:focus,
    select:focus {{
      border-color: #6366f1;
      box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.14);
    }}
    input:disabled {{
      background: #f8fafc;
      color: #475569;
    }}
    .summary,
    .email-action {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 14px 0 16px;
      border: 1px solid #e2e8f0;
      border-radius: 3px;
      background: #f8fafc;
      padding: 10px 12px;
      color: #64748b;
      font-size: 14px;
    }}
    .summary strong,
    .email-action strong {{
      display: block;
      margin-top: 4px;
      color: #0f172a;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    .send-code-button {{
      width: auto;
      min-width: 104px;
      height: 36px;
      margin: 0;
      padding: 0 14px;
      border-radius: 3px;
      font-size: 13px;
      box-shadow: none;
      flex: 0 0 auto;
    }}
    .otp-row {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}
    .otp-row input {{
      height: 48px;
      margin: 0;
      padding: 0;
      text-align: center;
      font-size: 22px;
      font-weight: 800;
      border-radius: 3px;
    }}
    button {{
      width: 100%;
      height: 42px;
      margin-top: 14px;
      border: 0;
      border-radius: 3px;
      background: linear-gradient(135deg, #2563eb, #9333ea);
      color: white;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: none;
    }}
    .button-secondary {{
      margin-top: 10px;
      border: 1px solid #cbd5e1;
      background: #fff;
      color: #334155;
      box-shadow: none;
    }}
    .alert {{
      border-radius: 3px;
      margin: 12px 0;
      padding: 10px 12px;
      line-height: 1.45;
    }}
    .alert-error {{
      background: #fef2f2;
      color: #991b1b;
      border: 1px solid #fecaca;
    }}
    .alert-success {{
      background: #ecfdf5;
      color: #065f46;
      border: 1px solid #a7f3d0;
    }}
    .alert-info {{
      background: #eff6ff;
      color: #1e40af;
      border: 1px solid #bfdbfe;
    }}
    @media (max-width: 520px) {{
      main {{
        padding: 18px;
      }}
      .otp-row {{
        gap: 7px;
      }}
      .otp-row input {{
        height: 50px;
        font-size: 20px;
      }}
      .email-action {{
        align-items: flex-start;
        flex-direction: column;
      }}
      .send-code-button {{
        width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>{step_title}</h1>
    <p>{step_description}</p>
    {error_html}
    {success_html}
    {notice_html}
    {form_html}
  </main>
  <script>
    const otpInputs = Array.from(document.querySelectorAll("[data-otp-input]"));
    otpInputs.forEach((input, index) => {{
      input.addEventListener("input", () => {{
        input.value = input.value.replace(/\\D/g, "").slice(0, 1);
        if (input.value && otpInputs[index + 1]) {{
          otpInputs[index + 1].focus();
        }}
      }});
      input.addEventListener("keydown", (event) => {{
        if (event.key === "Backspace" && !input.value && otpInputs[index - 1]) {{
          otpInputs[index - 1].focus();
        }}
      }});
      input.addEventListener("paste", (event) => {{
        event.preventDefault();
        const value = event.clipboardData.getData("text").replace(/\\D/g, "").slice(0, otpInputs.length);
        value.split("").forEach((digit, digitIndex) => {{
          if (otpInputs[digitIndex]) {{
            otpInputs[digitIndex].value = digit;
          }}
        }});
        const nextIndex = Math.min(value.length, otpInputs.length - 1);
        otpInputs[nextIndex]?.focus();
      }});
    }});
    otpInputs[0]?.focus();
  </script>
</body>
</html>"""


@router.get("/invitations/accept", response_class=HTMLResponse)
def get_admin_invitation_accept_form(
    token: str = Query(""),
    email: str = Query(""),
) -> HTMLResponse:
    return HTMLResponse(_admin_invitation_accept_html(token, email))


@router.post("/invitations/accept/profile", response_class=HTMLResponse)
def post_admin_invitation_profile_form(
    token: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(...),
    date_of_birth: str = Form(...),
    gender: str = Form(...),
) -> HTMLResponse:
    if not full_name.strip():
        return HTMLResponse(
            _admin_invitation_accept_html(
                token,
                email,
                error="Vui lòng nhập họ tên.",
                full_name=full_name,
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
            ),
            status_code=400,
        )
    if not phone.strip():
        return HTMLResponse(
            _admin_invitation_accept_html(
                token,
                email,
                error="Vui lòng nhập số điện thoại.",
                full_name=full_name,
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
            ),
            status_code=400,
        )
    if not date_of_birth.strip():
        return HTMLResponse(
            _admin_invitation_accept_html(
                token,
                email,
                error="Vui lòng chọn ngày sinh.",
                full_name=full_name,
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
            ),
            status_code=400,
        )
    if gender not in {"male", "female", "other"}:
        return HTMLResponse(
            _admin_invitation_accept_html(
                token,
                email,
                error="Vui lòng chọn giới tính.",
                full_name=full_name,
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
            ),
            status_code=400,
        )

    return HTMLResponse(
        _admin_invitation_accept_html(
            token,
            email,
            step="otp",
            full_name=full_name,
            phone=phone,
            date_of_birth=date_of_birth,
            gender=gender,
        )
    )


@router.post("/invitations/accept/edit-profile", response_class=HTMLResponse)
def post_admin_invitation_edit_profile_form(
    token: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(""),
    phone: str = Form(""),
    date_of_birth: str = Form(""),
    gender: str = Form(""),
) -> HTMLResponse:
    return HTMLResponse(
        _admin_invitation_accept_html(
            token,
            email,
            full_name=full_name,
            phone=phone,
            date_of_birth=date_of_birth,
            gender=gender,
        )
    )


@router.post("/invitations/accept/send-code", response_class=HTMLResponse)
def post_admin_invitation_send_code_form(
    token: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(...),
    date_of_birth: str = Form(...),
    gender: str = Form(...),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    try:
        send_admin_invitation_otp(
            db,
            token,
            email,
            full_name,
            phone,
            date_of_birth,
            gender,
        )
    except HTTPException as exc:
        return HTMLResponse(
            _admin_invitation_accept_html(
                token,
                email,
                step="otp",
                error=str(exc.detail),
                full_name=full_name,
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
            ),
            status_code=exc.status_code,
        )

    return HTMLResponse(
        _admin_invitation_accept_html(
            token,
            email,
            step="otp",
            notice="Đã gửi mã OTP về email. Vui lòng kiểm tra hộp thư đến hoặc thư rác.",
            full_name=full_name,
            phone=phone,
            date_of_birth=date_of_birth,
            gender=gender,
        )
    )


@router.post("/invitations/accept", response_class=HTMLResponse)
def post_admin_invitation_accept_form(
    token: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(...),
    date_of_birth: str = Form(...),
    gender: str = Form(...),
    otp_digit_1: str = Form(...),
    otp_digit_2: str = Form(...),
    otp_digit_3: str = Form(...),
    otp_digit_4: str = Form(...),
    otp_digit_5: str = Form(...),
    otp_digit_6: str = Form(...),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    otp_code = "".join(
        [
            otp_digit_1,
            otp_digit_2,
            otp_digit_3,
            otp_digit_4,
            otp_digit_5,
            otp_digit_6,
        ]
    )
    try:
        submit_admin_invitation_otp(
            db,
            token,
            email,
            otp_code,
            full_name,
            phone,
            date_of_birth,
            gender,
        )
    except HTTPException as exc:
        return HTMLResponse(
            _admin_invitation_accept_html(
                token,
                email,
                step="otp",
                error=str(exc.detail),
                full_name=full_name,
                phone=phone,
                date_of_birth=date_of_birth,
                gender=gender,
            ),
            status_code=exc.status_code,
        )

    return HTMLResponse(
        _admin_invitation_accept_html(
            token,
            email,
            step="success",
            success="Đã xác thực OTP. Yêu cầu của bạn đang chờ Administrator duyệt.",
        )
    )


@router.get("/crm/overview", response_model=AdminCrmOverviewResponse)
def get_crm_overview(
    period: str = Query("7d"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminCrmOverviewResponse:
    _ = current_admin
    return get_admin_crm_overview(db, period)


@router.get("/analytics/traffic", response_model=AdminWebTrafficOverviewResponse)
def get_analytics_traffic(
    period: str = Query("7d"),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminWebTrafficOverviewResponse:
    _ = current_admin
    return get_web_traffic_overview(db, period)


@router.get("/analytics/realtime", response_model=AdminWebRealtimeResponse)
def get_analytics_realtime(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminWebRealtimeResponse:
    _ = current_admin
    return get_web_realtime_overview(db)


@router.get("/teachers", response_model=AdminTeacherOverviewResponse)
def get_teachers_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminTeacherOverviewResponse:
    _ = current_admin
    return get_admin_teachers_overview(db)


@router.get("/teachers/{teacher_id}", response_model=AdminTeacherDetailResponse)
def get_teacher_detail(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminTeacherDetailResponse:
    _ = current_admin
    return get_admin_teacher_detail(db, teacher_id)


@router.put("/teachers/{teacher_id}", response_model=AdminTeacherDetailResponse)
def put_teacher_profile(
    teacher_id: int,
    payload: UpdateAdminUserProfileRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminTeacherDetailResponse:
    return update_admin_teacher_profile(
        db,
        current_administrator,
        teacher_id,
        payload.full_name,
        payload.email,
        payload.phone,
        payload.avatar_url,
        payload.date_of_birth,
        payload.gender,
        payload.school_name,
        payload.status,
    )


@router.post("/teachers/{teacher_id}/reset-password", response_model=MessageResponse)
def post_teacher_password_reset(
    teacher_id: int,
    payload: ResetAdminUserPasswordRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return reset_admin_teacher_password(db, current_administrator, teacher_id, payload.password)


@router.get("/students", response_model=AdminStudentOverviewResponse)
def get_students_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminStudentOverviewResponse:
    _ = current_admin
    return get_admin_students_overview(db)


@router.get("/students/{student_id}", response_model=AdminStudentDetailResponse)
def get_student_detail(
    student_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminStudentDetailResponse:
    _ = current_admin
    return get_admin_student_detail(db, student_id)


@router.put("/students/{student_id}", response_model=AdminStudentDetailResponse)
def put_student_profile(
    student_id: int,
    payload: UpdateAdminUserProfileRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminStudentDetailResponse:
    return update_admin_student_profile(
        db,
        current_administrator,
        student_id,
        payload.full_name,
        payload.email,
        payload.phone,
        payload.avatar_url,
        payload.date_of_birth,
        payload.gender,
        payload.school_name,
        payload.status,
    )


@router.post("/students/{student_id}/reset-password", response_model=MessageResponse)
def post_student_password_reset(
    student_id: int,
    payload: ResetAdminUserPasswordRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return reset_admin_student_password(db, current_administrator, student_id, payload.password)


@router.get("/classes", response_model=AdminClassOverviewResponse)
def get_classes_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminClassOverviewResponse:
    _ = current_admin
    return get_admin_classes_overview(db)


@router.get("/exams", response_model=AdminExamOverviewResponse)
def get_exams_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminExamOverviewResponse:
    _ = current_admin
    return get_admin_exams_overview(db)


@router.delete("/exams/{exam_id}", response_model=MessageResponse)
def delete_exam_route(
    exam_id: int,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return delete_admin_exam(db, current_administrator, exam_id)


@router.get("/documents", response_model=AdminDocumentOverviewResponse)
def get_documents_overview(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminDocumentOverviewResponse:
    _ = current_admin
    return get_admin_documents_overview(db)


@router.post("/documents", response_model=AdminDocumentResponse)
def post_admin_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    summary: str | None = Form(None),
    scope: str = Form("system"),
    classroom_id: int | None = Form(None),
    is_published: bool = Form(True),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminDocumentResponse:
    return create_admin_uploaded_document(
        db,
        current_admin,
        title,
        summary,
        file,
        scope,
        classroom_id,
        is_published,
    )


@router.get("/users", response_model=AdminAccountListResponse)
def get_admin_accounts(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminAccountListResponse:
    return list_admin_accounts(db, current_admin)


@router.get("/invitations", response_model=AdminInvitationListResponse)
def get_admin_invitations(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
) -> AdminInvitationListResponse:
    return list_admin_invitations(db, current_admin, status)


@router.post("/invitations", response_model=AdminInvitationResponse)
def post_admin_invitation(
    payload: CreateAdminInvitationRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminInvitationResponse:
    return create_admin_invitation(db, current_administrator, payload.email)


@router.post("/invitations/send-otp", response_model=AdminInvitationResponse)
def post_admin_invitation_send_otp(
    payload: SendAdminInvitationOtpRequest,
    db: Session = Depends(get_db),
) -> AdminInvitationResponse:
    return send_admin_invitation_otp(
        db,
        payload.token,
        payload.email,
        payload.full_name,
        payload.phone,
        payload.date_of_birth,
        payload.gender,
    )


@router.post("/invitations/verify-otp", response_model=AdminInvitationResponse)
def post_admin_invitation_otp(
    payload: VerifyAdminInvitationOtpRequest,
    db: Session = Depends(get_db),
) -> AdminInvitationResponse:
    return submit_admin_invitation_otp(
        db,
        payload.token,
        payload.email,
        payload.otp_code,
        payload.full_name,
        payload.phone,
        payload.date_of_birth,
        payload.gender,
    )


@router.post("/invitations/{invitation_id}/approve", response_model=ApproveAdminInvitationResponse)
def post_admin_invitation_approval(
    invitation_id: int,
    payload: ApproveAdminInvitationRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> ApproveAdminInvitationResponse:
    return approve_admin_invitation(db, current_administrator, invitation_id, payload.permissions)


@router.post("/invitations/{invitation_id}/reject", response_model=AdminInvitationResponse)
def post_admin_invitation_rejection(
    invitation_id: int,
    payload: RejectAdminInvitationRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminInvitationResponse:
    return reject_admin_invitation(db, current_administrator, invitation_id, payload.reason)


@router.post("/users", response_model=AdminAccountResponse)
def post_admin_account(
    payload: CreateAdminAccountRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminAccountResponse:
    _ = current_administrator
    return create_admin_account(db, payload.full_name, payload.email, payload.password)


@router.put("/users/{user_id}/permissions", response_model=AdminAccountResponse)
def put_admin_permissions(
    user_id: int,
    payload: UpdateAdminPermissionsRequest,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> AdminAccountResponse:
    return update_admin_permissions(db, current_administrator, user_id, payload.permissions)


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_admin_account_route(
    user_id: int,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return delete_admin_account(db, current_administrator, user_id)


@router.delete("/teachers/{teacher_id}", response_model=MessageResponse)
def delete_admin_teacher_route(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return delete_admin_teacher(db, current_administrator, teacher_id)


@router.delete("/students/{student_id}", response_model=MessageResponse)
def delete_admin_student_route(
    student_id: int,
    db: Session = Depends(get_db),
    current_administrator=Depends(get_current_administrator),
) -> MessageResponse:
    return delete_admin_student(db, current_administrator, student_id)
