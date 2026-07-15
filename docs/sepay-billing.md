# SePay billing

## Environment variables

```env
SEPAY_API_BASE_URL=https://userapi.sepay.vn/v2
SEPAY_API_TOKEN=YOUR_SEPAY_API_V2_TOKEN
SEPAY_BANK_ACCOUNT_ID=YOUR_SACOMBANK_ACCOUNT_UUID
SEPAY_VA_PREFIX=YOUR_ACTIVE_SACOMBANK_VA_PREFIX
SEPAY_WEBHOOK_SECRET=YOUR_RANDOM_HMAC_SECRET
SEPAY_QR_TEMPLATE=compact2
SEPAY_TIMEOUT_SECONDS=15
SEPAY_WEBHOOK_TOLERANCE_SECONDS=300
BILLING_ORDER_EXPIRE_MINUTES=15
```

Never commit API tokens, webhook secrets, bank identifiers, or account details.

## API flow

1. Load plans with `GET /api/billing/plans`.
2. Create an order with `POST /api/billing/orders` and body `{"plan_code":"gold"}`.
3. Display `qr_url` and optionally `payment_account` from the response.
4. Poll `GET /api/billing/orders/{order_id}` until `status` becomes `paid`.
5. Read the teacher's QC balance with `GET /api/billing/wallet`.

The browser never sends a price or QC amount. The API reads both from
`subscription_plans` and asks SePay to create an order VA for that exact amount.

## Production webhook

Create the webhook in SePay with these settings:

- Name: `QuizzVN - Xac nhan thanh toan`
- URL: `https://quizzvn.onrender.com/api/billing/webhooks/sepay`
- Event: incoming transfers only
- Content type: JSON
- Automatic retry: enabled
- Account: select only the linked Sacombank account
- Authentication: HMAC-SHA256
- Secret: exactly the same value as `SEPAY_WEBHOOK_SECRET`

The endpoint verifies the HMAC signature and timestamp over the raw request body.
It uses the SePay transaction ID as an idempotency key, requires an exact amount,
and writes a QC ledger entry before marking the order paid.
