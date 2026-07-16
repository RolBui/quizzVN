import hashlib
import hmac
import json
import logging
import re
import time
from datetime import timedelta, timezone
from typing import Any, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import HTTPException, status
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import utc_now
from app.database import SessionLocal, engine
from app.models.billing import (
    PaymentOrder,
    QCTransaction,
    SePayWebhookEvent,
    SubscriptionPlan,
    TeacherQCWallet,
)
from app.models.user import User


logger = logging.getLogger(__name__)

PAYMENT_STATUS_CREATING = "creating"
PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_PAID = "paid"
PAYMENT_STATUS_EXPIRED = "expired"
PAYMENT_STATUS_FAILED = "failed"

DEFAULT_PLANS = (
    {
        "code": "silver",
        "name": "Bạc",
        "price_vnd": 69_000,
        "qc_amount": 300,
        "duration_days": 0,
    },
    {
        "code": "gold",
        "name": "Vàng",
        "price_vnd": 129_000,
        "qc_amount": 800,
        "duration_days": 0,
    },
    {
        "code": "premium",
        "name": "Premium",
        "price_vnd": 249_000,
        "qc_amount": 2_000,
        "duration_days": 0,
    },
)


def bootstrap_billing_storage() -> None:
    SubscriptionPlan.__table__.create(bind=engine, checkfirst=True)
    PaymentOrder.__table__.create(bind=engine, checkfirst=True)
    _ensure_payment_order_provider_columns()
    TeacherQCWallet.__table__.create(bind=engine, checkfirst=True)
    QCTransaction.__table__.create(bind=engine, checkfirst=True)
    SePayWebhookEvent.__table__.create(bind=engine, checkfirst=True)

    db = SessionLocal()
    try:
        existing_plans = {
            plan.code: plan for plan in db.query(SubscriptionPlan).all()
        }
        for plan_data in DEFAULT_PLANS:
            existing_plan = existing_plans.get(plan_data["code"])
            if not existing_plan:
                db.add(SubscriptionPlan(**plan_data, is_active=True))
            else:
                existing_plan.duration_days = 0
        db.commit()
    finally:
        db.close()


def _ensure_payment_order_provider_columns() -> None:
    inspector = inspect(engine)
    if not inspector.has_table(PaymentOrder.__tablename__):
        return

    existing = {
        column["name"] for column in inspector.get_columns(PaymentOrder.__tablename__)
    }
    additions = {
        "provider": "VARCHAR(30) NOT NULL DEFAULT 'sepay'",
        "provider_order_id": "VARCHAR(100)",
        "provider_va_number": "VARCHAR(100)",
        "provider_transaction_id": "VARCHAR(100)",
        "provider_payload": "TEXT",
    }
    with engine.begin() as connection:
        for name, column_type in additions.items():
            if name not in existing:
                connection.execute(
                    text(
                        f"ALTER TABLE {PaymentOrder.__tablename__} "
                        f"ADD COLUMN {name} {column_type}"
                    )
                )
        for column_name in (
            "provider_order_id",
            "provider_va_number",
            "provider_transaction_id",
        ):
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    f"uq_payment_orders_{column_name} "
                    f"ON {PaymentOrder.__tablename__} ({column_name})"
                )
            )


def list_active_plans(db: Session) -> dict[str, list[SubscriptionPlan]]:
    plans = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.price_vnd.asc())
        .all()
    )
    return {"items": plans}


