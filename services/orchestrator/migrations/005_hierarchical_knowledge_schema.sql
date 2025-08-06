-- Migration: Hierarchical Knowledge Management Schema
-- This adds organization-level, team-level, and cross-hierarchy knowledge management

-- Enable vector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Organization-level knowledge base
CREATE TABLE IF NOT EXISTS organization_knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text' CHECK (content_type IN ('text', 'code', 'documentation', 'procedure', 'best_practice')),
    knowledge_category VARCHAR(100) NOT NULL, -- 'development', 'infrastructure', 'business', 'security', etc.
    
    -- Vector embedding for semantic search
    embedding vector(384),
    
    -- Source information
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('agent_contribution', 'team_aggregation', 'manual_entry', 'task_outcome', 'external_import')),
    source_agent_id UUID,
    source_team_id UUID,
    source_task_id UUID,
    source_reference TEXT,
    
    -- Relevance and quality metrics
    relevance_score FLOAT DEFAULT 0.5 CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    quality_score FLOAT DEFAULT 0.5 CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    usage_count INTEGER DEFAULT 0,
    success_correlation FLOAT DEFAULT 0.0, -- How often using this knowledge leads to success
    
    -- Access control and visibility
    visibility_level VARCHAR(20) DEFAULT 'organization' CHECK (visibility_level IN ('organization', 'team', 'agent', 'public')),
    access_teams UUID[], -- Specific teams that can access this knowledge
    access_agents UUID[], -- Specific agents that can access this knowledge
    
    -- Metadata and context
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    related_knowledge_ids UUID[],
    
    -- Temporal information
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE, -- For time-sensitive knowledge
    
    -- Constraints
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (source_agent_id) REFERENCES agents(id) ON DELETE SET NULL,
    FOREIGN KEY (source_team_id) REFERENCES teams(id) ON DELETE SET NULL,
    FOREIGN KEY (source_task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Team-level knowledge aggregates
CREATE TABLE IF NOT EXISTS team_knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text',
    knowledge_category VARCHAR(100) NOT NULL,
    
    -- Vector embedding
    embedding vector(384),
    
    -- Source tracking
    source_type VARCHAR(50) NOT NULL,
    contributing_agents UUID[], -- Agents that contributed to this knowledge
    source_knowledge_ids UUID[], -- Organization knowledge that contributed
    aggregation_method VARCHAR(50) DEFAULT 'synthesis', -- How this knowledge was created
    
    -- Quality and relevance
    team_relevance_score FLOAT DEFAULT 0.5,
    agent_adoption_rate FLOAT DEFAULT 0.0, -- How many team agents use this knowledge
    effectiveness_score FLOAT DEFAULT 0.0, -- How effective this knowledge is for the team
    
    -- Access and visibility
    visibility_level VARCHAR(20) DEFAULT 'team',
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    
    -- Temporal
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Knowledge propagation tracking
CREATE TABLE IF NOT EXISTS knowledge_propagation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('agent', 'team', 'organization')),
    source_id UUID NOT NULL,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('agent', 'team', 'organization')),
    target_id UUID NOT NULL,
    
    knowledge_type VARCHAR(50) NOT NULL,
    knowledge_content_id UUID, -- References the actual knowledge record
    
    -- Propagation details
    propagation_method VARCHAR(50) NOT NULL, -- 'automatic', 'manual', 'triggered'
    propagation_trigger VARCHAR(100), -- What triggered the propagation
    confidence_score FLOAT DEFAULT 0.5,
    
    -- Outcome tracking
    propagation_status VARCHAR(20) DEFAULT 'pending' CHECK (propagation_status IN ('pending', 'processing', 'completed', 'failed', 'rejected')),
    acceptance_status VARCHAR(20) DEFAULT 'pending' CHECK (acceptance_status IN ('pending', 'accepted', 'rejected', 'modified')),
    rejection_reason TEXT,
    
    -- Impact metrics
    usage_after_propagation INTEGER DEFAULT 0,
    success_impact_score FLOAT DEFAULT 0.0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Temporal
    propagated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Knowledge notifications and alerts
