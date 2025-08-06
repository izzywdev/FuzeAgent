-- Migration: Add Autonomous Agent Execution Schema
-- Version: 001
-- Description: Add support for repository settings, sandboxing, task dependencies, and chat interactions

BEGIN;

-- Add repository and sandbox settings to agents table
ALTER TABLE agents 
ADD COLUMN IF NOT EXISTS repository_settings JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS sandbox_settings JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS workspace_path TEXT,
ADD COLUMN IF NOT EXISTS git_credentials_encrypted TEXT;

-- Task dependency management
CREATE TABLE IF NOT EXISTS task_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dependent_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    prerequisite_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(20) CHECK (dependency_type IN ('blocking', 'soft', 'data')) DEFAULT 'blocking',
    status VARCHAR(20) DEFAULT 'waiting',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(dependent_task_id, prerequisite_task_id)
);

-- Task execution tracking with iterations
CREATE TABLE IF NOT EXISTS task_iterations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    iteration_number INTEGER NOT NULL,
    git_commit_hash VARCHAR(64),
    branch_name VARCHAR(255),
    status VARCHAR(20) DEFAULT 'in_progress',
    agent_message TEXT,
    human_question TEXT,
    human_response TEXT,
    code_changes JSONB DEFAULT '{}',
    test_results JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    UNIQUE(task_id, iteration_number)
);

-- Chat interactions between agents and humans
CREATE TABLE IF NOT EXISTS task_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) CHECK (sender_type IN ('agent', 'human', 'system')) NOT NULL,
    sender_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    message_type VARCHAR(20) DEFAULT 'text',
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Human-in-the-loop questions
CREATE TABLE IF NOT EXISTS task_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    iteration_id UUID REFERENCES task_iterations(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) DEFAULT 'general',
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    human_response TEXT,
    context_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    answered_at TIMESTAMP
);

-- Agent sandboxes tracking
CREATE TABLE IF NOT EXISTS agent_sandboxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sandbox_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    container_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'creating',
    workspace_path TEXT,
    resource_limits JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    destroyed_at TIMESTAMP
);

-- Task execution graphs for dependency management
CREATE TABLE IF NOT EXISTS task_execution_graphs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    graph_name VARCHAR(255),
    task_ids UUID[] NOT NULL,
    execution_plan JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_task_dependencies_dependent ON task_dependencies(dependent_task_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_prerequisite ON task_dependencies(prerequisite_task_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_status ON task_dependencies(status);

CREATE INDEX IF NOT EXISTS idx_task_iterations_task_id ON task_iterations(task_id);
CREATE INDEX IF NOT EXISTS idx_task_iterations_status ON task_iterations(status);

CREATE INDEX IF NOT EXISTS idx_task_messages_task_id ON task_messages(task_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_task_messages_sender ON task_messages(sender_type, sender_id);

CREATE INDEX IF NOT EXISTS idx_task_questions_task_id ON task_questions(task_id);
CREATE INDEX IF NOT EXISTS idx_task_questions_status ON task_questions(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_sandboxes_agent_id ON agent_sandboxes(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_sandboxes_task_id ON agent_sandboxes(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_sandboxes_status ON agent_sandboxes(status);

-- Add some useful views
CREATE OR REPLACE VIEW task_status_with_dependencies AS
SELECT 
    t.id,
    t.title,
    t.status,
    t.assigned_to,
    COUNT(td.prerequisite_task_id) as total_dependencies,
    COUNT(CASE WHEN td.status = 'satisfied' THEN 1 END) as satisfied_dependencies,
    CASE 
        WHEN COUNT(td.prerequisite_task_id) = 0 THEN 'ready'
        WHEN COUNT(td.prerequisite_task_id) = COUNT(CASE WHEN td.status = 'satisfied' THEN 1 END) THEN 'ready'
        ELSE 'waiting_dependencies'
    END as dependency_status
FROM tasks t
LEFT JOIN task_dependencies td ON t.id = td.dependent_task_id
GROUP BY t.id, t.title, t.status, t.assigned_to;

CREATE OR REPLACE VIEW agent_workload AS
SELECT 
    a.id,
    a.name,
    a.role,
    a.status,
    COUNT(t.id) as active_tasks,
    COUNT(s.id) as active_sandboxes,
    COALESCE((a.sandbox_settings->'resource_limits'->>'max_concurrent_tasks'), '5')::int as max_tasks
FROM agents a
LEFT JOIN tasks t ON a.id = t.assigned_to AND t.status IN ('pending', 'in_progress')
LEFT JOIN agent_sandboxes s ON a.id = s.agent_id AND s.status = 'running'
GROUP BY a.id, a.name, a.role, a.status, a.sandbox_settings;

-- Update existing tasks table to support enhanced status tracking
DO $$ 
BEGIN
    -- Add new columns if they don't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='git_branch') THEN
        ALTER TABLE tasks ADD COLUMN git_branch VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='pull_request_url') THEN
        ALTER TABLE tasks ADD COLUMN pull_request_url TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='iteration_count') THEN
        ALTER TABLE tasks ADD COLUMN iteration_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='execution_context') THEN
        ALTER TABLE tasks ADD COLUMN execution_context JSONB DEFAULT '{}';
    END IF;
END $$;

-- Add constraints and triggers
CREATE OR REPLACE FUNCTION update_task_iteration_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE tasks 
    SET iteration_count = (
        SELECT COUNT(*) FROM task_iterations 
        WHERE task_id = NEW.task_id
    )
    WHERE id = NEW.task_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_task_iteration_count
    AFTER INSERT ON task_iterations
    FOR EACH ROW
    EXECUTE FUNCTION update_task_iteration_count();

-- Function to check if a task's dependencies are satisfied
CREATE OR REPLACE FUNCTION check_task_dependencies_satisfied(task_uuid UUID)
RETURNS BOOLEAN AS $$
DECLARE
    unsatisfied_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO unsatisfied_count
    FROM task_dependencies
    WHERE dependent_task_id = task_uuid 
    AND status != 'satisfied';
    
    RETURN unsatisfied_count = 0;
END;
$$ LANGUAGE plpgsql;

-- Function to get ready tasks (no unsatisfied dependencies)
CREATE OR REPLACE FUNCTION get_ready_tasks()
RETURNS TABLE (
    task_id UUID,
    title TEXT,
    description TEXT,
    assigned_to UUID,
    priority INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.title,
        t.description,
        t.assigned_to,
        t.priority
    FROM tasks t
    WHERE t.status = 'pending'
    AND check_task_dependencies_satisfied(t.id) = true
    ORDER BY t.priority DESC, t.created_at ASC;
END;
$$ LANGUAGE plpgsql;

COMMIT;