def create_sepay_va_order(order: PaymentOrder) -> dict[str, Any]:
    _require_sepay_configuration()
    url = (
        f"{settings.SEPAY_API_BASE_URL}/bank-accounts/"
        f"{settings.SEPAY_BANK_ACCOUNT_ID}/orders"
    )
    payload = {
        "va_prefix": settings.SEPAY_VA_PREFIX,
        "order_code": order.transfer_code,
        "amount": order.amount_vnd,
        "duration": settings.BILLING_ORDER_EXPIRE_MINUTES * 60,
        "with_qrcode": "1",
        "qrcode_template": settings.SEPAY_QR_TEMPLATE,
    }
    try:
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.SEPAY_API_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.SEPAY_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        response_payload = response.json()
    except httpx.HTTPStatusError as exc:
        provider_code, provider_message = _read_sepay_error(exc.response)
        logger.warning(
            "SePay rejected order creation: status=%s code=%s message=%s",
            exc.response.status_code,
            provider_code or "unknown",
            provider_message or "unknown",
        )
        error_label = f" {provider_code}" if provider_code else ""
        error_message = f" {provider_message}" if provider_message else ""
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "SePay từ chối tạo mã thanh toán "
                f"({exc.response.status_code}{error_label}).{error_message}"
            ),
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("Unable to create SePay VA order")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Không thể tạo mã thanh toán SePay lúc này.",
        ) from exc

    data = response_payload.get("data") if isinstance(response_payload, dict) else None
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="SePay trả về dữ liệu đơn thanh toán không hợp lệ.",
        )
    return data


def _read_sepay_error(response: httpx.Response) -> tuple[str, str]:
    try:
        payload = response.json()
    except ValueError:
        return "", ""
    if not isinstance(payload, dict):
        return "", ""

    provider_code = str(
        payload.get("error_code") or payload.get("code") or ""
    ).strip()[:80]
    provider_message = str(
        payload.get("message") or payload.get("error") or ""
    ).strip()[:300]
    return provider_code, provider_message


def _with_transfer_code(qr_url: str, transfer_code: str) -> str:
    """Embed the order code so banking apps prefill the transfer description."""
    if not qr_url.startswith(("http://", "https://")):
        return qr_url

    parsed = urlsplit(qr_url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() != "des"
    ]
    query.append(("des", transfer_code))
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
    )


def create_payment_order(
    db: Session,
    teacher: User,
    plan_code: str,
    sepay_order_factory: Callable[[PaymentOrder], dict[str, Any]] = create_sepay_va_order,
) -> dict[str, Any]:
    _require_sepay_configuration()
    normalized_code = plan_code.strip().lower()
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.code == normalized_code,
            SubscriptionPlan.is_active.is_(True),
        )
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy gói đăng ký.",
        )

    now = utc_now()
    order = PaymentOrder(
        teacher_id=teacher.id,
        plan_id=plan.id,
        amount_vnd=plan.price_vnd,
        qc_amount=plan.qc_amount,
        duration_days=plan.duration_days,
        status=PAYMENT_STATUS_CREATING,
        provider="sepay",
        expires_at=now + timedelta(minutes=settings.BILLING_ORDER_EXPIRE_MINUTES),
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    db.flush()
    order.transfer_code = f"QV{order.id:010d}"
    db.commit()
    db.refresh(order)

    try:
        provider_data = sepay_order_factory(order)
        provider_order_id = str(provider_data.get("id") or "").strip()
        va_number = str(provider_data.get("va_number") or "").strip()
        qr_url = str(provider_data.get("qr_code_url") or "").strip()
        if not qr_url:
            qr_url = str(provider_data.get("qr_code") or "").strip()
        if not provider_order_id or not va_number or not qr_url:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="SePay trả thiếu thông tin VA hoặc mã QR.",
            )

        qr_url = _with_transfer_code(qr_url, order.transfer_code)

        order.provider_order_id = provider_order_id
        order.provider_va_number = va_number
        order.provider_payload = json.dumps(provider_data, ensure_ascii=False)
        order.qr_url = qr_url
        order.status = PAYMENT_STATUS_PENDING
        order.updated_at = utc_now()
        db.commit()
        db.refresh(order)
    except Exception:
        db.rollback()
        failed_order = db.get(PaymentOrder, order.id)
        if failed_order:
            failed_order.status = PAYMENT_STATUS_FAILED
            failed_order.updated_at = utc_now()
            db.commit()
        raise

    order.plan = plan
    return serialize_payment_order(order)


