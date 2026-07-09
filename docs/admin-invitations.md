# Admin invitation email OTP flow

This flow replaces direct admin creation when the administrator wants invitees to verify email ownership first.

## Environment

```env
ADMIN_INVITATION_BASE_URL=http://localhost:8000
FRONTEND_ADMIN_INVITATION_PATH=/admin/invitations/accept
ADMIN_INVITATION_LINK_EXPIRE_HOURS=24
ADMIN_INVITATION_OTP_EXPIRE_MINUTES=15
ADMIN_INVITATION_OTP_MAX_ATTEMPTS=5
```

The invitation email links to:

```text
{ADMIN_INVITATION_BASE_URL}{FRONTEND_ADMIN_INVITATION_PATH}?token=...&email=...
```

The shared email theme lives in:

```text
app/services/email_templates.py
```

For local visual checks without sending real email, run the backend and open:

```text
http://localhost:8000/dev/email-preview/admin-invitation
```

Optional query params:

```text
http://localhost:8000/dev/email-preview/admin-invitation?email=test@example.com&name=Thanh
```

The email logo is served locally from:

```text
http://localhost:8000/assets/email-logo.png
```

By default, `ADMIN_INVITATION_BASE_URL` uses `BACKEND_URL`, so the backend can
serve a simple public OTP form at `/admin/invitations/accept` even before the
main frontend implements this page.

## Endpoints

### Send invitation

```http
POST /admin/invitations
```

Requires an active `administrator`.

```json
{
  "email": "new.admin@example.com"
}
```

Sends an email with a registration link only. The OTP is not included in this
first email.

If the email already belongs to a non-admin user, the same endpoint starts a
promotion request instead of failing. Emails that already have `admin` or
`administrator` access are rejected.

### Send OTP after profile form

```http
POST /admin/invitations/send-otp
```

Public endpoint. The frontend reads `token` and `email` from the invitation link.
Call this after the invitee fills the profile form and clicks `Gửi mã`.

```json
{
  "token": "token-from-link",
  "email": "new.admin@example.com",
  "full_name": "New Admin",
  "phone": "0901234567",
  "date_of_birth": "2000-01-01",
  "gender": "male"
}
```

Sends a 6-digit OTP to the invitee email. Each call generates a new code and
resets the OTP expiry window.

### Submit OTP

```http
POST /admin/invitations/verify-otp
```

Public endpoint. The profile fields are kept so the final verify request can
submit the same data together with the OTP.

```json
{
  "token": "token-from-link",
  "email": "new.admin@example.com",
  "otp_code": "123456",
  "full_name": "New Admin",
  "phone": "0901234567",
  "date_of_birth": "2000-01-01",
  "gender": "male"
}
```

Moves the invitation to `pending_approval`. The backend-hosted accept page uses
a two-step flow: first profile information, then a 6-digit OTP screen with a
`Gửi mã` button.

### List invitations

```http
GET /admin/invitations
GET /admin/invitations?status=pending_approval
```

Statuses: `otp_pending`, `pending_approval`, `approved`, `rejected`, `expired`.

### Approve invitation

```http
POST /admin/invitations/{invitation_id}/approve
```

Requires an active `administrator`.

```json
{
  "permissions": ["teachers", "students", "classes"]
}
```

Creates the admin account for a new email. For an existing non-admin user, this
promotes the existing account to `admin`, assigns the selected permissions,
stores the submitted profile fields, generates a strong 10-character temporary
password, and emails the credentials to the user.

### Reject invitation

```http
POST /admin/invitations/{invitation_id}/reject
```

Requires an active `administrator`.

```json
{
  "reason": "Not approved"
}
```
