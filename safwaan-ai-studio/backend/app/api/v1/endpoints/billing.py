"""
SAFWAAN AI STUDIO - Billing and Monetization Endpoints
Subscription management, payments, and credit system.

This module provides:
- Subscription tier management
- Payment processing with Stripe
- Credit system and usage tracking
- Invoice generation and management
- Revenue analytics
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.schemas.billing import (
    SubscriptionPlan,
    PaymentMethod,
    Invoice,
    CreditTransaction,
    UsageReport
)
from app.services.billing_service import BillingService
from app.utils.exceptions import ValidationError, NotFoundError
from app.core.monitoring import record_error

router = APIRouter()


@router.get("/plans")
async def get_subscription_plans(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get available subscription plans.

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)
        plans = await billing_service.get_subscription_plans()
        return plans

    except Exception as e:
        record_error("get_plans_error", "billing")
        raise


@router.get("/subscription")
async def get_current_subscription(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current user's subscription details.

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)
        subscription = await billing_service.get_user_subscription(current_user["id"])
        return subscription

    except Exception as e:
        record_error("get_subscription_error", "billing")
        raise


@router.post("/subscription/upgrade")
async def upgrade_subscription(
    plan_id: str,
    payment_method_id: Optional[str] = None,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Upgrade user subscription plan.

    - **plan_id**: New subscription plan ID
    - **payment_method_id**: Payment method ID (optional)
    - **background_tasks**: Background task queue
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        result = await billing_service.upgrade_subscription(
            current_user["id"], plan_id, payment_method_id
        )

        # Send confirmation email
        background_tasks.add_task(
            send_subscription_change_email,
            current_user["id"],
            "upgrade",
            plan_id
        )

        return result

    except ValidationError:
        raise
    except Exception as e:
        record_error("upgrade_subscription_error", "billing")
        raise


@router.post("/subscription/cancel")
async def cancel_subscription(
    reason: Optional[str] = None,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Cancel user subscription.

    - **reason**: Cancellation reason (optional)
    - **background_tasks**: Background task queue
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        result = await billing_service.cancel_subscription(current_user["id"], reason)

        # Send confirmation email
        background_tasks.add_task(
            send_subscription_change_email,
            current_user["id"],
            "cancel",
            None
        )

        return result

    except Exception as e:
        record_error("cancel_subscription_error", "billing")
        raise


@router.get("/credits")
async def get_credit_balance(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current credit balance and usage.

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)
        balance = await billing_service.get_credit_balance(current_user["id"])
        return balance

    except Exception as e:
        record_error("get_credits_error", "billing")
        raise


@router.post("/credits/purchase")
async def purchase_credits(
    amount: int,
    payment_method_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Purchase additional credits.

    - **amount**: Number of credits to purchase
    - **payment_method_id**: Payment method ID
    - **background_tasks**: Background task queue
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        result = await billing_service.purchase_credits(
            current_user["id"], amount, payment_method_id
        )

        # Send confirmation email
        background_tasks.add_task(
            send_credit_purchase_email,
            current_user["id"],
            amount
        )

        return result

    except ValidationError:
        raise
    except Exception as e:
        record_error("purchase_credits_error", "billing")
        raise


@router.get("/transactions")
async def get_credit_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    transaction_type: Optional[str] = Query(None, regex="^(purchase|usage|refund|bonus)$"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get credit transaction history.

    - **skip**: Number of transactions to skip
    - **limit**: Maximum number of transactions to return
    - **transaction_type**: Filter by transaction type
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        transactions = await billing_service.get_credit_transactions(
            current_user["id"], skip, limit, transaction_type
        )

        return transactions

    except Exception as e:
        record_error("get_transactions_error", "billing")
        raise


@router.get("/usage")
async def get_usage_report(
    period: str = Query("month", regex="^(week|month|year)$"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get usage report for billing period.

    - **period**: Time period for report
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        report = await billing_service.get_usage_report(current_user["id"], period)

        return report

    except Exception as e:
        record_error("get_usage_error", "billing")
        raise


@router.get("/invoices")
async def get_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, regex="^(paid|pending|failed|refunded)$"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get user invoices.

    - **skip**: Number of invoices to skip
    - **limit**: Maximum number of invoices to return
    - **status**: Filter by invoice status
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        invoices = await billing_service.get_user_invoices(
            current_user["id"], skip, limit, status
        )

        return invoices

    except Exception as e:
        record_error("get_invoices_error", "billing")
        raise


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get specific invoice details.

    - **invoice_id**: Invoice ID
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        invoice = await billing_service.get_invoice(invoice_id)

        # Check ownership
        if invoice["user_id"] != current_user["id"]:
            raise NotFoundError("Invoice not found")

        return invoice

    except NotFoundError:
        raise
    except Exception as e:
        record_error("get_invoice_error", "billing")
        raise


@router.post("/payment-methods")
async def add_payment_method(
    payment_method_data: Dict[str, Any],  # TODO: Create proper schema
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Add new payment method.

    - **payment_method_data**: Payment method details
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        result = await billing_service.add_payment_method(
            current_user["id"], payment_method_data
        )

        return result

    except ValidationError:
        raise
    except Exception as e:
        record_error("add_payment_method_error", "billing")
        raise


@router.get("/payment-methods")
async def get_payment_methods(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get user's payment methods.

    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        methods = await billing_service.get_payment_methods(current_user["id"])

        return methods

    except Exception as e:
        record_error("get_payment_methods_error", "billing")
        raise


@router.delete("/payment-methods/{method_id}")
async def delete_payment_method(
    method_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete payment method.

    - **method_id**: Payment method ID
    - **current_user**: Current authenticated user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        result = await billing_service.delete_payment_method(
            current_user["id"], method_id
        )

        return result

    except Exception as e:
        record_error("delete_payment_method_error", "billing")
        raise


# Admin endpoints
@router.get("/admin/revenue", response_model=Dict[str, Any])
async def get_revenue_analytics(
    period: str = Query("month", regex="^(week|month|quarter|year)$"),
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get revenue analytics (admin only).

    - **period**: Time period for analysis
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        analytics = await billing_service.get_revenue_analytics(period)

        return analytics

    except Exception as e:
        record_error("get_revenue_analytics_error", "billing")
        raise


@router.get("/admin/subscriptions", response_model=Dict[str, Any])
async def get_subscription_analytics(
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get subscription analytics (admin only).

    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        analytics = await billing_service.get_subscription_analytics()

        return analytics

    except Exception as e:
        record_error("get_subscription_analytics_error", "billing")
        raise


@router.post("/admin/credits/grant")
async def grant_credits(
    user_id: str,
    amount: int,
    reason: str,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Grant credits to user (admin only).

    - **user_id**: Target user ID
    - **amount**: Number of credits to grant
    - **reason**: Reason for granting credits
    - **current_user**: Current admin user
    - **db**: Database session
    """
    try:
        billing_service = BillingService(db)

        result = await billing_service.grant_credits(user_id, amount, reason)

        return result

    except ValidationError:
        raise
    except Exception as e:
        record_error("grant_credits_error", "billing")
        raise


# Helper functions
async def send_subscription_change_email(user_id: str, change_type: str, plan_id: Optional[str]) -> None:
    """Send subscription change notification email."""
    # TODO: Implement email sending
    pass


async def send_credit_purchase_email(user_id: str, amount: int) -> None:
    """Send credit purchase confirmation email."""
    # TODO: Implement email sending
    pass