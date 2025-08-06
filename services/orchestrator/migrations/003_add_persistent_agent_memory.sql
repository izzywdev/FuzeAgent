-- Migration: Add Persistent Agent Memory System
-- This implements life-long agent memory that persists across container instances

-- Enable required extensions if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Agent Memory - Persistent across container instances
CREATE TABLE IF NOT EXISTS agent_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL, -- Permanent agent identity
    container_instance_id VARCHAR(255), -- Track which container created this
    task_id UUID, -- Task context where memory was created
    session_id UUID, -- Conversation session reference
    
    -- Memory content
    memory_type VARCHAR(50) NOT NULL CHECK (memory_type IN (
        'conversation', 'learning', 'pattern', 'error', 'success', 
        'task_outcome', 'code_pattern', 'debugging', 'optimization'
    )),
    content TEXT NOT NULL,
    embedding vector(384),
    
    -- Context metadata
    code_context JSONB DEFAULT '{}', -- Code files, languages, frameworks involved
    task_context JSONB DEFAULT '{}', -- Task type, complexity, requirements
    outcome_context JSONB DEFAULT '{}', -- Success/failure, metrics, lessons learned
    
    -- Experience tracking
    confidence_score FLOAT DEFAULT 1.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    success_correlation FLOAT DEFAULT 0.0, -- How this memory correlates with successful outcomes
    usage_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,
    
    -- Lifecycle tracking
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_container VARCHAR(255),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Agent expertise development tracking
CREATE TABLE IF NOT EXISTS agent_expertise (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    
    -- Expertise domains
    skill_area VARCHAR(100) NOT NULL, -- 'python_backend', 'react_frontend', 'database_design'
    expertise_level FLOAT DEFAULT 0.0 CHECK (expertise_level >= 0.0 AND expertise_level <= 1.0),
    task_count INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0 CHECK (success_rate >= 0.0 AND success_rate <= 1.0),
    
    -- Learning trajectory
    learning_velocity FLOAT DEFAULT 0.0, -- How fast agent is improving
    last_task_performance FLOAT, -- Performance on most recent task
    performance_trend VARCHAR(20) DEFAULT 'stable' CHECK (performance_trend IN ('improving', 'stable', 'declining')),
    
    -- Evidence and patterns
    key_learnings JSONB DEFAULT '{}', -- Important patterns and insights
    common_mistakes JSONB DEFAULT '{}', -- Recurring error patterns
    successful_approaches JSONB DEFAULT '{}', -- Proven successful patterns
    
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Container instance tracking
CREATE TABLE IF NOT EXISTS agent_container_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    container_id VARCHAR(255) NOT NULL,
    container_instance_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Instance lifecycle
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'stopped', 'crashed', 'terminated')),
    
    -- Performance metrics for this instance
    tasks_completed INTEGER DEFAULT 0,
    memory_entries_created INTEGER DEFAULT 0,
    uptime_hours FLOAT DEFAULT 0.0,
    
    -- Resource usage
    peak_memory_mb INTEGER,
    peak_cpu_percent FLOAT,
    total_tokens_used BIGINT DEFAULT 0,
    
    -- Metadata
    container_config JSONB DEFAULT '{}',
    exit_reason TEXT
);

