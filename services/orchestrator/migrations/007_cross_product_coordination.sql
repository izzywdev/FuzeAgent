-- Migration: Cross-Product Coordination System
-- This migration creates tables for managing coordination between different WCG products
-- Enables centralized coordination, resource sharing, and conflict resolution

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Product Registry - Track all products in the WCG ecosystem
CREATE TABLE IF NOT EXISTS product_registry (
    id VARCHAR(100) PRIMARY KEY, -- e.g., 'fuze_agent', 'fuze_front', 'hub_hit'
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    endpoints JSONB DEFAULT '[]', -- API endpoints exposed by this product
    dependencies JSONB DEFAULT '[]', -- Other products this depends on
    resource_requirements JSONB DEFAULT '{}', -- Infrastructure/resource needs
    team_contacts JSONB DEFAULT '[]', -- Contact information for team members
    priority_level INTEGER NOT NULL DEFAULT 5, -- 1-10 scale, business importance
    metadata JSONB DEFAULT '{}',
    
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_priority CHECK (priority_level >= 1 AND priority_level <= 10)
);

-- Coordination Requests - Cross-product coordination requests
CREATE TABLE IF NOT EXISTS coordination_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requesting_product VARCHAR(100) NOT NULL REFERENCES product_registry(id),
    target_products JSONB NOT NULL, -- Array of product IDs
    coordination_type VARCHAR(100) NOT NULL, -- e.g., 'resource_sharing', 'deployment', 'data_sync'
    
    scope VARCHAR(50) NOT NULL DEFAULT 'product_group', -- global, product_group, bilateral, team_level
    priority VARCHAR(50) NOT NULL DEFAULT 'medium', -- critical, high, medium, low
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, in_progress, resolved, escalated, cancelled
    
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    resource_requirements JSONB DEFAULT '{}',
    impact_assessment JSONB DEFAULT '{}', -- Risk analysis and impact data
    proposed_timeline JSONB DEFAULT '{}', -- Timeline for coordination
    stakeholders JSONB DEFAULT '[]', -- List of stakeholder IDs
    dependencies JSONB DEFAULT '[]', -- Dependencies for this coordination
    
    resolution_plan JSONB, -- Plan for resolving the coordination
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_scope CHECK (scope IN ('global', 'product_group', 'bilateral', 'team_level')),
    CONSTRAINT valid_priority CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'resolved', 'escalated', 'cancelled'))
);

-- Resource Allocations - Track resource usage across products
CREATE TABLE IF NOT EXISTS resource_allocations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id VARCHAR(100) NOT NULL REFERENCES product_registry(id),
    resource_type VARCHAR(100) NOT NULL, -- infrastructure, api_endpoints, data_sources, etc.
    resource_name VARCHAR(255) NOT NULL,
    allocation_details JSONB DEFAULT '{}',
    
    allocated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    valid_until TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, reserved, released
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'reserved', 'released')),
    UNIQUE(resource_type, resource_name) -- Prevent double allocation
);

-- Coordination History - Audit trail of coordination activities
CREATE TABLE IF NOT EXISTS coordination_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coordination_request_id UUID REFERENCES coordination_requests(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL, -- created, updated, resolved, escalated
    actor_id VARCHAR(255), -- Who performed the action
    actor_type VARCHAR(50) DEFAULT 'agent', -- agent, human, system
    
    details JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Product Dependencies - Track dependencies between products
CREATE TABLE IF NOT EXISTS product_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dependent_product VARCHAR(100) NOT NULL REFERENCES product_registry(id),
    dependency_product VARCHAR(100) NOT NULL REFERENCES product_registry(id),
    dependency_type VARCHAR(100) NOT NULL, -- api, data, infrastructure, deployment
    
    is_critical BOOLEAN DEFAULT false,
    version_constraint VARCHAR(100), -- Version requirement for dependency
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(dependent_product, dependency_product, dependency_type),
    CONSTRAINT no_self_dependency CHECK (dependent_product != dependency_product)
);

