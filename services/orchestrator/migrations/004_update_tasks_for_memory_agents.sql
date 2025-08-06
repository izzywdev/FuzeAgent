-- Migration: Update tasks table for memory-enabled agents
-- Add fields needed for memory-enabled agent task management

-- Add missing columns to tasks table
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS agent_id UUID REFERENCES agents(id),
ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT 'development',
ADD COLUMN IF NOT EXISTS complexity VARCHAR(20) DEFAULT 'medium',
ADD COLUMN IF NOT EXISTS language VARCHAR(50),
ADD COLUMN IF NOT EXISTS framework VARCHAR(100),
ADD COLUMN IF NOT EXISTS requirements JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS assigned_to_memory_agent BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS updated_by UUID,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_memory_agent ON tasks(assigned_to_memory_agent);
CREATE INDEX IF NOT EXISTS idx_tasks_status_memory ON tasks(status, assigned_to_memory_agent);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
CREATE INDEX IF NOT EXISTS idx_tasks_complexity ON tasks(complexity);
CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at DESC);

-- Add check constraints
ALTER TABLE tasks ADD CONSTRAINT check_task_type 
CHECK (type IN ('development', 'testing', 'debugging', 'code_review', 'deployment', 'research', 'documentation'));

ALTER TABLE tasks ADD CONSTRAINT check_task_complexity 
CHECK (complexity IN ('low', 'medium', 'high', 'very_high'));

-- Add trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON COLUMN tasks.agent_id IS 'ID of the agent assigned to this task';
COMMENT ON COLUMN tasks.type IS 'Type of task (development, testing, debugging, etc.)';
COMMENT ON COLUMN tasks.complexity IS 'Task complexity level (low, medium, high, very_high)';
COMMENT ON COLUMN tasks.language IS 'Primary programming language for the task';
COMMENT ON COLUMN tasks.framework IS 'Framework or technology stack used';
COMMENT ON COLUMN tasks.requirements IS 'JSON array of task requirements and constraints';
COMMENT ON COLUMN tasks.assigned_to_memory_agent IS 'Whether this task is assigned to a memory-enabled agent';
COMMENT ON COLUMN tasks.updated_by IS 'ID of the agent or user who last updated this task';
COMMENT ON COLUMN tasks.updated_at IS 'Timestamp of last update';