def verify_sepay_webhook_signature(
    raw_body: bytes,
    signature: str | None,
    timestamp: str | None,
    now_seconds: int | None = None,
) -> None:
    if not settings.SEPAY_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SePay webhook chưa được cấu hình trên máy chủ.",
        )
    try:
        parsed_timestamp = int(timestamp or "")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu timestamp của SePay.",
        ) from exc

    current_timestamp = int(time.time()) if now_seconds is None else now_seconds
    if abs(current_timestamp - parsed_timestamp) > settings.SEPAY_WEBHOOK_TOLERANCE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook SePay đã hết hiệu lực.",
        )

    signed_payload = str(parsed_timestamp).encode("utf-8") + b"." + raw_body
    expected = "sha256=" + hmac.new(
        settings.SEPAY_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chữ ký webhook SePay không hợp lệ.",
        )


def process_sepay_webhook(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    sepay_id = _required_non_negative_int(payload, "id")
    transfer_amount = _required_positive_int(payload, "transferAmount")
    raw_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    existing_event = (
        db.query(SePayWebhookEvent)
        .filter(SePayWebhookEvent.sepay_transaction_id == sepay_id)
        .first()
    )
    if existing_event:
        return {"status": "duplicate", "order_id": existing_event.payment_order_id}

    order = _find_payment_order_for_webhook(db, payload)
    event = SePayWebhookEvent(
        sepay_transaction_id=sepay_id,
        payment_order_id=order.id if order else None,
        reference_code=str(payload.get("referenceCode") or "")[:255] or None,
        status="received",
        payload=raw_payload,
    )
    db.add(event)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate", "order_id": None}

    if not order:
        return _finish_webhook_event(db, event, "ignored", "payment_order_not_found")
    if str(payload.get("transferType") or "").lower() != "in":
        return _finish_webhook_event(db, event, "ignored", "not_incoming")
    if transfer_amount != order.amount_vnd:
        return _finish_webhook_event(db, event, "rejected", "amount_mismatch")

    locked_order = (
        db.query(PaymentOrder)
        .filter(PaymentOrder.id == order.id)
        .with_for_update()
        .one()
    )
    existing_credit = (
        db.query(QCTransaction)
        .filter(QCTransaction.payment_order_id == locked_order.id)
        .first()
    )
    if existing_credit or locked_order.status == PAYMENT_STATUS_PAID:
        return _finish_webhook_event(db, event, "ignored", "order_already_paid")

    db.query(User).filter(User.id == locked_order.teacher_id).with_for_update().one()
    wallet = (
        db.query(TeacherQCWallet)
        .filter(TeacherQCWallet.teacher_id == locked_order.teacher_id)
        .with_for_update()
        .first()
    )
    if not wallet:
        wallet = TeacherQCWallet(
            teacher_id=locked_order.teacher_id,
            balance=0,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(wallet)
        db.flush()

    wallet.balance += locked_order.qc_amount
    wallet.updated_at = utc_now()
    db.add(
        QCTransaction(
            teacher_id=locked_order.teacher_id,
            payment_order_id=locked_order.id,
            amount=locked_order.qc_amount,
            balance_after=wallet.balance,
            transaction_type="payment_credit",
            external_reference=f"sepay:{sepay_id}",
            created_at=utc_now(),
        )
    )
    locked_order.status = PAYMENT_STATUS_PAID
    locked_order.paid_at = utc_now()
    locked_order.provider_transaction_id = str(sepay_id)
    locked_order.updated_at = utc_now()
    event.status = "processed"
    event.reason = None
    db.commit()
    return {"status": "processed", "order_id": locked_order.id, "balance": wallet.balance}


def _finish_webhook_event(
    db: Session,
    event: SePayWebhookEvent,
    event_status: str,
    reason: str,
) -> dict[str, Any]:
    event.status = event_status
    event.reason = reason
    db.commit()
    return {
        "status": event_status,
        "reason": reason,
        "order_id": event.payment_order_id,
    }


def _find_payment_order_for_webhook(
    db: Session,
    payload: dict[str, Any],
) -> PaymentOrder | None:
    sub_account = str(payload.get("subAccount") or "").strip()
    if sub_account:
        order = (
            db.query(PaymentOrder)
            .filter(PaymentOrder.provider_va_number == sub_account)
            .first()
        )
        if order:
            return order

    code = str(payload.get("code") or "").strip().upper()
    if code:
        order = db.query(PaymentOrder).filter(PaymentOrder.transfer_code == code).first()
        if order:
            return order

    content = str(payload.get("content") or "").upper()
    match = re.search(r"\bQV\d{10}\b", content)
    if not match:
        return None
    return (
        db.query(PaymentOrder)
        .filter(PaymentOrder.transfer_code == match.group(0))
        .first()
    )


def _required_positive_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool):
        value = None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Webhook SePay thiếu trường {field} hợp lệ.",
        ) from exc
    if parsed <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Webhook SePay thiếu trường {field} hợp lệ.",
        )
    return parsed


