-- Database schema extensions for Model Configuration and API Key Management

-- Organization-level provider credentials
CREATE TABLE IF NOT EXISTS organization_provider_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL,
    encrypted_api_key TEXT NOT NULL,
    endpoint_url TEXT,
    additional_config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(organization_id, provider)
);

-- Agent-specific model configurations
CREATE TABLE IF NOT EXISTS agent_model_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    primary_model VARCHAR(100) NOT NULL,
    fallback_models JSONB DEFAULT '[]',
    temperature DECIMAL(3,2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    top_p DECIMAL(3,2) DEFAULT 1.0,
    frequency_penalty DECIMAL(3,2) DEFAULT 0.0,
    presence_penalty DECIMAL(3,2) DEFAULT 0.0,
    custom_instructions TEXT DEFAULT '',
    use_function_calling BOOLEAN DEFAULT true,
    streaming_enabled BOOLEAN DEFAULT true,
    cost_limit_per_task DECIMAL(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id)
);

-- Model usage tracking
CREATE TABLE IF NOT EXISTS model_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    agent_id UUID REFERENCES agents(id),
    task_id UUID REFERENCES tasks(id),
    model_id VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
    cost_usd DECIMAL(10,6) NOT NULL DEFAULT 0,
    completion_time_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Model usage aggregates (for performance)
CREATE TABLE IF NOT EXISTS model_usage_daily_aggregates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    agent_id UUID,
    model_id VARCHAR(100),
    provider VARCHAR(50),
    usage_date DATE NOT NULL,
    total_requests INTEGER DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(12,6) DEFAULT 0,
    avg_completion_time_ms INTEGER,
    success_rate DECIMAL(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, agent_id, model_id, provider, usage_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_org_provider_creds_org_provider 
ON organization_provider_credentials(organization_id, provider);

CREATE INDEX IF NOT EXISTS idx_agent_model_config_agent 
ON agent_model_configurations(agent_id);

CREATE INDEX IF NOT EXISTS idx_model_usage_org_timestamp 
ON model_usage_logs(organization_id, request_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_model_usage_agent_timestamp 
ON model_usage_logs(agent_id, request_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_model_usage_task 
ON model_usage_logs(task_id);

CREATE INDEX IF NOT EXISTS idx_usage_aggregates_org_date 
ON model_usage_daily_aggregates(organization_id, usage_date DESC);

-- Functions for updating aggregates
CREATE OR REPLACE FUNCTION update_model_usage_aggregates()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO model_usage_daily_aggregates (
        organization_id, agent_id, model_id, provider, usage_date,
        total_requests, total_input_tokens, total_output_tokens, 
        total_tokens, total_cost_usd, avg_completion_time_ms, success_rate
    )
    VALUES (
        NEW.organization_id, NEW.agent_id, NEW.model_id, NEW.provider, 
        DATE(NEW.request_timestamp),
        1, NEW.input_tokens, NEW.output_tokens, NEW.total_tokens, NEW.cost_usd,
        NEW.completion_time_ms, CASE WHEN NEW.success THEN 1.0 ELSE 0.0 END
    )
    ON CONFLICT (organization_id, agent_id, model_id, provider, usage_date)
    DO UPDATE SET
        total_requests = model_usage_daily_aggregates.total_requests + 1,
        total_input_tokens = model_usage_daily_aggregates.total_input_tokens + NEW.input_tokens,
        total_output_tokens = model_usage_daily_aggregates.total_output_tokens + NEW.output_tokens,
        total_tokens = model_usage_daily_aggregates.total_tokens + NEW.total_tokens,
        total_cost_usd = model_usage_daily_aggregates.total_cost_usd + NEW.cost_usd,
        avg_completion_time_ms = CASE 
            WHEN NEW.completion_time_ms IS NOT NULL 
            THEN COALESCE(
                (model_usage_daily_aggregates.avg_completion_time_ms * (model_usage_daily_aggregates.total_requests - 1) + NEW.completion_time_ms) / model_usage_daily_aggregates.total_requests,
                NEW.completion_time_ms
            )
            ELSE model_usage_daily_aggregates.avg_completion_time_ms
        END,
        success_rate = (
            model_usage_daily_aggregates.success_rate * (model_usage_daily_aggregates.total_requests - 1) + 
            CASE WHEN NEW.success THEN 1.0 ELSE 0.0 END
        ) / model_usage_daily_aggregates.total_requests,
        updated_at = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for automatic aggregate updates
DROP TRIGGER IF EXISTS trigger_update_model_usage_aggregates ON model_usage_logs;
CREATE TRIGGER trigger_update_model_usage_aggregates
    AFTER INSERT ON model_usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_model_usage_aggregates();

-- Views for easier querying
CREATE OR REPLACE VIEW organization_model_usage_summary AS
SELECT 
    o.id as organization_id,
    o.name as organization_name,
    COUNT(DISTINCT a.id) as active_agents,
    COUNT(DISTINCT mul.model_id) as models_used,
    SUM(muda.total_requests) as total_requests_30d,
    SUM(muda.total_tokens) as total_tokens_30d,
    SUM(muda.total_cost_usd) as total_cost_30d,
    AVG(muda.success_rate) as avg_success_rate_30d
FROM organizations o
LEFT JOIN agents a ON o.id = a.organization_id
LEFT JOIN model_usage_logs mul ON a.id = mul.agent_id
LEFT JOIN model_usage_daily_aggregates muda ON (
    o.id = muda.organization_id 
    AND muda.usage_date >= CURRENT_DATE - INTERVAL '30 days'
)
GROUP BY o.id, o.name;

CREATE OR REPLACE VIEW agent_model_usage_summary AS
SELECT 
    a.id as agent_id,
    a.name as agent_name,
    a.type as agent_type,
    amc.primary_model,
    COUNT(mul.id) as total_requests_30d,
    SUM(mul.total_tokens) as total_tokens_30d,
    SUM(mul.cost_usd) as total_cost_30d,
    AVG(CASE WHEN mul.success THEN 1.0 ELSE 0.0 END) as success_rate_30d,
    AVG(mul.completion_time_ms) as avg_completion_time_ms
FROM agents a
LEFT JOIN agent_model_configurations amc ON a.id = amc.agent_id
LEFT JOIN model_usage_logs mul ON (
    a.id = mul.agent_id 
    AND mul.request_timestamp >= NOW() - INTERVAL '30 days'
)
GROUP BY a.id, a.name, a.type, amc.primary_model;