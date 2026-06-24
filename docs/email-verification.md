# Email verification setup

The backend already supports email verification for local email/password
accounts.

## Current flow

1. `POST /auth/register` creates the user with `email_verified=false`.
2. The backend sends a verification link to the registered email.
3. The link opens `GET /auth/verify-email?token=...`.
4. The backend marks the user as verified, then redirects to:

```text
{FRONTEND_URL}{FRONTEND_EMAIL_VERIFICATION_PATH}?status=verified
```

Users can request another email with:

```http
POST /auth/email-verification/resend
```

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

Then register a user and copy the verification link from the backend terminal
logs.
