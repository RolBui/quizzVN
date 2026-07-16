import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_teacher
from app.schemas.billing import (
    AIQCCostEstimateRequest,
    AIQCCostEstimateResponse,
    BillingPlanListResponse,
    CreatePaymentOrderRequest,
    PaymentOrderListResponse,
    PaymentOrderResponse,
    QCWalletResponse,
    QCTransactionListResponse,
    SePayWebhookResponse,
)
from app.services.billing_service import (
    create_payment_order,
    estimate_ai_qc_cost,
    get_teacher_qc_wallet,
    get_teacher_payment_order,
    list_active_plans,
    list_teacher_qc_transactions,
    list_teacher_payment_orders,
    process_sepay_webhook,
    verify_sepay_webhook_signature,
)


router = APIRouter(prefix="/api/billing", tags=["Billing"])


@router.post("/webhooks/sepay", response_model=SePayWebhookResponse)
async def post_sepay_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> SePayWebhookResponse:
    raw_body = await request.body()
    verify_sepay_webhook_signature(
        raw_body,
        request.headers.get("X-SePay-Signature"),
        request.headers.get("X-SePay-Timestamp"),
    )
    try:
        payload = json.loads(raw_body)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook SePay không phải JSON hợp lệ.",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook SePay phải là một JSON object.",
        )
    process_sepay_webhook(db, payload)
    return {"success": True}


@router.get("/plans", response_model=BillingPlanListResponse)
def get_billing_plans(db: Session = Depends(get_db)) -> BillingPlanListResponse:
    return list_active_plans(db)


@router.post("/orders", response_model=PaymentOrderResponse, status_code=status.HTTP_201_CREATED)
def post_payment_order(
    payload: CreatePaymentOrderRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> PaymentOrderResponse:
    return create_payment_order(
        db,
        current_teacher,
        payload.plan_code,
        payload.quantity,
    )


@router.get("/orders", response_model=PaymentOrderListResponse)
def get_payment_orders(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> PaymentOrderListResponse:
    return list_teacher_payment_orders(db, current_teacher, limit)


@router.get("/wallet", response_model=QCWalletResponse)
def get_qc_wallet(
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> QCWalletResponse:
    return get_teacher_qc_wallet(db, current_teacher)


@router.post("/ai-cost/estimate", response_model=AIQCCostEstimateResponse)
def post_ai_cost_estimate(
    payload: AIQCCostEstimateRequest,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> AIQCCostEstimateResponse:
    return estimate_ai_qc_cost(
        db,
        current_teacher,
        payload.question_count,
        payload.operation,
    )


@router.get("/transactions", response_model=QCTransactionListResponse)
def get_qc_transactions(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> QCTransactionListResponse:
    return list_teacher_qc_transactions(db, current_teacher, limit)


@router.get("/orders/{order_id}", response_model=PaymentOrderResponse)
def get_payment_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_teacher=Depends(get_current_teacher),
) -> PaymentOrderResponse:
    return get_teacher_payment_order(db, current_teacher, order_id)
