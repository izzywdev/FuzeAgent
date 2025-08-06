-- Migration: Tiered Pricing and Billing System
-- This migration creates tables for managing subscription tiers, usage tracking,
-- billing calculations, and payment processing for the FuzeAgent platform

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Subscriptions - Customer subscription information
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Subscription Details
    tier VARCHAR(50) NOT NULL DEFAULT 'starter', -- starter, professional, enterprise, custom
    status VARCHAR(50) NOT NULL DEFAULT 'trial', -- active, trial, suspended, cancelled, past_due, expired
    billing_cycle VARCHAR(50) NOT NULL DEFAULT 'monthly', -- monthly, quarterly, annual, custom
    
    -- Billing Periods
    current_period_start DATE NOT NULL,
    current_period_end DATE NOT NULL,
    trial_end DATE, -- End of trial period if applicable
    
    -- Subscription Configuration
    quantity INTEGER DEFAULT 1, -- Number of seats/licenses
    custom_limits JSONB DEFAULT '{}', -- Custom limits for enterprise plans
    
    -- Billing Information
    billing_email VARCHAR(255) NOT NULL,
    payment_method_id VARCHAR(255), -- Reference to payment method
    
    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT valid_tier CHECK (tier IN ('starter', 'professional', 'enterprise', 'custom')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'trial', 'suspended', 'cancelled', 'past_due', 'expired')),
    CONSTRAINT valid_billing_cycle CHECK (billing_cycle IN ('monthly', 'quarterly', 'annual', 'custom')),
    CONSTRAINT valid_quantity CHECK (quantity >= 1),
    CONSTRAINT valid_period CHECK (current_period_end > current_period_start)
);

-- Usage Records - Track usage metrics for billing
CREATE TABLE IF NOT EXISTS usage_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    
    -- Usage Details
    metric_type VARCHAR(100) NOT NULL, -- agent_hours, api_calls, tasks_executed, storage_gb, etc.
    value DECIMAL(15,4) NOT NULL, -- Usage amount
    unit VARCHAR(50) NOT NULL DEFAULT 'count', -- Unit of measurement
    
    -- Timing
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    billing_period VARCHAR(100) NOT NULL, -- e.g., "2025-08-01_2025-08-31"
    
    -- Additional Context
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT positive_value CHECK (value >= 0)
);

-- Invoices - Generated billing invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    
    -- Invoice Details
    invoice_number VARCHAR(100) NOT NULL UNIQUE,
    amount_due DECIMAL(12,2) NOT NULL,
    amount_paid DECIMAL(12,2) DEFAULT 0.00,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Billing Period
    billing_period_start DATE NOT NULL,
    billing_period_end DATE NOT NULL,
    due_date DATE NOT NULL,
    
    -- Payment Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, completed, failed, refunded, partially_refunded
    
    -- Invoice Items
    line_items JSONB NOT NULL, -- Array of line items with descriptions and amounts
    tax_amount DECIMAL(12,2) DEFAULT 0.00,
    discount_amount DECIMAL(12,2) DEFAULT 0.00,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    paid_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'completed', 'failed', 'refunded', 'partially_refunded')),
    CONSTRAINT non_negative_amounts CHECK (amount_due >= 0 AND amount_paid >= 0 AND tax_amount >= 0 AND discount_amount >= 0),
    CONSTRAINT valid_billing_period CHECK (billing_period_end > billing_period_start)
);

-- Payment Transactions - Track payment attempts and results
CREATE TABLE IF NOT EXISTS payment_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Transaction Details
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(100), -- credit_card, bank_transfer, paypal, etc.
    payment_processor VARCHAR(100), -- stripe, paypal, square, etc.
    processor_transaction_id VARCHAR(255), -- External transaction ID
    
    -- Transaction Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, completed, failed, refunded
    failure_reason TEXT,
    
    -- Timestamps
    initiated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    CONSTRAINT positive_amount CHECK (amount > 0)
);

-- Pricing Tiers - Define available subscription tiers and their limits
CREATE TABLE IF NOT EXISTS pricing_tiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tier VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Pricing
    monthly_price DECIMAL(10,2) NOT NULL,
    annual_price DECIMAL(10,2) NOT NULL,
    
    -- Included Limits
    agent_hours_included INTEGER DEFAULT 0,
    max_concurrent_agents INTEGER DEFAULT 1,
    max_team_members INTEGER DEFAULT 1,
    api_calls_included INTEGER DEFAULT 0,
    storage_gb_included INTEGER DEFAULT 0,
    integrations_included INTEGER DEFAULT 0,
    
    -- Features
    features JSONB DEFAULT '[]', -- Array of included features
    overage_rates JSONB DEFAULT '{}', -- Rates for usage beyond included amounts
    
    -- Configuration
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT positive_prices CHECK (monthly_price >= 0 AND annual_price >= 0),
    CONSTRAINT non_negative_limits CHECK (
        agent_hours_included >= 0 AND 
        max_concurrent_agents >= 0 AND 
        max_team_members >= 0 AND 
        api_calls_included >= 0 AND 
        storage_gb_included >= 0 AND 
        integrations_included >= 0
    )
);

