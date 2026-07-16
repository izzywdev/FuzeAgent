"""
Tiered Pricing and Billing System for FuzeAgent

This service manages subscription tiers, usage tracking, billing calculations,
and payment processing for the FuzeAgent AI team orchestration platform.
Supports multiple pricing models and enterprise customization.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import asyncpg

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    """Available subscription tiers"""

    STARTER = "starter"  # Individual developers, small teams
    PROFESSIONAL = "professional"  # Growing teams, advanced features
    ENTERPRISE = "enterprise"  # Large organizations, custom limits
    CUSTOM = "custom"  # Tailored enterprise solutions


class BillingCycle(str, Enum):
    """Billing cycle options"""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class UsageMetricType(str, Enum):
    """Types of usage metrics tracked"""

    AGENT_HOURS = "agent_hours"  # AI agent compute hours
    API_CALLS = "api_calls"  # API requests made
    TASKS_EXECUTED = "tasks_executed"  # Number of tasks processed
    STORAGE_GB = "storage_gb"  # Data storage used
    INTEGRATIONS = "integrations"  # External integrations
    TEAM_MEMBERS = "team_members"  # Human team members
    CONCURRENT_AGENTS = "concurrent_agents"  # Peak concurrent agents


class SubscriptionStatus(str, Enum):
    """Subscription status options"""

    ACTIVE = "active"
    TRIAL = "trial"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    EXPIRED = "expired"


class PaymentStatus(str, Enum):
    """Payment transaction status"""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


@dataclass
class PricingTier:
    """Definition of a pricing tier"""

    tier: SubscriptionTier
    name: str
    description: str
    monthly_price: Decimal
    annual_price: Decimal
    agent_hours_included: int
    max_concurrent_agents: int
    max_team_members: int
    api_calls_included: int
    storage_gb_included: int
    integrations_included: int
    features: List[str]
    overage_rates: Dict[str, Decimal]
    is_active: bool
    metadata: Dict[str, Any]


@dataclass
class Subscription:
    """Customer subscription information"""

    id: str
    organization_id: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    current_period_start: date
    current_period_end: date
    trial_end: Optional[date]
    quantity: int
    custom_limits: Dict[str, Any]
    billing_email: str
    payment_method_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime]
    metadata: Dict[str, Any]


@dataclass
class UsageRecord:
    """Usage tracking record"""

    id: str
    organization_id: str
    subscription_id: str
    metric_type: UsageMetricType
    value: Decimal
    unit: str
    recorded_at: datetime
    billing_period: str
    metadata: Dict[str, Any]


@dataclass
class Invoice:
    """Billing invoice"""

    id: str
    organization_id: str
    subscription_id: str
    invoice_number: str
    amount_due: Decimal
    amount_paid: Decimal
    currency: str
    billing_period_start: date
    billing_period_end: date
    due_date: date
    status: PaymentStatus
    line_items: List[Dict[str, Any]]
    tax_amount: Decimal
    discount_amount: Decimal
    created_at: datetime
    paid_at: Optional[datetime]


class PricingBillingService:
    """Manages pricing, subscriptions, and billing"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.pricing_tiers = self._initialize_pricing_tiers()

    def _initialize_pricing_tiers(self) -> Dict[SubscriptionTier, PricingTier]:
        """Initialize standard pricing tiers"""
        return {
            SubscriptionTier.STARTER: PricingTier(
                tier=SubscriptionTier.STARTER,
                name="Starter",
                description="Perfect for individual developers and small teams getting started with AI automation",
                monthly_price=Decimal("29.00"),
                annual_price=Decimal("290.00"),  # 2 months free
                agent_hours_included=100,
                max_concurrent_agents=5,
                max_team_members=3,
                api_calls_included=10000,
                storage_gb_included=10,
                integrations_included=3,
                features=[
                    "Basic AI agent creation",
                    "Task automation",
                    "Standard integrations",
                    "Email support",
                    "Basic analytics",
                ],
                overage_rates={
                    "agent_hours": Decimal("0.50"),
                    "api_calls": Decimal("0.001"),
                    "storage_gb": Decimal("2.00"),
                    "integrations": Decimal("10.00"),
                },
                is_active=True,
                metadata={"target_audience": "individual_developers"},
            ),
            SubscriptionTier.PROFESSIONAL: PricingTier(
                tier=SubscriptionTier.PROFESSIONAL,
                name="Professional",
                description="Advanced features for growing teams and professional workflows",
                monthly_price=Decimal("99.00"),
                annual_price=Decimal("990.00"),  # 2 months free
                agent_hours_included=500,
                max_concurrent_agents=25,
                max_team_members=10,
                api_calls_included=100000,
                storage_gb_included=100,
                integrations_included=10,
                features=[
                    "Advanced AI agent templates",
                    "Custom workflows",
                    "Priority integrations",
                    "Advanced analytics",
                    "Phone & email support",
                    "Team collaboration tools",
                    "API access",
                ],
                overage_rates={
                    "agent_hours": Decimal("0.40"),
                    "api_calls": Decimal("0.0008"),
                    "storage_gb": Decimal("1.50"),
                    "integrations": Decimal("8.00"),
                },
                is_active=True,
                metadata={"target_audience": "professional_teams"},
            ),
            SubscriptionTier.ENTERPRISE: PricingTier(
                tier=SubscriptionTier.ENTERPRISE,
                name="Enterprise",
                description="Full-scale AI team orchestration for large organizations",
                monthly_price=Decimal("499.00"),
                annual_price=Decimal("4990.00"),  # 2 months free
                agent_hours_included=5000,
                max_concurrent_agents=100,
                max_team_members=50,
                api_calls_included=1000000,
                storage_gb_included=1000,
                integrations_included=50,
                features=[
                    "Unlimited custom agents",
                    "Enterprise integrations",
                    "Advanced security features",
                    "SSO & RBAC",
                    "Dedicated support",
                    "Custom training",
                    "SLA guarantees",
                    "Advanced analytics & reporting",
                ],
                overage_rates={
                    "agent_hours": Decimal("0.30"),
                    "api_calls": Decimal("0.0005"),
                    "storage_gb": Decimal("1.00"),
                    "integrations": Decimal("5.00"),
                },
                is_active=True,
                metadata={"target_audience": "enterprise"},
            ),
        }

    async def create_subscription(
        self,
        organization_id: str,
        tier: SubscriptionTier,
        billing_cycle: BillingCycle,
        billing_email: str,
        payment_method_id: Optional[str] = None,
        trial_days: int = 14,
        custom_limits: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new subscription"""

        subscription_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Calculate billing periods
        if billing_cycle == BillingCycle.MONTHLY:
            period_start = date.today()
            period_end = (
                period_start.replace(month=period_start.month + 1)
                if period_start.month < 12
                else period_start.replace(year=period_start.year + 1, month=1)
            )
        elif billing_cycle == BillingCycle.ANNUAL:
            period_start = date.today()
            period_end = period_start.replace(year=period_start.year + 1)
        else:
            # Quarterly or custom - default to monthly for now
            period_start = date.today()
            period_end = (
                period_start.replace(month=period_start.month + 1)
                if period_start.month < 12
                else period_start.replace(year=period_start.year + 1, month=1)
            )

        trial_end = (
            date.today() + timedelta(days=trial_days) if trial_days > 0 else None
        )

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO subscriptions (
                        id, organization_id, tier, status, billing_cycle,
                        current_period_start, current_period_end, trial_end,
                        quantity, custom_limits, billing_email, payment_method_id,
                        created_at, updated_at, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                """,
                    subscription_id,
                    organization_id,
                    tier.value,
                    SubscriptionStatus.TRIAL.value
                    if trial_end
                    else SubscriptionStatus.ACTIVE.value,
                    billing_cycle.value,
                    period_start,
                    period_end,
                    trial_end,
                    1,
                    json.dumps(custom_limits or {}),
                    billing_email,
                    payment_method_id,
                    now,
                    now,
                    json.dumps({"created_via": "api"}),
                )

            logger.info(
                f"Created subscription {subscription_id} for organization {organization_id}"
            )
            return subscription_id

        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise

    async def track_usage(
        self,
        organization_id: str,
        metric_type: UsageMetricType,
        value: Decimal,
        unit: str = "count",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track usage metrics for billing"""

        try:
            # Get current subscription
            async with self.db_pool.acquire() as conn:
                subscription = await conn.fetchrow(
                    """
                    SELECT id, current_period_start, current_period_end
                    FROM subscriptions 
                    WHERE organization_id = $1 AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                """,
                    organization_id,
                )

            if not subscription:
                logger.warning(
                    f"No active subscription found for organization {organization_id}"
                )
                return False

            billing_period = f"{subscription['current_period_start']}_{subscription['current_period_end']}"
            usage_id = str(uuid.uuid4())

            # Record usage
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO usage_records (
                        id, organization_id, subscription_id, metric_type,
                        value, unit, recorded_at, billing_period, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    usage_id,
                    organization_id,
                    subscription["id"],
                    metric_type.value,
                    value,
                    unit,
                    datetime.utcnow(),
                    billing_period,
                    json.dumps(metadata or {}),
                )

            # Check for usage limits and send alerts if needed
            await self._check_usage_limits(
                organization_id, subscription["id"], metric_type
            )

            return True

        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
            return False

    async def calculate_monthly_bill(
        self, organization_id: str, billing_period_start: date, billing_period_end: date
    ) -> Dict[str, Any]:
        """Calculate the monthly bill for an organization"""

        try:
            # Get subscription details
            async with self.db_pool.acquire() as conn:
                subscription = await conn.fetchrow(
                    """
                    SELECT * FROM subscriptions 
                    WHERE organization_id = $1 
                    AND current_period_start <= $2 
                    AND current_period_end >= $3
                    AND status IN ('active', 'trial')
                    ORDER BY created_at DESC LIMIT 1
                """,
                    organization_id,
                    billing_period_start,
                    billing_period_end,
                )

            if not subscription:
                return {"error": "No active subscription found for billing period"}

            tier_config = self.pricing_tiers[SubscriptionTier(subscription["tier"])]
            billing_period = f"{billing_period_start}_{billing_period_end}"

            # Get usage for billing period
            async with self.db_pool.acquire() as conn:
                usage_records = await conn.fetch(
                    """
                    SELECT metric_type, SUM(value) as total_usage
                    FROM usage_records
                    WHERE organization_id = $1 AND billing_period = $2
                    GROUP BY metric_type
                """,
                    organization_id,
                    billing_period,
                )

            usage_by_metric = {
                record["metric_type"]: Decimal(str(record["total_usage"]))
                for record in usage_records
            }

            # Calculate base subscription fee
            if subscription["billing_cycle"] == "monthly":
                base_amount = tier_config.monthly_price
            else:
                base_amount = tier_config.annual_price / 12  # Prorated monthly amount

            # Calculate overage charges
            overage_charges = {}
            total_overage = Decimal("0.00")

            for metric, usage in usage_by_metric.items():
                if metric == UsageMetricType.AGENT_HOURS.value:
                    included = tier_config.agent_hours_included
                    overage_rate = tier_config.overage_rates.get(
                        "agent_hours", Decimal("0.50")
                    )
                elif metric == UsageMetricType.API_CALLS.value:
                    included = tier_config.api_calls_included
                    overage_rate = tier_config.overage_rates.get(
                        "api_calls", Decimal("0.001")
                    )
                elif metric == UsageMetricType.STORAGE_GB.value:
                    included = tier_config.storage_gb_included
                    overage_rate = tier_config.overage_rates.get(
                        "storage_gb", Decimal("2.00")
                    )
                else:
                    continue  # Skip metrics without overage billing

                if usage > included:
                    overage = usage - included
                    overage_cost = overage * overage_rate
                    overage_charges[metric] = {
                        "included": included,
                        "used": float(usage),
                        "overage": float(overage),
                        "rate": float(overage_rate),
                        "cost": float(overage_cost),
                    }
                    total_overage += overage_cost

            # Calculate taxes (simplified - 8% for now)
            subtotal = base_amount + total_overage
            tax_rate = Decimal("0.08")
            tax_amount = (subtotal * tax_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_amount = subtotal + tax_amount

            return {
                "organization_id": organization_id,
                "subscription_id": subscription["id"],
                "billing_period": {
                    "start": billing_period_start,
                    "end": billing_period_end,
                },
                "tier": subscription["tier"],
                "base_subscription": float(base_amount),
                "usage_summary": {
                    metric: float(usage) for metric, usage in usage_by_metric.items()
                },
                "overage_charges": overage_charges,
                "subtotal": float(subtotal),
                "tax_amount": float(tax_amount),
                "total_amount": float(total_amount),
                "currency": "USD",
            }

        except Exception as e:
            logger.error(f"Error calculating bill for {organization_id}: {e}")
            return {"error": str(e)}

    async def generate_invoice(
        self, organization_id: str, billing_calculation: Dict[str, Any]
    ) -> str:
        """Generate an invoice from billing calculation"""

        try:
            invoice_id = str(uuid.uuid4())
            invoice_number = (
                f"INV-{datetime.now().strftime('%Y%m%d')}-{invoice_id[:8].upper()}"
            )

            # Create line items
            line_items = []

            # Base subscription line item
            line_items.append(
                {
                    "description": f"{billing_calculation['tier'].title()} Plan Subscription",
                    "quantity": 1,
                    "unit_price": billing_calculation["base_subscription"],
                    "amount": billing_calculation["base_subscription"],
                }
            )

            # Overage line items
            for metric, details in billing_calculation.get(
                "overage_charges", {}
            ).items():
                line_items.append(
                    {
                        "description": f"{metric.replace('_', ' ').title()} Overage ({details['overage']} units)",
                        "quantity": details["overage"],
                        "unit_price": details["rate"],
                        "amount": details["cost"],
                    }
                )

            due_date = date.today() + timedelta(days=30)

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO invoices (
                        id, organization_id, subscription_id, invoice_number,
                        amount_due, amount_paid, currency,
                        billing_period_start, billing_period_end, due_date,
                        status, line_items, tax_amount, discount_amount,
                        created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                """,
                    invoice_id,
                    organization_id,
                    billing_calculation["subscription_id"],
                    invoice_number,
                    Decimal(str(billing_calculation["total_amount"])),
                    Decimal("0.00"),
                    billing_calculation["currency"],
                    billing_calculation["billing_period"]["start"],
                    billing_calculation["billing_period"]["end"],
                    due_date,
                    PaymentStatus.PENDING.value,
                    json.dumps(line_items),
                    Decimal(str(billing_calculation["tax_amount"])),
                    Decimal("0.00"),
                    datetime.utcnow(),
                )

            logger.info(
                f"Generated invoice {invoice_number} for organization {organization_id}"
            )
            return invoice_id

        except Exception as e:
            logger.error(f"Error generating invoice: {e}")
            raise

    async def get_subscription_details(
        self, organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed subscription information for an organization"""

        try:
            async with self.db_pool.acquire() as conn:
                subscription = await conn.fetchrow(
                    """
                    SELECT * FROM subscriptions 
                    WHERE organization_id = $1 
                    AND status IN ('active', 'trial')
                    ORDER BY created_at DESC LIMIT 1
                """,
                    organization_id,
                )

            if not subscription:
                return None

            tier_config = self.pricing_tiers[SubscriptionTier(subscription["tier"])]

            # Get current usage
            billing_period = f"{subscription['current_period_start']}_{subscription['current_period_end']}"
            async with self.db_pool.acquire() as conn:
                current_usage = await conn.fetch(
                    """
                    SELECT metric_type, SUM(value) as total_usage
                    FROM usage_records
                    WHERE organization_id = $1 AND billing_period = $2
                    GROUP BY metric_type
                """,
                    organization_id,
                    billing_period,
                )

            usage_summary = {
                record["metric_type"]: float(record["total_usage"])
                for record in current_usage
            }

            return {
                "subscription": dict(subscription),
                "tier_config": asdict(tier_config),
                "current_usage": usage_summary,
                "usage_limits": {
                    "agent_hours": tier_config.agent_hours_included,
                    "max_concurrent_agents": tier_config.max_concurrent_agents,
                    "api_calls": tier_config.api_calls_included,
                    "storage_gb": tier_config.storage_gb_included,
                    "integrations": tier_config.integrations_included,
                },
            }

        except Exception as e:
            logger.error(f"Error getting subscription details: {e}")
            return None

    async def _check_usage_limits(
        self, organization_id: str, subscription_id: str, metric_type: UsageMetricType
    ):
        """Check if usage is approaching limits and send alerts"""

        try:
            # Get subscription tier
            async with self.db_pool.acquire() as conn:
                subscription = await conn.fetchrow(
                    """
                    SELECT tier, current_period_start, current_period_end
                    FROM subscriptions WHERE id = $1
                """,
                    subscription_id,
                )

            if not subscription:
                return

            tier_config = self.pricing_tiers[SubscriptionTier(subscription["tier"])]
            billing_period = f"{subscription['current_period_start']}_{subscription['current_period_end']}"

            # Get current usage for this metric
            async with self.db_pool.acquire() as conn:
                current_usage = await conn.fetchval(
                    """
                    SELECT COALESCE(SUM(value), 0)
                    FROM usage_records
                    WHERE organization_id = $1 
                    AND subscription_id = $2 
                    AND metric_type = $3
                    AND billing_period = $4
                """,
                    organization_id,
                    subscription_id,
                    metric_type.value,
                    billing_period,
                )

            # Check limits and send alerts at 80% and 100%
            limit = 0
            if metric_type == UsageMetricType.AGENT_HOURS:
                limit = tier_config.agent_hours_included
            elif metric_type == UsageMetricType.API_CALLS:
                limit = tier_config.api_calls_included
            elif metric_type == UsageMetricType.STORAGE_GB:
                limit = tier_config.storage_gb_included

            if limit > 0 and current_usage:
                usage_percent = float(current_usage) / limit * 100

                if usage_percent >= 80:
                    # Would send alert to organization
                    logger.info(
                        f"Usage alert: {organization_id} at {usage_percent:.1f}% of {metric_type.value} limit"
                    )

        except Exception as e:
            logger.error(f"Error checking usage limits: {e}")

    async def upgrade_subscription(
        self,
        organization_id: str,
        new_tier: SubscriptionTier,
        effective_date: Optional[date] = None,
    ) -> bool:
        """Upgrade a subscription to a higher tier"""

        try:
            if effective_date is None:
                effective_date = date.today()

            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE subscriptions 
                    SET tier = $2, updated_at = $3
                    WHERE organization_id = $1 
                    AND status IN ('active', 'trial')
                """,
                    organization_id,
                    new_tier.value,
                    datetime.utcnow(),
                )

            if result == "UPDATE 1":
                logger.info(
                    f"Upgraded subscription for {organization_id} to {new_tier.value}"
                )
                return True
            else:
                logger.warning(
                    f"No subscription found to upgrade for {organization_id}"
                )
                return False

        except Exception as e:
            logger.error(f"Error upgrading subscription: {e}")
            return False