def _required_non_negative_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if isinstance(value, bool):
        value = None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Webhook SePay thiếu trường {field} hợp lệ.",
        ) from exc
    if parsed < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Webhook SePay thiếu trường {field} hợp lệ.",
        )
    return parsed


def get_teacher_payment_order(
    db: Session,
    teacher: User,
    order_id: int,
) -> dict[str, Any]:
    order = (
        db.query(PaymentOrder)
        .options(joinedload(PaymentOrder.plan))
        .filter(
            PaymentOrder.id == order_id,
            PaymentOrder.teacher_id == teacher.id,
        )
        .first()
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy đơn thanh toán.",
        )
    _expire_order_if_needed(db, order)
    return serialize_payment_order(order)


def list_teacher_payment_orders(
    db: Session,
    teacher: User,
    limit: int,
) -> dict[str, list[dict[str, Any]]]:
    orders = (
        db.query(PaymentOrder)
        .options(joinedload(PaymentOrder.plan))
        .filter(PaymentOrder.teacher_id == teacher.id)
        .order_by(PaymentOrder.id.desc())
        .limit(limit)
        .all()
    )
    changed = False
    for order in orders:
        changed = _expire_order_if_needed(db, order, commit=False) or changed
    if changed:
        db.commit()
    return {"items": [serialize_payment_order(order) for order in orders]}


def get_teacher_qc_wallet(db: Session, teacher: User) -> dict[str, int]:
    wallet = (
        db.query(TeacherQCWallet)
        .filter(TeacherQCWallet.teacher_id == teacher.id)
        .first()
    )
    return {"balance": wallet.balance if wallet else 0}


def serialize_payment_order(order: PaymentOrder) -> dict[str, Any]:
    return {
        "id": order.id,
        "transfer_code": order.transfer_code or "",
        "plan_code": order.plan.code,
        "plan_name": order.plan.name,
        "amount_vnd": order.amount_vnd,
        "qc_amount": order.qc_amount,
        "status": order.status,
        "provider": order.provider or "sepay",
        "payment_account": order.provider_va_number,
        "qr_url": order.qr_url or "",
        "expires_at": order.expires_at,
        "paid_at": order.paid_at,
        "created_at": order.created_at,
    }


def _expire_order_if_needed(
    db: Session,
    order: PaymentOrder,
    commit: bool = True,
) -> bool:
    if order.status != PAYMENT_STATUS_PENDING:
        return False
    expires_at = order.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at > utc_now():
        return False
    order.status = PAYMENT_STATUS_EXPIRED
    order.updated_at = utc_now()
    if commit:
        db.commit()
        db.refresh(order)
    return True


def _require_sepay_configuration() -> None:
    required_values = (
        settings.SEPAY_API_TOKEN,
        settings.SEPAY_BANK_ACCOUNT_ID,
        settings.SEPAY_VA_PREFIX,
    )
    if not all(required_values):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SePay chưa được cấu hình đầy đủ trên máy chủ.",
        )
