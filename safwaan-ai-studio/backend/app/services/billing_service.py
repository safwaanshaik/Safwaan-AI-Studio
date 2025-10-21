"""
SAFWAAN AI STUDIO - Billing Service
Business logic for billing, subscriptions, and monetization operations.

This module provides:
- Subscription management
- Payment processing
- Credit system operations
- Invoice generation
- Revenue analytics
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_

from app.db.models.billing import (
    Subscription,
    PaymentMethod,
    Invoice,
    CreditTransaction,
    SubscriptionPlan
)
from app.schemas.billing import (
    SubscriptionCreate,
    PaymentMethodCreate,
    CreditTransactionCreate
)
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.core.monitoring import record_error


class BillingService:
    """Service class for billing operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_subscription_plans(self) -> List[Dict[str, Any]]:
        """Get all available subscription plans."""
        try:
            query = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
            result = await self.db.execute(query)
            plans = result.scalars().all()

            return [
                {
                    "id": plan.id,
                    "name": plan.name,
                    "description": plan.description,
                    "price": plan.price,
                    "currency": plan.currency,
                    "interval": plan.interval,
                    "features": plan.features,
                    "max_credits": plan.max_credits,
                    "max_projects": plan.max_projects,
                    "max_videos_per_month": plan.max_videos_per_month,
                    "priority_support": plan.priority_support,
                    "api_access": plan.api_access
                }
                for plan in plans
            ]

        except Exception as e:
            record_error("get_subscription_plans_error", "billing_service")
            raise

    async def get_user_subscription(self, user_id: str) -> Dict[str, Any]:
        """Get user's current subscription."""
        try:
            query = select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.is_active == True
                )
            )
            result = await self.db.execute(query)
            subscription = result.scalar_one_or_none()

            if not subscription:
                return {
                    "plan": "free",
                    "status": "inactive",
                    "credits_remaining": 0,
                    "next_billing_date": None,
                    "features": []
                }

            return {
                "id": subscription.id,
                "plan_id": subscription.plan_id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "credits_remaining": subscription.credits_remaining,
                "features": subscription.features or []
            }

        except Exception as e:
            record_error("get_user_subscription_error", "billing_service")
            raise

    async def upgrade_subscription(
        self,
        user_id: str,
        plan_id: str,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Upgrade user subscription plan."""
        try:
            # Get plan details
            plan_query = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
            plan_result = await self.db.execute(plan_query)
            plan = plan_result.scalar_one_or_none()

            if not plan:
                raise NotFoundError("Subscription plan not found")

            # Check current subscription
            current_query = select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.is_active == True
                )
            )
            current_result = await self.db.execute(current_query)
            current_subscription = current_result.scalar_one_or_none()

            if current_subscription:
                # Update existing subscription
                update_data = {
                    "plan_id": plan_id,
                    "updated_at": datetime.utcnow()
                }

                # Prorate credits if upgrading
                if plan.max_credits > current_subscription.credits_remaining:
                    update_data["credits_remaining"] = plan.max_credits

                query = (
                    update(Subscription)
                    .where(Subscription.id == current_subscription.id)
                    .values(**update_data)
                )
            else:
                # Create new subscription
                new_subscription = Subscription(
                    user_id=user_id,
                    plan_id=plan_id,
                    status="active",
                    credits_remaining=plan.max_credits,
                    current_period_start=datetime.utcnow(),
                    current_period_end=datetime.utcnow() + timedelta(days=30),
                    features=plan.features,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(new_subscription)

            await self.db.commit()

            return {"message": "Subscription upgraded successfully"}

        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            record_error("upgrade_subscription_error", "billing_service")
            raise

    async def cancel_subscription(self, user_id: str, reason: Optional[str] = None) -> Dict[str, str]:
        """Cancel user subscription."""
        try:
            query = (
                update(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.is_active == True
                    )
                )
                .values(
                    cancel_at_period_end=True,
                    cancellation_reason=reason,
                    updated_at=datetime.utcnow()
                )
            )

            result = await self.db.execute(query)
            if result.rowcount == 0:
                raise NotFoundError("Active subscription not found")

            await self.db.commit()

            return {"message": "Subscription cancelled successfully"}

        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            record_error("cancel_subscription_error", "billing_service")
            raise

    async def get_credit_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user's credit balance."""
        try:
            # Get current subscription credits
            sub_query = select(Subscription.credits_remaining).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.is_active == True
                )
            )
            sub_result = await self.db.execute(sub_query)
            subscription_credits = sub_result.scalar() or 0

            # Get additional purchased credits (not used)
            # TODO: Implement purchased credits tracking

            # Get credit usage this month
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            usage_query = select(func.sum(CreditTransaction.amount)).where(
                and_(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.type == "usage",
                    CreditTransaction.created_at >= month_start
                )
            )
            usage_result = await self.db.execute(usage_query)
            monthly_usage = usage_result.scalar() or 0

            return {
                "subscription_credits": subscription_credits,
                "purchased_credits": 0,  # TODO: Implement
                "total_available": subscription_credits,
                "monthly_usage": monthly_usage,
                "monthly_limit": 1000  # TODO: Get from subscription plan
            }

        except Exception as e:
            record_error("get_credit_balance_error", "billing_service")
            raise

    async def purchase_credits(
        self,
        user_id: str,
        amount: int,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """Purchase additional credits."""
        try:
            # TODO: Implement payment processing with Stripe
            # For now, simulate successful purchase

            # Calculate cost (example: $0.10 per credit)
            cost_per_credit = Decimal("0.10")
            total_cost = Decimal(amount) * cost_per_credit

            # Create invoice
            invoice = Invoice(
                user_id=user_id,
                amount=total_cost,
                currency="USD",
                status="paid",
                description=f"Credit purchase: {amount} credits",
                payment_method_id=payment_method_id,
                created_at=datetime.utcnow(),
                paid_at=datetime.utcnow()
            )
            self.db.add(invoice)

            # Add credits to user subscription
            sub_query = (
                update(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.is_active == True
                    )
                )
                .values(
                    credits_remaining=Subscription.credits_remaining + amount,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(sub_query)

            # Record credit transaction
            transaction = CreditTransaction(
                user_id=user_id,
                amount=amount,
                type="purchase",
                description=f"Purchased {amount} credits",
                invoice_id=invoice.id,
                created_at=datetime.utcnow()
            )
            self.db.add(transaction)

            await self.db.commit()

            return {
                "message": "Credits purchased successfully",
                "credits_added": amount,
                "total_cost": float(total_cost),
                "invoice_id": invoice.id
            }

        except Exception as e:
            await self.db.rollback()
            record_error("purchase_credits_error", "billing_service")
            raise

    async def get_credit_transactions(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        transaction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's credit transaction history."""
        try:
            query = select(CreditTransaction).where(CreditTransaction.user_id == user_id)

            if transaction_type:
                query = query.where(CreditTransaction.type == transaction_type)

            query = query.order_by(CreditTransaction.created_at.desc()).offset(skip).limit(limit)

            result = await self.db.execute(query)
            transactions = result.scalars().all()

            return [
                {
                    "id": tx.id,
                    "amount": tx.amount,
                    "type": tx.type,
                    "description": tx.description,
                    "created_at": tx.created_at
                }
                for tx in transactions
            ]

        except Exception as e:
            record_error("get_credit_transactions_error", "billing_service")
            raise

    async def get_usage_report(self, user_id: str, period: str = "month") -> Dict[str, Any]:
        """Get usage report for billing period."""
        try:
            # Calculate period start
            now = datetime.utcnow()
            if period == "week":
                period_start = now - timedelta(days=7)
            elif period == "month":
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == "year":
                period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                raise ValidationError("Invalid period")

            # Get usage statistics
            usage_query = select(
                func.sum(CreditTransaction.amount).label("total_used"),
                func.count(CreditTransaction.id).label("transaction_count")
            ).where(
                and_(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.type == "usage",
                    CreditTransaction.created_at >= period_start
                )
            )

            usage_result = await self.db.execute(usage_query)
            usage_stats = usage_result.first()

            return {
                "period": period,
                "period_start": period_start,
                "period_end": now,
                "total_credits_used": usage_stats.total_used or 0,
                "transaction_count": usage_stats.transaction_count or 0,
                "average_cost_per_video": 0.0  # TODO: Calculate based on video costs
            }

        except ValidationError:
            raise
        except Exception as e:
            record_error("get_usage_report_error", "billing_service")
            raise

    async def get_user_invoices(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user's invoices."""
        try:
            query = select(Invoice).where(Invoice.user_id == user_id)

            if status:
                query = query.where(Invoice.status == status)

            query = query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit)

            result = await self.db.execute(query)
            invoices = result.scalars().all()

            return [
                {
                    "id": invoice.id,
                    "amount": float(invoice.amount),
                    "currency": invoice.currency,
                    "status": invoice.status,
                    "description": invoice.description,
                    "created_at": invoice.created_at,
                    "paid_at": invoice.paid_at
                }
                for invoice in invoices
            ]

        except Exception as e:
            record_error("get_user_invoices_error", "billing_service")
            raise

    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Get invoice details."""
        try:
            query = select(Invoice).where(Invoice.id == invoice_id)
            result = await self.db.execute(query)
            invoice = result.scalar_one_or_none()

            if not invoice:
                raise NotFoundError("Invoice not found")

            return {
                "id": invoice.id,
                "user_id": invoice.user_id,
                "amount": float(invoice.amount),
                "currency": invoice.currency,
                "status": invoice.status,
                "description": invoice.description,
                "payment_method_id": invoice.payment_method_id,
                "created_at": invoice.created_at,
                "paid_at": invoice.paid_at,
                "due_date": invoice.due_date
            }

        except NotFoundError:
            raise
        except Exception as e:
            record_error("get_invoice_error", "billing_service")
            raise

    async def add_payment_method(
        self,
        user_id: str,
        payment_method_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add payment method for user."""
        try:
            # TODO: Integrate with Stripe for payment method creation
            # For now, simulate adding payment method

            payment_method = PaymentMethod(
                user_id=user_id,
                type=payment_method_data.get("type", "card"),
                provider="stripe",  # TODO: Make configurable
                provider_payment_method_id=f"pm_{datetime.utcnow().timestamp()}",
                last_four=payment_method_data.get("last_four"),
                brand=payment_method_data.get("brand"),
                expiry_month=payment_method_data.get("expiry_month"),
                expiry_year=payment_method_data.get("expiry_year"),
                is_default=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            self.db.add(payment_method)
            await self.db.commit()
            await self.db.refresh(payment_method)

            return {
                "id": payment_method.id,
                "type": payment_method.type,
                "brand": payment_method.brand,
                "last_four": payment_method.last_four,
                "is_default": payment_method.is_default
            }

        except Exception as e:
            await self.db.rollback()
            record_error("add_payment_method_error", "billing_service")
            raise

    async def get_payment_methods(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's payment methods."""
        try:
            query = select(PaymentMethod).where(
                and_(
                    PaymentMethod.user_id == user_id,
                    PaymentMethod.is_deleted == False
                )
            )

            result = await self.db.execute(query)
            methods = result.scalars().all()

            return [
                {
                    "id": method.id,
                    "type": method.type,
                    "brand": method.brand,
                    "last_four": method.last_four,
                    "expiry_month": method.expiry_month,
                    "expiry_year": method.expiry_year,
                    "is_default": method.is_default
                }
                for method in methods
            ]

        except Exception as e:
            record_error("get_payment_methods_error", "billing_service")
            raise

    async def delete_payment_method(self, user_id: str, method_id: str) -> Dict[str, str]:
        """Delete payment method."""
        try:
            query = (
                update(PaymentMethod)
                .where(
                    and_(
                        PaymentMethod.id == method_id,
                        PaymentMethod.user_id == user_id
                    )
                )
                .values(
                    is_deleted=True,
                    deleted_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )

            result = await self.db.execute(query)
            if result.rowcount == 0:
                raise NotFoundError("Payment method not found")

            await self.db.commit()

            return {"message": "Payment method deleted successfully"}

        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            record_error("delete_payment_method_error", "billing_service")
            raise

    async def get_revenue_analytics(self, period: str = "month") -> Dict[str, Any]:
        """Get revenue analytics (admin only)."""
        try:
            # Calculate period start
            now = datetime.utcnow()
            if period == "week":
                period_start = now - timedelta(days=7)
            elif period == "month":
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == "quarter":
                quarter = ((now.month - 1) // 3) + 1
                period_start = now.replace(month=((quarter - 1) * 3) + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == "year":
                period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                raise ValidationError("Invalid period")

            # Get revenue statistics
            revenue_query = select(
                func.sum(Invoice.amount).label("total_revenue"),
                func.count(Invoice.id).label("total_invoices")
            ).where(
                and_(
                    Invoice.status == "paid",
                    Invoice.created_at >= period_start
                )
            )

            revenue_result = await self.db.execute(revenue_query)
            revenue_stats = revenue_result.first()

            return {
                "period": period,
                "period_start": period_start,
                "period_end": now,
                "total_revenue": float(revenue_stats.total_revenue or 0),
                "total_invoices": revenue_stats.total_invoices or 0,
                "average_invoice_value": float(revenue_stats.total_revenue or 0) / max(revenue_stats.total_invoices or 1, 1)
            }

        except ValidationError:
            raise
        except Exception as e:
            record_error("get_revenue_analytics_error", "billing_service")
            raise

    async def get_subscription_analytics(self) -> Dict[str, Any]:
        """Get subscription analytics (admin only)."""
        try:
            # Get subscription statistics
            sub_query = select(
                Subscription.plan_id,
                func.count(Subscription.id).label("count")
            ).where(Subscription.is_active == True).group_by(Subscription.plan_id)

            sub_result = await self.db.execute(sub_query)
            plan_distribution = dict(sub_result.all())

            # Get total active subscriptions
            total_query = select(func.count(Subscription.id)).where(Subscription.is_active == True)
            total_result = await self.db.execute(total_query)
            total_active = total_result.scalar()

            return {
                "total_active_subscriptions": total_active,
                "subscriptions_by_plan": plan_distribution,
                "generated_at": datetime.utcnow()
            }

        except Exception as e:
            record_error("get_subscription_analytics_error", "billing_service")
            raise

    async def grant_credits(self, user_id: str, amount: int, reason: str) -> Dict[str, str]:
        """Grant credits to user (admin only)."""
        try:
            # Add credits to user subscription
            sub_query = (
                update(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.is_active == True
                    )
                )
                .values(
                    credits_remaining=Subscription.credits_remaining + amount,
                    updated_at=datetime.utcnow()
                )
            )

            result = await self.db.execute(sub_query)
            if result.rowcount == 0:
                raise NotFoundError("Active subscription not found")

            # Record credit transaction
            transaction = CreditTransaction(
                user_id=user_id,
                amount=amount,
                type="bonus",
                description=f"Admin credit grant: {reason}",
                created_at=datetime.utcnow()
            )
            self.db.add(transaction)

            await self.db.commit()

            return {"message": f"Successfully granted {amount} credits to user"}

        except NotFoundError:
            raise
        except Exception as e:
            await self.db.rollback()
            record_error("grant_credits_error", "billing_service")
            raise