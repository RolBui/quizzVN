import hashlib
import hmac
import importlib
import json
import pkgutil
import unittest
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.core.config import settings
from app.core.security import utc_now
from app.database import Base
from app.models.billing import (
    PaymentOrder,
    QCTransaction,
    SePayWebhookEvent,
    SubscriptionPlan,
    TeacherQCWallet,
)
from app.models.role import Role
from app.models.user import User
from app.services.billing_service import (
    create_payment_order,
    process_sepay_webhook,
    verify_sepay_webhook_signature,
)


for module in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module(f"app.models.{module.name}")


class BillingServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        role = Role(name="teacher")
        self.db.add(role)
        self.db.flush()
        self.teacher = User(
            role_id=role.id,
            full_name="Teacher Test",
            username="teacher-test",
            email="teacher@example.com",
        )
        self.plan = SubscriptionPlan(
            code="gold",
            name="Vàng",
            price_vnd=129_000,
            qc_amount=800,
            duration_days=30,
            is_active=True,
        )
        self.db.add_all([self.teacher, self.plan])
        self.db.commit()
        self.db.refresh(self.teacher)
        self.db.refresh(self.plan)

        self.original_settings = {
            "SEPAY_API_TOKEN": settings.SEPAY_API_TOKEN,
            "SEPAY_BANK_ACCOUNT_ID": settings.SEPAY_BANK_ACCOUNT_ID,
            "SEPAY_VA_PREFIX": settings.SEPAY_VA_PREFIX,
            "SEPAY_WEBHOOK_SECRET": settings.SEPAY_WEBHOOK_SECRET,
            "SEPAY_WEBHOOK_TOLERANCE_SECONDS": settings.SEPAY_WEBHOOK_TOLERANCE_SECONDS,
        }
        settings.SEPAY_API_TOKEN = "test-token"
        settings.SEPAY_BANK_ACCOUNT_ID = "test-bank-account-id"
        settings.SEPAY_VA_PREFIX = "SEPQUIZVN"
        settings.SEPAY_WEBHOOK_SECRET = "test-webhook-secret"
        settings.SEPAY_WEBHOOK_TOLERANCE_SECONDS = 300

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        for key, value in self.original_settings.items():
            setattr(settings, key, value)

    def test_create_payment_order_uses_sepay_va_response(self):
        def fake_create(order):
            self.assertEqual(order.amount_vnd, 129_000)
            self.assertTrue(order.transfer_code.startswith("QV"))
            return {
                "id": "provider-order-id",
                "va_number": "963QUIZVN000001",
                "qr_code_url": (
                    "https://vietqr.app/img?acc=963QUIZVN000001"
                    "&bank=Sacombank&amount=129000&template=compact"
                ),
            }

        result = create_payment_order(
            self.db,
            self.teacher,
            "gold",
            sepay_order_factory=fake_create,
        )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["provider"], "sepay")
        self.assertEqual(result["payment_account"], "963QUIZVN000001")
        qr_query = parse_qs(urlsplit(result["qr_url"]).query)
        self.assertEqual(qr_query["amount"], ["129000"])
        self.assertEqual(qr_query["template"], ["compact"])
        self.assertEqual(qr_query["des"], [result["transfer_code"]])

    def test_valid_webhook_credits_qc_only_once(self):
        order = self._create_pending_order("963QUIZVN000002")
        payload = self._webhook_payload(
            sepay_id=92704,
            sub_account=order.provider_va_number,
            amount=order.amount_vnd,
        )

        first = process_sepay_webhook(self.db, payload)
        second = process_sepay_webhook(self.db, payload)

        wallet = self.db.query(TeacherQCWallet).one()
        refreshed_order = self.db.get(PaymentOrder, order.id)
        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(wallet.balance, 800)
        self.assertEqual(refreshed_order.status, "paid")
        self.assertEqual(self.db.query(QCTransaction).count(), 1)
        self.assertEqual(self.db.query(SePayWebhookEvent).count(), 1)

    def test_wrong_amount_does_not_credit_qc(self):
        order = self._create_pending_order("963QUIZVN000003")
        payload = self._webhook_payload(
            sepay_id=92705,
            sub_account=order.provider_va_number,
            amount=order.amount_vnd - 1,
        )

        result = process_sepay_webhook(self.db, payload)

        refreshed_order = self.db.get(PaymentOrder, order.id)
        event = self.db.query(SePayWebhookEvent).one()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "amount_mismatch")
        self.assertEqual(refreshed_order.status, "pending")
        self.assertEqual(event.reason, "amount_mismatch")
        self.assertEqual(self.db.query(TeacherQCWallet).count(), 0)
        self.assertEqual(self.db.query(QCTransaction).count(), 0)

    def test_separate_paid_orders_accumulate_qc_balance(self):
        first_order = self._create_pending_order("963QUIZVN000005")
        second_order = self._create_pending_order("963QUIZVN000006")

        process_sepay_webhook(
            self.db,
            self._webhook_payload(92707, first_order.provider_va_number, 129_000),
        )
        process_sepay_webhook(
            self.db,
            self._webhook_payload(92708, second_order.provider_va_number, 129_000),
        )

        wallet = self.db.query(TeacherQCWallet).one()
        self.assertEqual(wallet.balance, 1_600)
        self.assertEqual(self.db.query(QCTransaction).count(), 2)

    def test_dashboard_mock_webhook_is_acknowledged_without_credit(self):
        payload = self._webhook_payload(
            sepay_id=0,
            sub_account="MOCK-VA",
            amount=10_000,
        )

        result = process_sepay_webhook(self.db, payload)

        self.assertEqual(result["status"], "ignored")
        self.assertEqual(result["reason"], "payment_order_not_found")
        self.assertEqual(self.db.query(SePayWebhookEvent).count(), 1)
        self.assertEqual(self.db.query(TeacherQCWallet).count(), 0)

    def test_hmac_signature_uses_raw_body_and_timestamp(self):
        raw_body = json.dumps(
            self._webhook_payload(92706, "963QUIZVN000004", 129_000),
            separators=(",", ":"),
        ).encode("utf-8")
        timestamp = 1_750_000_000
        signed = str(timestamp).encode("utf-8") + b"." + raw_body
        signature = "sha256=" + hmac.new(
            settings.SEPAY_WEBHOOK_SECRET.encode("utf-8"),
            signed,
            hashlib.sha256,
        ).hexdigest()

        verify_sepay_webhook_signature(
            raw_body,
            signature,
            str(timestamp),
            now_seconds=timestamp,
        )

        with self.assertRaises(Exception):
            verify_sepay_webhook_signature(
                raw_body + b" ",
                signature,
                str(timestamp),
                now_seconds=timestamp,
            )

    def _create_pending_order(self, va_number: str) -> PaymentOrder:
        order = PaymentOrder(
            teacher_id=self.teacher.id,
            plan_id=self.plan.id,
            transfer_code=f"QV{va_number[-6:]}",
            amount_vnd=self.plan.price_vnd,
            qc_amount=self.plan.qc_amount,
            duration_days=self.plan.duration_days,
            status="pending",
            provider="sepay",
            provider_order_id=f"order-{va_number}",
            provider_va_number=va_number,
            qr_url="https://example.com/qr.png",
            expires_at=utc_now() + timedelta(minutes=15),
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    @staticmethod
    def _webhook_payload(
        sepay_id: int,
        sub_account: str,
        amount: int,
    ) -> dict:
        return {
            "id": sepay_id,
            "gateway": "Sacombank",
            "transactionDate": "2026-07-15 20:00:00",
            "accountNumber": "masked",
            "subAccount": sub_account,
            "code": None,
            "content": "Thanh toan QuizzVN",
            "transferType": "in",
            "transferAmount": amount,
            "accumulated": 0,
            "referenceCode": f"REF{sepay_id}",
            "description": "",
        }


if __name__ == "__main__":
    unittest.main()
