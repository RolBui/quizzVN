from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
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


class QCTransaction(Base):
    __tablename__ = "qc_transactions"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    payment_order_id = Column(
        Integer,
        ForeignKey("payment_orders.id"),
        nullable=False,
        unique=True,
        index=True,
    )
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