CREATE TABLE IF NOT EXISTS knowledge_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_type VARCHAR(20) NOT NULL CHECK (recipient_type IN ('agent', 'team', 'organization', 'user')),
    recipient_id UUID NOT NULL,
    
    notification_type VARCHAR(50) NOT NULL CHECK (notification_type IN (
        'new_knowledge', 'knowledge_update', 'knowledge_conflict', 'knowledge_expiry',
        'relevant_knowledge', 'knowledge_request', 'knowledge_feedback'
    )),
    
    title VARCHAR(300) NOT NULL,
    message TEXT NOT NULL,
    
    -- Related knowledge
    knowledge_id UUID,
    knowledge_type VARCHAR(50), -- 'organization', 'team', 'agent'
    
    -- Priority and urgency
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    requires_action BOOLEAN DEFAULT false,
    
    -- Status
    status VARCHAR(20) DEFAULT 'unread' CHECK (status IN ('unread', 'read', 'acknowledged', 'acted_upon', 'dismissed')),
    
    -- Action information
    suggested_actions JSONB DEFAULT '[]',
    action_taken JSONB,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Temporal
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    read_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Knowledge relationships and dependencies
CREATE TABLE IF NOT EXISTS knowledge_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_knowledge_id UUID NOT NULL,
    source_knowledge_type VARCHAR(20) NOT NULL, -- 'organization', 'team', 'agent'
    target_knowledge_id UUID NOT NULL,
    target_knowledge_type VARCHAR(20) NOT NULL,
    
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN (
        'depends_on', 'builds_upon', 'conflicts_with', 'supersedes', 
        'complements', 'derived_from', 'similar_to'
    )),
    
    strength FLOAT DEFAULT 0.5 CHECK (strength >= 0.0 AND strength <= 1.0),
    confidence FLOAT DEFAULT 0.5 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verified_at TIMESTAMP WITH TIME ZONE
);

-- Extend existing agent_memory table to support hierarchical knowledge
ALTER TABLE agent_memory 
ADD COLUMN IF NOT EXISTS organization_context_id UUID,
ADD COLUMN IF NOT EXISTS team_context_id UUID,
ADD COLUMN IF NOT EXISTS knowledge_contribution_score FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS propagated_to_team BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS propagated_to_org BOOLEAN DEFAULT FALSE;