-- Subscription History - Track subscription changes
CREATE TABLE IF NOT EXISTS subscription_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    
    -- Change Details
    change_type VARCHAR(100) NOT NULL, -- created, upgraded, downgraded, cancelled, renewed
    previous_tier VARCHAR(50),
    new_tier VARCHAR(50),
    change_reason TEXT,
    
    -- Financial Impact
    proration_amount DECIMAL(12,2), -- Amount credited/charged for tier changes
    effective_date DATE NOT NULL,
    
    -- Audit
    changed_by VARCHAR(255), -- User or system that made the change
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Billing Alerts - Track usage alerts and billing notifications
CREATE TABLE IF NOT EXISTS billing_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    
    -- Alert Details
    alert_type VARCHAR(100) NOT NULL, -- usage_warning, usage_exceeded, payment_failed, trial_ending
    metric_type VARCHAR(100), -- Which usage metric triggered the alert
    threshold_percentage DECIMAL(5,2), -- e.g., 80.00 for 80% threshold
    current_usage DECIMAL(15,4),
    usage_limit DECIMAL(15,4),
    
    -- Alert Status
    status VARCHAR(50) DEFAULT 'sent', -- sent, acknowledged, dismissed
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    
    -- Message Content
    alert_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_subscriptions_organization ON subscriptions(organization_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_period ON subscriptions(current_period_start, current_period_end);

CREATE INDEX IF NOT EXISTS idx_usage_records_organization ON usage_records(organization_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_subscription ON usage_records(subscription_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_metric_type ON usage_records(metric_type);
CREATE INDEX IF NOT EXISTS idx_usage_records_billing_period ON usage_records(billing_period);
CREATE INDEX IF NOT EXISTS idx_usage_records_recorded_at ON usage_records(recorded_at);

CREATE INDEX IF NOT EXISTS idx_invoices_organization ON invoices(organization_id);
CREATE INDEX IF NOT EXISTS idx_invoices_subscription ON invoices(subscription_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_invoice ON payment_transactions(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_organization ON payment_transactions(organization_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON payment_transactions(status);

CREATE INDEX IF NOT EXISTS idx_subscription_history_subscription ON subscription_history(subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_history_date ON subscription_history(effective_date);

CREATE INDEX IF NOT EXISTS idx_billing_alerts_organization ON billing_alerts(organization_id);
CREATE INDEX IF NOT EXISTS idx_billing_alerts_status ON billing_alerts(status);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pricing_tiers_updated_at BEFORE UPDATE ON pricing_tiers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default pricing tiers
INSERT INTO pricing_tiers (
    tier, name, description, monthly_price, annual_price,
    agent_hours_included, max_concurrent_agents, max_team_members,
    api_calls_included, storage_gb_included, integrations_included,
    features, overage_rates, sort_order
) VALUES
(
    'starter', 'Starter', 
    'Perfect for individual developers and small teams getting started with AI automation',
    29.00, 290.00, 100, 5, 3, 10000, 10, 3,
    '["Basic AI agent creation", "Task automation", "Standard integrations", "Email support", "Basic analytics"]',
    '{"agent_hours": 0.50, "api_calls": 0.001, "storage_gb": 2.00, "integrations": 10.00}',
    1
),
(
    'professional', 'Professional',
    'Advanced features for growing teams and professional workflows', 
    99.00, 990.00, 500, 25, 10, 100000, 100, 10,
    '["Advanced AI agent templates", "Custom workflows", "Priority integrations", "Advanced analytics", "Phone & email support", "Team collaboration tools", "API access"]',
    '{"agent_hours": 0.40, "api_calls": 0.0008, "storage_gb": 1.50, "integrations": 8.00}',
    2
),
(
    'enterprise', 'Enterprise',
    'Full-scale AI team orchestration for large organizations',
    499.00, 4990.00, 5000, 100, 50, 1000000, 1000, 50,
    '["Unlimited custom agents", "Enterprise integrations", "Advanced security features", "SSO & RBAC", "Dedicated support", "Custom training", "SLA guarantees", "Advanced analytics & reporting"]',
    '{"agent_hours": 0.30, "api_calls": 0.0005, "storage_gb": 1.00, "integrations": 5.00}',
    3
)
ON CONFLICT (tier) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    monthly_price = EXCLUDED.monthly_price,
    annual_price = EXCLUDED.annual_price,
    agent_hours_included = EXCLUDED.agent_hours_included,
    max_concurrent_agents = EXCLUDED.max_concurrent_agents,
    max_team_members = EXCLUDED.max_team_members,
    api_calls_included = EXCLUDED.api_calls_included,
    storage_gb_included = EXCLUDED.storage_gb_included,
    integrations_included = EXCLUDED.integrations_included,
    features = EXCLUDED.features,
    overage_rates = EXCLUDED.overage_rates,
    sort_order = EXCLUDED.sort_order,
    updated_at = NOW();