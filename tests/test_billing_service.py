import hashlib
import hmac
import importlib
import json
import pkgutil
import unittest
from datetime import timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.core.config import settings
from app.core.security import utc_now
from app.database import Base
from app.models.billing import (
    AIQCUsage,
    PaymentOrder,
    QCTransaction,
    SePayWebhookEvent,
    SubscriptionPlan,
    TeacherDailyAIQuota,
    TeacherPlanEntitlement,
    TeacherQCWallet,
)
from app.models.ai_exam import AIExamGenerationJob, AIQuestionDraft
from app.models.role import Role
from app.models.user import User
from app.services.billing_service import (
    calculate_plan_purchase,
    create_payment_order,
    estimate_ai_qc_cost,
    grant_teacher_welcome_qc,
    process_sepay_webhook,
    refund_ai_qc_usage,
    reserve_ai_qc,
    settle_ai_qc_usage,
    verify_sepay_webhook_signature,
)
from app.services.ai_exam_service import (
    AIAgentResultValidationError,
    AIExamGenerationError,
    complete_ai_agent_job,
    create_ai_exam_generation_job,
    generate_exam_for_teacher,
    prepare_ai_agent_dispatch,
    update_ai_agent_job_progress,
)
from app.services.ai_provider_client import AIProviderError


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
            "AI_QC_COST_PER_QUESTION": settings.AI_QC_COST_PER_QUESTION,
            "TEACHER_WELCOME_QC": settings.TEACHER_WELCOME_QC,
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
        settings.AI_QC_COST_PER_QUESTION = 1
        settings.TEACHER_WELCOME_QC = 30

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

    def test_premium_three_months_applies_discount_and_bonus_qc(self):
        premium = SubscriptionPlan(
            code="premium",
            name="Premium",
            price_vnd=249_000,
            qc_amount=2_000,
            duration_days=30,
            discount_min_quantity=3,
            discount_percent=10,
            bonus_qc_percent=20,
            daily_free_more_questions=10,
            priority_level=1,
            is_active=True,
        )

        purchase = calculate_plan_purchase(premium, 3)

        self.assertEqual(purchase["subtotal_vnd"], 747_000)
        self.assertEqual(purchase["amount_vnd"], 672_300)
        self.assertEqual(purchase["base_qc_amount"], 6_000)
        self.assertEqual(purchase["bonus_qc_amount"], 1_200)
        self.assertEqual(purchase["qc_amount"], 7_200)
        self.assertEqual(purchase["duration_days"], 90)

    def test_paid_premium_order_credits_bonus_and_activates_entitlement(self):
        premium = SubscriptionPlan(
            code="premium",
            name="Premium",
            price_vnd=249_000,
            qc_amount=2_000,
            duration_days=30,
            discount_min_quantity=3,
            discount_percent=10,
            bonus_qc_percent=20,
            daily_free_more_questions=10,
            priority_level=1,
            is_active=True,
        )
        self.db.add(premium)
        self.db.flush()
        order = PaymentOrder(
            teacher_id=self.teacher.id,
            plan_id=premium.id,
            transfer_code="QVPREMIUM3",
            amount_vnd=672_300,
            qc_amount=7_200,
            duration_days=90,
            quantity=3,
            unit_price_vnd=249_000,
            subtotal_vnd=747_000,
            discount_percent=10,
            base_qc_amount=6_000,
            bonus_qc_amount=1_200,
            status="pending",
            provider="sepay",
            provider_order_id="premium-provider-order",
            provider_va_number="963QUIZVNPREMIUM",
            qr_url="https://example.com/premium-qr.png",
            expires_at=utc_now() + timedelta(minutes=15),
        )
        self.db.add(order)
        self.db.commit()

        result = process_sepay_webhook(
            self.db,
            self._webhook_payload(
                92709,
                order.provider_va_number,
                order.amount_vnd,
            ),
        )

        wallet = self.db.query(TeacherQCWallet).one()
        entitlement = self.db.query(TeacherPlanEntitlement).one()
        expires_at = entitlement.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(wallet.balance, 7_200)
        self.assertGreater(expires_at, utc_now() + timedelta(days=89))
        self.assertEqual(entitlement.daily_free_more_questions, 10)
        self.assertEqual(entitlement.priority_level, 1)

    def test_teacher_welcome_qc_is_granted_only_once(self):
        self.teacher.email_verified = True
        self.teacher.status = "active"
        self.db.commit()

        first = grant_teacher_welcome_qc(self.db, self.teacher)
        second = grant_teacher_welcome_qc(self.db, self.teacher)

        wallet = self.db.query(TeacherQCWallet).one()
        transactions = self.db.query(QCTransaction).filter(
            QCTransaction.transaction_type == "welcome_credit"
        )
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(wallet.balance, 30)
        self.assertEqual(transactions.count(), 1)

    def test_ai_qc_reservation_and_refund_are_idempotent(self):
        wallet = TeacherQCWallet(teacher_id=self.teacher.id, balance=20)
        job = self._create_ai_job(question_count=5)
        self.db.add(wallet)
        self.db.commit()

        usage = reserve_ai_qc(
            self.db,
            self.teacher,
            job,
            operation_key="initial:test-reserve-refund",
            operation_type="initial",
            question_count=5,
        )
        self.db.commit()

        self.assertEqual(usage.qc_reserved, 5)
        self.assertEqual(self.db.get(TeacherQCWallet, wallet.id).balance, 15)

        refund_ai_qc_usage(self.db, job.id, "initial")
        refund_ai_qc_usage(self.db, job.id, "initial")

        self.db.refresh(usage)
        self.db.refresh(job)
        self.assertEqual(self.db.get(TeacherQCWallet, wallet.id).balance, 20)
        self.assertEqual(usage.status, "refunded")
        self.assertEqual(usage.qc_refunded, 5)
        self.assertEqual(job.qc_refunded, 5)
        self.assertEqual(
            self.db.query(QCTransaction)
            .filter(QCTransaction.ai_usage_id == usage.id)
            .count(),
            2,
        )

    def test_ai_qc_reservation_rejects_insufficient_balance(self):
        wallet = TeacherQCWallet(teacher_id=self.teacher.id, balance=2)
        job = self._create_ai_job(question_count=5)
        self.db.add(wallet)
        self.db.commit()

        with self.assertRaises(HTTPException) as raised:
            reserve_ai_qc(
                self.db,
                self.teacher,
                job,
                operation_key="initial:not-enough",
                operation_type="initial",
                question_count=5,
            )

        self.assertEqual(raised.exception.status_code, 402)
        self.assertEqual(self.db.get(TeacherQCWallet, wallet.id).balance, 2)
        self.assertEqual(self.db.query(AIQCUsage).count(), 0)

    def test_premium_free_more_quota_is_restored_after_refund(self):
        now = utc_now()
        wallet = TeacherQCWallet(teacher_id=self.teacher.id, balance=20)
        entitlement = TeacherPlanEntitlement(
            teacher_id=self.teacher.id,
            plan_code="premium",
            starts_at=now,
            expires_at=now + timedelta(days=30),
            daily_free_more_questions=10,
            priority_level=1,
        )
        job = self._create_ai_job(question_count=12)
        self.db.add_all([wallet, entitlement])
        self.db.commit()

        usage = reserve_ai_qc(
            self.db,
            self.teacher,
            job,
            operation_key="generate-more:premium",
            operation_type="generate_more",
            question_count=12,
        )
        self.db.commit()

        estimate = estimate_ai_qc_cost(
            self.db,
            self.teacher,
            question_count=2,
            operation="generate_more",
        )
        quota = self.db.query(TeacherDailyAIQuota).one()
        self.assertEqual(usage.free_questions, 10)
        self.assertEqual(usage.qc_reserved, 2)
        self.assertEqual(wallet.balance, 18)
        self.assertEqual(quota.free_questions_used, 10)
        self.assertEqual(estimate["free_more_questions_remaining"], 0)

        refund_ai_qc_usage(self.db, job.id, "generate_more")

        self.db.refresh(wallet)
        self.db.refresh(quota)
        self.assertEqual(wallet.balance, 20)
        self.assertEqual(quota.free_questions_used, 0)

    def test_settled_ai_usage_is_not_refunded(self):
        wallet = TeacherQCWallet(teacher_id=self.teacher.id, balance=10)
        job = self._create_ai_job(question_count=4)
        self.db.add(wallet)
        self.db.commit()
        usage = reserve_ai_qc(
            self.db,
            self.teacher,
            job,
            operation_key="initial:settle",
            operation_type="initial",
            question_count=4,
        )
        self.db.commit()

        settle_ai_qc_usage(self.db, job.id, "initial")
        refund_ai_qc_usage(self.db, job.id, "initial")

        self.db.refresh(wallet)
        self.db.refresh(usage)
        self.db.refresh(job)
        self.assertEqual(wallet.balance, 6)
        self.assertEqual(usage.status, "charged")
        self.assertEqual(usage.qc_charged, 4)
        self.assertEqual(job.qc_charged, 4)

    def test_ai_generation_idempotency_key_does_not_charge_twice(self):
        self.teacher.email_verified = True
        self.db.commit()
        request_data = self._ai_request_data(question_count=5)

        first_job, first_created = create_ai_exam_generation_job(
            self.db,
            self.teacher,
            request_data,
            idempotency_key="same-request",
        )
        second_job, second_created = create_ai_exam_generation_job(
            self.db,
            self.teacher,
            request_data,
            idempotency_key="same-request",
        )

        wallet = self.db.query(TeacherQCWallet).one()
        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_job.id, second_job.id)
        self.assertEqual(wallet.balance, 25)
        self.assertEqual(self.db.query(AIQCUsage).count(), 1)

    def test_failed_ai_generation_refunds_reserved_qc(self):
        self.teacher.email_verified = True
        self.db.commit()
        provider = MagicMock()
        provider.generate_exam.side_effect = AIProviderError("provider unavailable")

        with patch(
            "app.services.ai_exam_service._get_ai_provider_client",
            return_value=provider,
        ):
            with self.assertRaises(AIExamGenerationError):
                generate_exam_for_teacher(
                    self.db,
                    self.teacher,
                    self._ai_request_data(question_count=5),
                )

        wallet = self.db.query(TeacherQCWallet).one()
        job = self.db.query(AIExamGenerationJob).one()
        usage = self.db.query(AIQCUsage).one()
        self.assertEqual(wallet.balance, 30)
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.qc_refunded, 5)
        self.assertEqual(usage.status, "refunded")
        self.assertEqual(usage.qc_refunded, 5)

    def test_ai_agent_callback_is_idempotent(self):
        self.teacher.email_verified = True
        self.db.commit()
        request_data = self._ai_request_data(question_count=1)
        job, _ = create_ai_exam_generation_job(
            self.db,
            self.teacher,
            request_data,
            idempotency_key="agent-callback",
        )
        dispatch = prepare_ai_agent_dispatch(self.db, job.id, "initial")
        payload = {
            "title": "AI exam",
            "description": "Generated by Agent",
            "subject": "Toan",
            "grade": "12",
            "duration_minutes": 30,
            "total_points": 1,
            "questions": [
                {
                    "type": "multiple_choice",
                    "content": "Ket qua cua 1 + 1 la gi?",
                    "options": ["1", "2", "3", "4"],
                    "correct_answer": "2",
                    "explanation": "1 + 1 = 2.",
                    "difficulty": "easy",
                    "points": 1,
                    "topic": "Tich phan",
                }
            ],
        }

        first = complete_ai_agent_job(
            self.db,
            job.id,
            dispatch["dispatch_id"],
            "initial",
            payload,
            payload,
            "gemini",
            "gemini-2.5-flash",
        )
        second = complete_ai_agent_job(
            self.db,
            job.id,
            dispatch["dispatch_id"],
            "initial",
            payload,
            payload,
            "gemini",
            "gemini-2.5-flash",
        )

        usage = self.db.query(AIQCUsage).one()
        self.assertEqual(first.status, "completed")
        self.assertEqual(second.agent_result_status, "completed")
        self.assertEqual(self.db.query(AIQuestionDraft).count(), 1)
        self.assertEqual(usage.status, "charged")
        self.assertEqual(usage.qc_charged, 1)

    def test_ai_agent_progress_does_not_settle_or_refund_qc(self):
        self.teacher.email_verified = True
        self.db.commit()
        request_data = self._ai_request_data(question_count=10)
        job, _ = create_ai_exam_generation_job(
            self.db,
            self.teacher,
            request_data,
            idempotency_key="agent-progress",
        )
        dispatch = prepare_ai_agent_dispatch(self.db, job.id, "initial")

        updated = update_ai_agent_job_progress(
            self.db,
            job.id,
            dispatch["dispatch_id"],
            "initial",
            "validating",
            7,
            10,
            "Da kiem tra 7/10 cau",
        )

        usage = self.db.query(AIQCUsage).one()
        self.assertEqual(updated.status, "running")
        self.assertEqual(updated.agent_stage, "validating")
        self.assertEqual(updated.agent_progress_current, 7)
        self.assertEqual(updated.agent_progress_total, 10)
        self.assertEqual(usage.status, "reserved")

    def test_ai_agent_semantic_error_can_be_repaired_before_qc_settlement(self):
        self.teacher.email_verified = True
        self.db.commit()
        request_data = self._ai_request_data(question_count=1)
        request_data["question_types"] = ["true_false"]
        request_data["question_type_distribution"] = {"true_false": 1}
        job, _ = create_ai_exam_generation_job(
            self.db,
            self.teacher,
            request_data,
            idempotency_key="agent-semantic-repair",
        )
        dispatch = prepare_ai_agent_dispatch(self.db, job.id, "initial")
        payload = {
            "title": "AI exam",
            "description": "Generated by Agent",
            "subject": "Toan",
            "grade": "12",
            "duration_minutes": 30,
            "total_points": 1,
            "questions": [
                {
                    "type": "true_false",
                    "content": "Mot menh de dung hay sai?",
                    "options": [],
                    "correct_answer": "khong ro",
                    "explanation": "Giai thich.",
                    "difficulty": "easy",
                    "points": 1,
                    "topic": "Tich phan",
                }
            ],
        }

        with self.assertRaises(AIAgentResultValidationError):
            complete_ai_agent_job(
                self.db,
                job.id,
                dispatch["dispatch_id"],
                "initial",
                payload,
                payload,
                "gemini",
                "gemini-3.5-flash",
            )

        usage = self.db.query(AIQCUsage).one()
        wallet = self.db.query(TeacherQCWallet).one()
        self.assertEqual(usage.status, "reserved")
        self.assertEqual(wallet.balance, 29)

        payload["questions"][0]["correct_answer"] = "Đúng"
        completed = complete_ai_agent_job(
            self.db,
            job.id,
            dispatch["dispatch_id"],
            "initial",
            payload,
            payload,
            "gemini",
            "gemini-3.5-flash",
        )

        usage = self.db.query(AIQCUsage).one()
        draft = self.db.query(AIQuestionDraft).one()
        self.assertEqual(completed.status, "completed")
        self.assertEqual(usage.status, "charged")
        self.assertIs(draft.correct_answer, True)

    def _create_ai_job(self, question_count: int) -> AIExamGenerationJob:
        job = AIExamGenerationJob(
            teacher_id=self.teacher.id,
            subject="Toan",
            grade="12",
            topic="Tich phan",
            duration_minutes=30,
            question_count=question_count,
            question_types=["multiple_choice"],
            question_type_distribution={"multiple_choice": question_count},
            difficulty_distribution={"medium": question_count},
            language="Vietnamese",
            additional_instructions="",
            status="pending",
        )
        self.db.add(job)
        self.db.flush()
        return job

    @staticmethod
    def _ai_request_data(question_count: int) -> dict:
        return {
            "subject": "Toan",
            "grade": "12",
            "topic": "Tich phan",
            "duration_minutes": 30,
            "question_count": question_count,
            "question_types": ["multiple_choice"],
            "question_type_distribution": {
                "multiple_choice": question_count,
            },
            "difficulty_distribution": {
                "easy": 40,
                "medium": 40,
                "hard": 20,
            },
            "language": "Vietnamese",
            "additional_instructions": "",
        }

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