-- Memory access patterns for optimization
CREATE TABLE IF NOT EXISTS agent_memory_access_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL,
    memory_id UUID NOT NULL REFERENCES agent_memory(id) ON DELETE CASCADE,
    access_timestamp TIMESTAMP DEFAULT NOW(),
    access_context JSONB DEFAULT '{}', -- What query/context led to this access
    relevance_score FLOAT, -- How relevant was this memory to the query
    used_in_response BOOLEAN DEFAULT FALSE -- Was this memory actually used in generating response
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id ON agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_created ON agent_memory(agent_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory(agent_id, memory_type);
CREATE INDEX IF NOT EXISTS idx_agent_memory_confidence ON agent_memory(agent_id, confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memory_usage ON agent_memory(agent_id, usage_count DESC);

-- Vector similarity search index
CREATE INDEX IF NOT EXISTS idx_agent_memory_embedding 
ON agent_memory USING ivfflat (embedding vector_cosine_ops);

-- Expertise indexes
CREATE INDEX IF NOT EXISTS idx_agent_expertise_agent ON agent_expertise(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_expertise_skill ON agent_expertise(agent_id, skill_area);
CREATE INDEX IF NOT EXISTS idx_agent_expertise_level ON agent_expertise(agent_id, expertise_level DESC);

-- Container instance indexes
CREATE INDEX IF NOT EXISTS idx_container_instances_agent ON agent_container_instances(agent_id);
CREATE INDEX IF NOT EXISTS idx_container_instances_started ON agent_container_instances(agent_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_container_instances_status ON agent_container_instances(status);

-- Memory access pattern indexes
CREATE INDEX IF NOT EXISTS idx_memory_access_agent ON agent_memory_access_patterns(agent_id, access_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_memory_access_memory ON agent_memory_access_patterns(memory_id);

-- Unique constraints
ALTER TABLE agent_expertise ADD CONSTRAINT unique_agent_skill UNIQUE(agent_id, skill_area);

-- Add foreign key constraints
ALTER TABLE agent_memory ADD CONSTRAINT fk_agent_memory_agent 
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;

ALTER TABLE agent_expertise ADD CONSTRAINT fk_agent_expertise_agent 
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;

ALTER TABLE agent_container_instances ADD CONSTRAINT fk_container_instances_agent 
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;

ALTER TABLE agent_memory_access_patterns ADD CONSTRAINT fk_memory_access_agent 
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;

-- Triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
DROP TRIGGER IF EXISTS update_agent_memory_updated_at ON agent_memory;
CREATE TRIGGER update_agent_memory_updated_at
    BEFORE UPDATE ON agent_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_agent_expertise_updated_at ON agent_expertise;
CREATE TRIGGER update_agent_expertise_updated_at
    BEFORE UPDATE ON agent_expertise
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Views for common queries
CREATE OR REPLACE VIEW agent_memory_summary AS
SELECT 
    agent_id,
    COUNT(*) as total_memories,
    COUNT(DISTINCT memory_type) as memory_types_count,
    AVG(confidence_score) as avg_confidence,
    SUM(usage_count) as total_usage,
    MAX(created_at) as last_memory_created,
    COUNT(DISTINCT container_instance_id) as container_instances_used
FROM agent_memory
GROUP BY agent_id;

CREATE OR REPLACE VIEW agent_expertise_summary AS
SELECT 
    agent_id,
    COUNT(*) as skill_areas_count,
    AVG(expertise_level) as avg_expertise_level,
    SUM(task_count) as total_tasks,
    AVG(success_rate) as avg_success_rate,
    COUNT(CASE WHEN performance_trend = 'improving' THEN 1 END) as improving_skills,
    COUNT(CASE WHEN performance_trend = 'declining' THEN 1 END) as declining_skills
FROM agent_expertise
GROUP BY agent_id;

-- Functions for memory management
CREATE OR REPLACE FUNCTION get_agent_relevant_memories(
    p_agent_id UUID,
    p_query_embedding vector(384),
    p_memory_types TEXT[] DEFAULT NULL,
    p_min_confidence FLOAT DEFAULT 0.3,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    memory_id UUID,
    content TEXT,
    memory_type VARCHAR(50),
    relevance_score FLOAT,
    confidence_score FLOAT,
    usage_count INTEGER,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        am.id,
        am.content,
        am.memory_type,
        (1 - (am.embedding <=> p_query_embedding))::FLOAT as relevance_score,
        am.confidence_score,
        am.usage_count,
        am.created_at
    FROM agent_memory am
    WHERE am.agent_id = p_agent_id
        AND am.confidence_score >= p_min_confidence
        AND (p_memory_types IS NULL OR am.memory_type = ANY(p_memory_types))
        AND (1 - (am.embedding <=> p_query_embedding)) > 0.7
    ORDER BY 
        (1 - (am.embedding <=> p_query_embedding)) DESC,
        am.confidence_score DESC,
        am.usage_count DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to update memory usage
CREATE OR REPLACE FUNCTION update_memory_usage(
    p_memory_ids UUID[],
    p_agent_id UUID,
    p_access_context JSONB DEFAULT '{}'
)
RETURNS VOID AS $$
BEGIN
    -- Update usage count and last accessed
    UPDATE agent_memory 
    SET usage_count = usage_count + 1, 
        last_accessed = NOW()
    WHERE id = ANY(p_memory_ids) AND agent_id = p_agent_id;
    
    -- Log access patterns
    INSERT INTO agent_memory_access_patterns (agent_id, memory_id, access_context)
    SELECT p_agent_id, unnest(p_memory_ids), p_access_context;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE agent_memory IS 'Persistent memory for agents across container instances, enabling life-long learning';
COMMENT ON TABLE agent_expertise IS 'Tracks agent expertise development and learning trajectory in different skill areas';
COMMENT ON TABLE agent_container_instances IS 'Tracks container instances for agents, enabling performance analysis';
COMMENT ON TABLE agent_memory_access_patterns IS 'Logs memory access patterns for optimization and analytics';

COMMENT ON COLUMN agent_memory.confidence_score IS 'Agent confidence in this memory (0.0-1.0), used for relevance ranking';
COMMENT ON COLUMN agent_memory.success_correlation IS 'How strongly this memory correlates with successful task outcomes';
COMMENT ON COLUMN agent_expertise.learning_velocity IS 'Rate of improvement in this skill area (positive = improving)';
COMMENT ON COLUMN agent_expertise.performance_trend IS 'Whether agent is improving, stable, or declining in this skill';