-- Knowledge analytics and metrics
CREATE TABLE IF NOT EXISTS knowledge_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    team_id UUID,
    agent_id UUID,
    
    metric_type VARCHAR(50) NOT NULL, -- 'usage', 'effectiveness', 'propagation', 'quality'
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(20),
    
    -- Context
    knowledge_category VARCHAR(100),
    time_period VARCHAR(20) DEFAULT 'daily', -- 'hourly', 'daily', 'weekly', 'monthly'
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_org_knowledge_org_id ON organization_knowledge_base(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_knowledge_category ON organization_knowledge_base(knowledge_category);
CREATE INDEX IF NOT EXISTS idx_org_knowledge_source_type ON organization_knowledge_base(source_type);
CREATE INDEX IF NOT EXISTS idx_org_knowledge_tags ON organization_knowledge_base USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_org_knowledge_created_at ON organization_knowledge_base(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_org_knowledge_usage_count ON organization_knowledge_base(usage_count DESC);
CREATE INDEX IF NOT EXISTS idx_org_knowledge_relevance ON organization_knowledge_base(relevance_score DESC);

-- Vector similarity indexes (using HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_org_knowledge_embedding ON organization_knowledge_base 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_team_knowledge_team_id ON team_knowledge_base(team_id);
CREATE INDEX IF NOT EXISTS idx_team_knowledge_org_id ON team_knowledge_base(organization_id);
CREATE INDEX IF NOT EXISTS idx_team_knowledge_embedding ON team_knowledge_base 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_knowledge_propagation_source ON knowledge_propagation_log(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_propagation_target ON knowledge_propagation_log(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_propagation_status ON knowledge_propagation_log(propagation_status);

CREATE INDEX IF NOT EXISTS idx_knowledge_notifications_recipient ON knowledge_notifications(recipient_type, recipient_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_notifications_type ON knowledge_notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_notifications_status ON knowledge_notifications(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_notifications_created ON knowledge_notifications(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_source ON knowledge_relationships(source_knowledge_id, source_knowledge_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_target ON knowledge_relationships(target_knowledge_id, target_knowledge_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_relationships_type ON knowledge_relationships(relationship_type);

CREATE INDEX IF NOT EXISTS idx_knowledge_analytics_org ON knowledge_analytics(organization_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_analytics_team ON knowledge_analytics(team_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_analytics_agent ON knowledge_analytics(agent_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_knowledge_analytics_type ON knowledge_analytics(metric_type, metric_name);

-- Create functions for knowledge management operations

-- Function to calculate knowledge relevance score
CREATE OR REPLACE FUNCTION calculate_knowledge_relevance(
    knowledge_id UUID,
    context_metadata JSONB
) RETURNS FLOAT AS $$
DECLARE
    base_score FLOAT;
    usage_factor FLOAT;
    recency_factor FLOAT;
    success_factor FLOAT;
    final_score FLOAT;
BEGIN
    -- Get base knowledge metrics
    SELECT 
        COALESCE(relevance_score, 0.5),
        COALESCE(usage_count, 0),
        EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0, -- Days old
        COALESCE(success_correlation, 0.0)
    INTO base_score, usage_factor, recency_factor, success_factor
    FROM organization_knowledge_base 
    WHERE id = knowledge_id;
    
    -- Calculate weighted relevance score
    final_score := base_score * 0.4 + 
                   LEAST(usage_factor / 10.0, 1.0) * 0.3 +  -- Usage factor (capped at 1.0)
                   (1.0 - LEAST(recency_factor / 365.0, 1.0)) * 0.2 +  -- Recency factor
                   success_factor * 0.1;
    
    RETURN LEAST(final_score, 1.0);
END;
$$ LANGUAGE plpgsql;

-- Function to propagate agent knowledge to team level
CREATE OR REPLACE FUNCTION propagate_agent_knowledge_to_team(
    agent_memory_id UUID,
    team_id_param UUID
) RETURNS UUID AS $$
DECLARE
    new_team_knowledge_id UUID;
    agent_mem RECORD;
    existing_similar UUID;
BEGIN
    -- Get agent memory details
    SELECT * INTO agent_mem FROM agent_memory WHERE id = agent_memory_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Agent memory not found: %', agent_memory_id;
    END IF;
    
    -- Check for similar existing team knowledge (simple content similarity)
    SELECT id INTO existing_similar 
    FROM team_knowledge_base 
    WHERE team_id = team_id_param 
      AND similarity(content, agent_mem.content) > 0.8
    LIMIT 1;
    
    IF existing_similar IS NOT NULL THEN
        -- Update existing knowledge instead of creating duplicate
        UPDATE team_knowledge_base 
        SET usage_count = usage_count + 1,
            contributing_agents = array_append(contributing_agents, agent_mem.agent_id),
            updated_at = NOW()
        WHERE id = existing_similar;
        
        RETURN existing_similar;
    END IF;
    
    -- Create new team knowledge entry
    INSERT INTO team_knowledge_base (
        team_id, organization_id, title, content, content_type,
        knowledge_category, embedding, source_type, contributing_agents,
        team_relevance_score, metadata, tags
    )
    SELECT 
        team_id_param,
        t.organization_id,
        COALESCE(agent_mem.task_context->>'task_type', 'General Knowledge'),
        agent_mem.content,
        CASE agent_mem.memory_type 
            WHEN 'code_pattern' THEN 'code'
            WHEN 'task_outcome' THEN 'procedure'
            ELSE 'text'
        END,
        COALESCE(agent_mem.task_context->>'skill_area', 'general'),
        agent_mem.embedding,
        'agent_contribution',
        ARRAY[agent_mem.agent_id],
        agent_mem.confidence_score,
        agent_mem.task_context,
        ARRAY[agent_mem.memory_type::text]
    FROM teams t
    WHERE t.id = team_id_param
    RETURNING id INTO new_team_knowledge_id;
    
    -- Log the propagation
    INSERT INTO knowledge_propagation_log (
        source_type, source_id, target_type, target_id,
        knowledge_type, knowledge_content_id, propagation_method,
        propagation_trigger, confidence_score, propagation_status
    ) VALUES (
        'agent', agent_mem.agent_id, 'team', team_id_param,
        agent_mem.memory_type::text, new_team_knowledge_id, 'automatic',
        'task_completion', agent_mem.confidence_score, 'completed'
    );
    
    -- Mark agent memory as propagated
    UPDATE agent_memory 
    SET propagated_to_team = TRUE, team_context_id = new_team_knowledge_id
    WHERE id = agent_memory_id;
    
    RETURN new_team_knowledge_id;
END;
$$ LANGUAGE plpgsql;

-- Function to search organization knowledge with semantic similarity
CREATE OR REPLACE FUNCTION search_organization_knowledge(
    org_id UUID,
    query_embedding vector(384),
    category_filter VARCHAR(100) DEFAULT NULL,
    limit_results INTEGER DEFAULT 10,
    min_relevance FLOAT DEFAULT 0.3
) RETURNS TABLE (
    knowledge_id UUID,
    title VARCHAR(500),
    content TEXT,
    content_type VARCHAR(50),
    relevance_score FLOAT,
    similarity_score FLOAT,
    usage_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        okb.id as knowledge_id,
        okb.title,
        okb.content,
        okb.content_type,
        okb.relevance_score,
        (1 - (okb.embedding <=> query_embedding)) as similarity_score,
        okb.usage_count,
        okb.created_at
    FROM organization_knowledge_base okb
    WHERE okb.organization_id = org_id
      AND (category_filter IS NULL OR okb.knowledge_category = category_filter)
      AND (1 - (okb.embedding <=> query_embedding)) >= min_relevance
    ORDER BY (1 - (okb.embedding <=> query_embedding)) DESC, okb.relevance_score DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Create materialized view for knowledge analytics dashboard
CREATE MATERIALIZED VIEW IF NOT EXISTS knowledge_dashboard_metrics AS
SELECT 
    o.id as organization_id,
    o.name as organization_name,
    COUNT(DISTINCT okb.id) as total_knowledge_items,
    COUNT(DISTINCT tkb.id) as team_knowledge_items,
    COUNT(DISTINCT am.id) as agent_memories,
    AVG(okb.relevance_score) as avg_knowledge_relevance,
    COUNT(DISTINCT CASE WHEN okb.created_at >= NOW() - INTERVAL '7 days' THEN okb.id END) as knowledge_added_7d,
    COUNT(DISTINCT CASE WHEN okb.last_accessed >= NOW() - INTERVAL '7 days' THEN okb.id END) as knowledge_used_7d,
    COUNT(DISTINCT kpl.id) as total_propagations,
    COUNT(DISTINCT CASE WHEN kpl.propagated_at >= NOW() - INTERVAL '7 days' THEN kpl.id END) as propagations_7d
FROM organizations o
LEFT JOIN organization_knowledge_base okb ON o.id = okb.organization_id
LEFT JOIN team_knowledge_base tkb ON o.id = tkb.organization_id
LEFT JOIN teams t ON o.id = t.organization_id
LEFT JOIN agents a ON t.id = a.team_id
LEFT JOIN agent_memory am ON a.id = am.agent_id
LEFT JOIN knowledge_propagation_log kpl ON (
    (kpl.source_type = 'organization' AND kpl.source_id = o.id) OR
    (kpl.target_type = 'organization' AND kpl.target_id = o.id)
)
GROUP BY o.id, o.name;

-- Create refresh function for the materialized view
CREATE OR REPLACE FUNCTION refresh_knowledge_dashboard()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW knowledge_dashboard_metrics;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-refresh dashboard periodically (or call manually)
-- Note: In production, you might want to use a scheduled job instead

COMMENT ON TABLE organization_knowledge_base IS 'Central repository for organization-level knowledge with vector embeddings for semantic search';
COMMENT ON TABLE team_knowledge_base IS 'Team-specific knowledge aggregated from agents and filtered for team relevance';
COMMENT ON TABLE knowledge_propagation_log IS 'Tracks the flow of knowledge between different levels of the organization hierarchy';
COMMENT ON TABLE knowledge_notifications IS 'Manages notifications about knowledge updates, conflicts, and opportunities';
COMMENT ON TABLE knowledge_relationships IS 'Defines relationships and dependencies between different knowledge items';
COMMENT ON TABLE knowledge_analytics IS 'Stores metrics and analytics about knowledge usage, effectiveness, and propagation';