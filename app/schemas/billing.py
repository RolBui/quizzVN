from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BillingPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    price_vnd: int
    qc_amount: int
    duration_days: int
    discount_min_quantity: int
    discount_percent: int
    bonus_qc_percent: int
    daily_free_more_questions: int
    priority_level: int


class BillingPlanListResponse(BaseModel):
    items: list[BillingPlanResponse]


class CreatePaymentOrderRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=30)
    quantity: int = Field(default=1, ge=1, le=12)


class PaymentOrderResponse(BaseModel):
    id: int
    transfer_code: str
    plan_code: str
    plan_name: str
    amount_vnd: int
    qc_amount: int
    quantity: int
    unit_price_vnd: int
    subtotal_vnd: int
    discount_percent: int
    base_qc_amount: int
    bonus_qc_amount: int
    entitlement_days: int
    status: str
    provider: str
    payment_account: str | None = None
    qr_url: str
    expires_at: datetime
    paid_at: datetime | None = None
    created_at: datetime


class PaymentOrderListResponse(BaseModel):
    items: list[PaymentOrderResponse]


class QCWalletResponse(BaseModel):
    balance: int
    qc_per_question: int
    premium_active: bool
    premium_expires_at: datetime | None = None
    free_more_questions_daily: int
    free_more_questions_remaining: int
    priority_level: int


class AIQCCostEstimateRequest(BaseModel):
    question_count: int = Field(ge=1, le=50)
    operation: Literal["initial", "generate_more"] = "initial"


class AIQCCostEstimateResponse(BaseModel):
    requested_questions: int
    free_questions: int
    charged_questions: int
    qc_cost: int
    balance: int
    sufficient_balance: bool
    premium_active: bool
    free_more_questions_remaining: int


class QCTransactionResponse(BaseModel):
    id: int
    amount: int
    balance_after: int
    transaction_type: str
    external_reference: str
    created_at: datetime


class QCTransactionListResponse(BaseModel):
    items: list[QCTransactionResponse]


class SePayWebhookResponse(BaseModel):
    success: bool
