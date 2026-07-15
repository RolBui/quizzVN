from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BillingPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    price_vnd: int
    qc_amount: int


class BillingPlanListResponse(BaseModel):
    items: list[BillingPlanResponse]


class CreatePaymentOrderRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=30)


class PaymentOrderResponse(BaseModel):
    id: int
    transfer_code: str
    plan_code: str
    plan_name: str
    amount_vnd: int
    qc_amount: int
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


class SePayWebhookResponse(BaseModel):
    success: bool
