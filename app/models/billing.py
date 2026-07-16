from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    price_vnd = Column(Integer, nullable=False)
    qc_amount = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False, default=30)
    discount_min_quantity = Column(Integer, nullable=False, default=0)
    discount_percent = Column(Integer, nullable=False, default=0)
    bonus_qc_percent = Column(Integer, nullable=False, default=0)
    daily_free_more_questions = Column(Integer, nullable=False, default=0)
    priority_level = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payment_orders = relationship("PaymentOrder", back_populates="plan")


class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True)
    transfer_code = Column(String(25), nullable=True, unique=True, index=True)
    amount_vnd = Column(Integer, nullable=False)
    qc_amount = Column(Integer, nullable=False)
    duration_days = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_vnd = Column(Integer, nullable=False, default=0)
    subtotal_vnd = Column(Integer, nullable=False, default=0)
    discount_percent = Column(Integer, nullable=False, default=0)
    base_qc_amount = Column(Integer, nullable=False, default=0)
    bonus_qc_amount = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="pending", index=True)
    provider = Column(String(30), nullable=False, default="sepay")
    provider_order_id = Column(String(100), nullable=True, unique=True, index=True)
    provider_va_number = Column(String(100), nullable=True, unique=True, index=True)
    provider_transaction_id = Column(String(100), nullable=True, unique=True, index=True)
    provider_payload = Column(Text, nullable=True)
    qr_url = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plan = relationship("SubscriptionPlan", back_populates="payment_orders")


class TeacherQCWallet(Base):
    __tablename__ = "teacher_qc_wallets"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    balance = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TeacherPlanEntitlement(Base):
    __tablename__ = "teacher_plan_entitlements"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    plan_code = Column(String(30), nullable=False, default="premium")
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    daily_free_more_questions = Column(Integer, nullable=False, default=0)
    priority_level = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TeacherDailyAIQuota(Base):
    __tablename__ = "teacher_daily_ai_quotas"
    __table_args__ = (
        UniqueConstraint("teacher_id", "quota_date", name="uq_teacher_daily_ai_quota"),
    )

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quota_date = Column(Date, nullable=False, index=True)
    free_questions_used = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIQCUsage(Base):
    __tablename__ = "ai_qc_usages"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ai_job_id = Column(Integer, ForeignKey("ai_exam_generation_jobs.id"), nullable=False, index=True)
    operation_key = Column(String(160), nullable=False, unique=True, index=True)
    operation_type = Column(String(30), nullable=False)
    requested_questions = Column(Integer, nullable=False)
    free_questions = Column(Integer, nullable=False, default=0)
    qc_reserved = Column(Integer, nullable=False, default=0)
    qc_charged = Column(Integer, nullable=False, default=0)
    qc_refunded = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="reserved", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class QCTransaction(Base):
    __tablename__ = "qc_transactions"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    payment_order_id = Column(
        Integer,
        ForeignKey("payment_orders.id"),
        nullable=True,
        index=True,
    )
    ai_usage_id = Column(Integer, ForeignKey("ai_qc_usages.id"), nullable=True, index=True)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    transaction_type = Column(String(30), nullable=False, default="payment_credit")
    external_reference = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SePayWebhookEvent(Base):
    __tablename__ = "sepay_webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    sepay_transaction_id = Column(BigInteger, nullable=False, unique=True, index=True)
    payment_order_id = Column(Integer, ForeignKey("payment_orders.id"), nullable=True, index=True)
    reference_code = Column(String(255), nullable=True)
    status = Column(String(30), nullable=False)
    reason = Column(String(255), nullable=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
