# Email verification setup

The backend already supports email verification for local email/password
accounts.

## Current flow

1. `POST /auth/register` creates the user with `email_verified=false`.
2. The backend sends a 6-digit OTP code to the registered email.
3. The frontend submits that code with `POST /auth/email-verification/verify-otp`.
4. The backend marks the current authenticated user as verified.

Users can request another email with:

```http
POST /auth/email-verification/resend
```

or the clearer alias:

```http
POST /auth/email-verification/send-otp
```

Submit an OTP with:

```http
POST /auth/email-verification/verify-otp
Content-Type: application/json

{
  "otp_code": "123456"
}
```

These endpoints require the auth session created by register/login.

`GET /auth/verify-email?token=...` is still available for old verification
links, but register now sends OTP instead of link.

## Recommended free provider

Use Brevo SMTP for MVP/local production testing. It has a free plan and works
with the existing SMTP code, so no backend code change is needed.

Brevo SMTP env example:

```env
EMAIL_DELIVERY_MODE=smtp
EMAIL_FROM_ADDRESS=your_verified_sender@example.com
EMAIL_FROM_NAME=Scholar Clarity
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USERNAME=your_brevo_smtp_login
SMTP_PASSWORD=your_brevo_smtp_key
SMTP_USE_TLS=true
SMTP_USE_SSL=false
EMAIL_VERIFICATION_SECRET=replace_with_a_long_random_secret
EMAIL_VERIFICATION_EXPIRE_HOURS=24
EMAIL_VERIFICATION_OTP_EXPIRE_MINUTES=15
EMAIL_VERIFICATION_OTP_MAX_ATTEMPTS=5
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3001
FRONTEND_EMAIL_VERIFICATION_PATH=/verify-email
```

For Render, set the same values in the backend service environment variables,
then redeploy.

## Other free options

Resend also works through SMTP, but it is best when the project has a verified
domain. Gmail SMTP can work for development with an app password, but it is less
ideal for product email because personal inbox sending is easier to hit limits
or spam checks.

## Local testing

For local testing without a real email provider:

```env
EMAIL_DELIVERY_MODE=log
```

Then register a user and copy the 6-digit verification code from the backend
terminal logs.
