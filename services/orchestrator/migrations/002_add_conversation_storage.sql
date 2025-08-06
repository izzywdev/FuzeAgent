-- Migration: Add conversation storage for Claude Code interactions
-- This extends the existing task_messages table and adds new conversation tracking

-- Extend existing task_messages table with Claude Code conversation fields
ALTER TABLE task_messages 
ADD COLUMN IF NOT EXISTS iteration_number INTEGER,
ADD COLUMN IF NOT EXISTS token_count INTEGER,
ADD COLUMN IF NOT EXISTS model_used VARCHAR(100),
ADD COLUMN IF NOT EXISTS temperature FLOAT,
ADD COLUMN IF NOT EXISTS conversation_context JSONB DEFAULT '{}';

-- Create dedicated Claude Code conversation table for detailed tracking
CREATE TABLE IF NOT EXISTS claude_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    iteration_number INTEGER NOT NULL,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN (
        'user_prompt', 
        'claude_response', 
        'system_message', 
        'error_message',
        'code_execution',
        'test_result'
    )),
    content TEXT NOT NULL,
    token_count INTEGER,
    model_used VARCHAR(100),
    temperature FLOAT,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Agent conversation sessions for tracking Claude Code CLI sessions
CREATE TABLE IF NOT EXISTS agent_conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    sandbox_id VARCHAR(255),
    session_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_ended_at TIMESTAMP,
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed', 'cancelled')),
    metadata JSONB DEFAULT '{}'
);

-- Code generation tracking for storing generated files and their context
CREATE TABLE IF NOT EXISTS code_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    iteration_number INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50), -- 'implementation', 'test', 'documentation'
    language VARCHAR(50),
    content TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    commit_hash VARCHAR(255),
    test_results JSONB,
    quality_metrics JSONB DEFAULT '{}'
);

-- Human interactions tracking for detailed human-in-the-loop conversations
CREATE TABLE IF NOT EXISTS human_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    iteration_number INTEGER NOT NULL,
    interaction_type VARCHAR(50) NOT NULL CHECK (interaction_type IN (
        'question',
        'clarification',
        'approval_request',
        'error_report',
        'progress_update'
    )),
    agent_message TEXT NOT NULL,
    human_response TEXT,
    response_time_seconds INTEGER,
    asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Agent performance metrics for tracking efficiency and quality
CREATE TABLE IF NOT EXISTS agent_performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(20),
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context JSONB DEFAULT '{}'
    
    -- Common metrics: 'iterations_to_completion', 'code_quality_score', 
    -- 'test_coverage', 'execution_time_minutes', 'tokens_used', 'cost_usd'
);

-- Update existing task_iterations table to reference conversation sessions
ALTER TABLE task_iterations 
ADD COLUMN IF NOT EXISTS conversation_session_id UUID REFERENCES agent_conversation_sessions(id),
ADD COLUMN IF NOT EXISTS message_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS token_usage INTEGER DEFAULT 0;

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_claude_conversations_task_id ON claude_conversations(task_id);
CREATE INDEX IF NOT EXISTS idx_claude_conversations_iteration ON claude_conversations(task_id, iteration_number);
CREATE INDEX IF NOT EXISTS idx_claude_conversations_type ON claude_conversations(message_type);
CREATE INDEX IF NOT EXISTS idx_claude_conversations_created_at ON claude_conversations(created_at);

CREATE INDEX IF NOT EXISTS idx_agent_conversations_agent_id ON agent_conversation_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_task_id ON agent_conversation_sessions(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_conversations_status ON agent_conversation_sessions(status);

CREATE INDEX IF NOT EXISTS idx_code_generations_task_id ON code_generations(task_id);
CREATE INDEX IF NOT EXISTS idx_code_generations_iteration ON code_generations(task_id, iteration_number);
CREATE INDEX IF NOT EXISTS idx_code_generations_file_type ON code_generations(file_type);
CREATE INDEX IF NOT EXISTS idx_code_generations_language ON code_generations(language);

CREATE INDEX IF NOT EXISTS idx_human_interactions_task_id ON human_interactions(task_id);
CREATE INDEX IF NOT EXISTS idx_human_interactions_type ON human_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_human_interactions_status ON human_interactions(responded_at);

CREATE INDEX IF NOT EXISTS idx_agent_performance_agent_id ON agent_performance_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_performance_task_id ON agent_performance_metrics(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_performance_type ON agent_performance_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_agent_performance_measured_at ON agent_performance_metrics(measured_at);