-- Coordination Protocols - Define standard coordination procedures
CREATE TABLE IF NOT EXISTS coordination_protocols (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    protocol_name VARCHAR(255) NOT NULL UNIQUE,
    coordination_type VARCHAR(100) NOT NULL,
    scope VARCHAR(50) NOT NULL,
    
    procedure_steps JSONB NOT NULL, -- Step-by-step coordination procedure
    required_approvals JSONB DEFAULT '[]', -- Who needs to approve
    sla_requirements JSONB DEFAULT '{}', -- Service level agreements
    escalation_rules JSONB DEFAULT '{}', -- When and how to escalate
    
    is_active BOOLEAN DEFAULT true,
    version VARCHAR(20) DEFAULT '1.0',
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cross-Product Events - Track significant events across products
CREATE TABLE IF NOT EXISTS cross_product_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL, -- deployment, incident, maintenance, update
    source_product VARCHAR(100) NOT NULL REFERENCES product_registry(id),
    affected_products JSONB DEFAULT '[]', -- Products affected by this event
    
    title TEXT NOT NULL,
    description TEXT,
    severity VARCHAR(50) DEFAULT 'info', -- critical, high, medium, low, info
    
    event_data JSONB DEFAULT '{}',
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_severity CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_coordination_requests_status ON coordination_requests(status);
CREATE INDEX IF NOT EXISTS idx_coordination_requests_priority ON coordination_requests(priority);
CREATE INDEX IF NOT EXISTS idx_coordination_requests_requesting_product ON coordination_requests(requesting_product);
CREATE INDEX IF NOT EXISTS idx_coordination_requests_created_at ON coordination_requests(created_at);

CREATE INDEX IF NOT EXISTS idx_resource_allocations_product ON resource_allocations(product_id);
CREATE INDEX IF NOT EXISTS idx_resource_allocations_type ON resource_allocations(resource_type);
CREATE INDEX IF NOT EXISTS idx_resource_allocations_status ON resource_allocations(status);

CREATE INDEX IF NOT EXISTS idx_coordination_history_request ON coordination_history(coordination_request_id);
CREATE INDEX IF NOT EXISTS idx_coordination_history_timestamp ON coordination_history(timestamp);

CREATE INDEX IF NOT EXISTS idx_product_dependencies_dependent ON product_dependencies(dependent_product);
CREATE INDEX IF NOT EXISTS idx_product_dependencies_dependency ON product_dependencies(dependency_product);

CREATE INDEX IF NOT EXISTS idx_cross_product_events_type ON cross_product_events(event_type);
CREATE INDEX IF NOT EXISTS idx_cross_product_events_source ON cross_product_events(source_product);
CREATE INDEX IF NOT EXISTS idx_cross_product_events_severity ON cross_product_events(severity);

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_product_registry_updated_at BEFORE UPDATE ON product_registry FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_coordination_requests_updated_at BEFORE UPDATE ON coordination_requests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_resource_allocations_updated_at BEFORE UPDATE ON resource_allocations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_product_dependencies_updated_at BEFORE UPDATE ON product_dependencies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_coordination_protocols_updated_at BEFORE UPDATE ON coordination_protocols FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial WCG products
INSERT INTO product_registry (id, name, version, priority_level, metadata) VALUES
('fuze_agent', 'FuzeAgent', '1.0.0', 10, '{"description": "AI team orchestration platform", "category": "ai_tools"}'),
('fuze_front', 'FuzeFront', '2.1.0', 9, '{"description": "Frontend platform with module federation", "category": "frontend"}'),
('hub_hit', 'HubHit', '1.5.0', 8, '{"description": "Admin portals and management interfaces", "category": "admin"}'),
('deploy_ai', 'DeployAI', '1.2.0', 8, '{"description": "AI-powered deployment automation", "category": "devops"}'),
('fuze_picker', 'FuzePicker', '1.0.0', 7, '{"description": "Asset and resource picker tools", "category": "utilities"}'),
('fuze_infra', 'FuzeInfra', '3.0.0', 10, '{"description": "Shared infrastructure and services", "category": "infrastructure"}')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    version = EXCLUDED.version,
    priority_level = EXCLUDED.priority_level,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();

-- Insert initial coordination protocols
INSERT INTO coordination_protocols (protocol_name, coordination_type, scope, procedure_steps, required_approvals, sla_requirements) VALUES
('Standard Deployment Coordination', 'deployment', 'product_group', 
 '{"steps": ["notify_stakeholders", "resource_check", "impact_assessment", "approval", "execution", "verification"]}',
 '["technical_lead", "product_owner"]',
 '{"response_time": "2_hours", "resolution_time": "24_hours"}'),
 
('Emergency Incident Response', 'incident', 'global',
 '{"steps": ["incident_declaration", "stakeholder_alert", "impact_assessment", "mitigation_plan", "execution", "post_mortem"]}',
 '["incident_commander", "executive_approval"]',
 '{"response_time": "15_minutes", "resolution_time": "4_hours"}'),
 
('Resource Sharing Request', 'resource_sharing', 'bilateral',
 '{"steps": ["resource_assessment", "impact_analysis", "approval_request", "implementation", "monitoring"]}',
 '["resource_owner", "technical_lead"]',
 '{"response_time": "4_hours", "resolution_time": "48_hours"}')
ON CONFLICT (protocol_name) DO NOTHING;