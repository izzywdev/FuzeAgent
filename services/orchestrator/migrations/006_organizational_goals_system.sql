-- Migration: Organizational Goals and Milestone Management System
-- This migration creates a comprehensive goals system for organizations
-- Enables hierarchical goal → milestone → task workflow with conversation support

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Goals Table - Organizational objectives with deadlines and priorities
CREATE TABLE IF NOT EXISTS organization_goals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Goal Basic Information
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    goal_type VARCHAR(50) NOT NULL DEFAULT 'business', -- business, technical, growth, operational
    priority_level INTEGER NOT NULL DEFAULT 5, -- 1-10 scale, 10 being highest
    
    -- Financial and Metrics
    target_value DECIMAL(15,2), -- e.g., $100,000 for MRR goal
    target_unit VARCHAR(50), -- e.g., 'USD', 'users', 'downloads', '%'
    current_value DECIMAL(15,2) DEFAULT 0,
    success_criteria JSONB, -- Flexible criteria definition
    
    -- Timeline
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    target_deadline DATE NOT NULL,
    actual_completion_date DATE,
    
    -- Status and Progress
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, paused, completed, cancelled, overdue
    progress_percentage DECIMAL(5,2) DEFAULT 0.00, -- 0.00 to 100.00
    completion_confidence DECIMAL(3,2) DEFAULT 0.50, -- AI-calculated confidence score
    
    -- Organizational Assignment
    assigned_teams UUID[] DEFAULT '{}', -- Array of team IDs
    goal_owner_agent_id UUID REFERENCES agents(id), -- Primary responsible agent
    stakeholder_agents UUID[] DEFAULT '{}', -- Other involved agents
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Audit Fields
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_priority CHECK (priority_level >= 1 AND priority_level <= 10),
    CONSTRAINT valid_progress CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    CONSTRAINT valid_confidence CHECK (completion_confidence >= 0 AND completion_confidence <= 1),
    CONSTRAINT valid_dates CHECK (target_deadline >= start_date)
);

-- Goal Conversations Table - AI-powered discussion and planning for each goal
CREATE TABLE IF NOT EXISTS goal_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL REFERENCES organization_goals(id) ON DELETE CASCADE,
    
    -- Conversation Metadata
    conversation_type VARCHAR(50) NOT NULL DEFAULT 'planning', -- planning, review, adjustment, problem_solving
    conversation_title TEXT NOT NULL,
    conversation_summary TEXT,
    
    -- AI Context
    conversation_context JSONB DEFAULT '{}', -- AI conversation context and memory
    participants JSONB DEFAULT '[]', -- List of human and AI participants
    
    -- Conversation Content
    messages JSONB DEFAULT '[]', -- Array of conversation messages
    insights_generated JSONB DEFAULT '[]', -- Key insights from the conversation
    action_items JSONB DEFAULT '[]', -- Action items derived from conversation
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, archived, completed
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Audit Fields
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Milestones Table - Intermediate objectives that lead to goal completion
CREATE TABLE IF NOT EXISTS goal_milestones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL REFERENCES organization_goals(id) ON DELETE CASCADE,
    parent_milestone_id UUID REFERENCES goal_milestones(id), -- For sub-milestones
    
    -- Milestone Definition
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    milestone_type VARCHAR(50) NOT NULL DEFAULT 'deliverable', -- deliverable, metric, checkpoint, review
    
    -- Timeline
    target_date DATE NOT NULL,
    actual_completion_date DATE,
    
    -- Success Criteria
    success_criteria JSONB NOT NULL, -- Specific criteria for milestone completion
    deliverables JSONB DEFAULT '[]', -- Expected deliverables
    dependencies JSONB DEFAULT '[]', -- Dependencies on other milestones
    
    -- Progress Tracking
    status VARCHAR(50) NOT NULL DEFAULT 'planned', -- planned, in_progress, completed, blocked, cancelled
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    completion_confidence DECIMAL(3,2) DEFAULT 0.50,
    
    -- Assignment
    assigned_teams UUID[] DEFAULT '{}',
    responsible_agent_id UUID REFERENCES agents(id),
    supporting_agents UUID[] DEFAULT '{}',
    
    -- Priority and Weight
    priority_level INTEGER NOT NULL DEFAULT 5,
    weight_in_goal DECIMAL(5,2) DEFAULT 10.00, -- Percentage contribution to overall goal
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Audit Fields
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_milestone_priority CHECK (priority_level >= 1 AND priority_level <= 10),
    CONSTRAINT valid_milestone_progress CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    CONSTRAINT valid_milestone_confidence CHECK (completion_confidence >= 0 AND completion_confidence <= 1),
    CONSTRAINT valid_milestone_weight CHECK (weight_in_goal >= 0 AND weight_in_goal <= 100)
);

-- Goal Tasks Table - Specific actionable items derived from milestones
CREATE TABLE IF NOT EXISTS goal_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL REFERENCES organization_goals(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES goal_milestones(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES goal_tasks(id), -- For subtasks
    
    -- Task Definition
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    task_type VARCHAR(50) NOT NULL DEFAULT 'development', -- development, research, marketing, sales, operations
    complexity_level VARCHAR(20) DEFAULT 'medium', -- low, medium, high, very_high
    
    -- Assignment
    assigned_team_id UUID REFERENCES teams(id),
    assigned_agent_id UUID REFERENCES agents(id),
    created_by_agent_id UUID REFERENCES agents(id),
    
    -- Timeline
    estimated_hours DECIMAL(6,2),
    due_date DATE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Task Management
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, assigned, in_progress, review, completed, cancelled
    priority INTEGER NOT NULL DEFAULT 5,
    
    -- Dependencies and Relationships
    dependencies JSONB DEFAULT '[]', -- Task dependencies
    blockers JSONB DEFAULT '[]', -- Current blockers
    
    -- Task Execution
    result JSONB, -- Task execution results
    quality_score DECIMAL(3,2), -- Quality assessment (0-1)
    effort_actual_hours DECIMAL(6,2), -- Actual effort spent
    
    -- Requirements and Specifications
    requirements JSONB DEFAULT '{}', -- Detailed requirements
    acceptance_criteria JSONB DEFAULT '[]', -- Acceptance criteria
    technical_specifications JSONB DEFAULT '{}', -- Technical specs if applicable
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    labels JSONB DEFAULT '[]', -- Additional categorization
    metadata JSONB DEFAULT '{}',
    
    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_task_priority CHECK (priority >= 1 AND priority <= 10),
    CONSTRAINT valid_quality_score CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1))
);

-- Goal Progress Tracking Table - Historical progress tracking and analytics
CREATE TABLE IF NOT EXISTS goal_progress_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL REFERENCES organization_goals(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES goal_milestones(id) ON DELETE CASCADE,
    
    -- Progress Snapshot
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    progress_type VARCHAR(50) NOT NULL, -- goal_progress, milestone_progress, task_completion, metric_update
    
    -- Progress Data
    progress_percentage DECIMAL(5,2) NOT NULL,
    current_value DECIMAL(15,2),
    target_value DECIMAL(15,2),
    
    -- Metadata
    progress_notes TEXT,
    recorded_by UUID REFERENCES agents(id),
    data_source VARCHAR(100), -- manual, automated, agent_report, system_calculation
    
    -- Context
    context_data JSONB DEFAULT '{}', -- Additional context about the progress
    
    CONSTRAINT valid_tracked_progress CHECK (progress_percentage >= 0 AND progress_percentage <= 100)
);

-- Goal Dependencies Table - Track dependencies between goals
CREATE TABLE IF NOT EXISTS goal_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_goal_id UUID NOT NULL REFERENCES organization_goals(id) ON DELETE CASCADE,
    dependent_goal_id UUID NOT NULL REFERENCES organization_goals(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) NOT NULL DEFAULT 'prerequisite', -- prerequisite, related, blocking, supporting
    dependency_strength DECIMAL(3,2) DEFAULT 0.50, -- How critical this dependency is (0-1)
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT no_self_dependency CHECK (source_goal_id != dependent_goal_id),
    CONSTRAINT valid_dependency_strength CHECK (dependency_strength >= 0 AND dependency_strength <= 1)
);

-- Goal Metrics Table - Track various metrics associated with goals
CREATE TABLE IF NOT EXISTS goal_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    goal_id UUID NOT NULL REFERENCES organization_goals(id) ON DELETE CASCADE,
    
    -- Metric Definition
    metric_name VARCHAR(100) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- financial, operational, technical, engagement
    metric_unit VARCHAR(20),
    
    -- Current State
    current_value DECIMAL(15,4) NOT NULL DEFAULT 0,
    target_value DECIMAL(15,4) NOT NULL,
    baseline_value DECIMAL(15,4), -- Starting point
    
    -- Tracking
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    update_frequency VARCHAR(20) DEFAULT 'daily', -- daily, weekly, monthly
    data_source VARCHAR(100), -- Where the metric data comes from
    
    -- Thresholds
    warning_threshold DECIMAL(15,4), -- Yellow flag threshold
    critical_threshold DECIMAL(15,4), -- Red flag threshold
    
    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, paused, archived
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(goal_id, metric_name)
);

-- Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_organization_goals_org_id ON organization_goals(organization_id);
CREATE INDEX IF NOT EXISTS idx_organization_goals_status ON organization_goals(status);
CREATE INDEX IF NOT EXISTS idx_organization_goals_deadline ON organization_goals(target_deadline);
CREATE INDEX IF NOT EXISTS idx_organization_goals_priority ON organization_goals(priority_level DESC);

CREATE INDEX IF NOT EXISTS idx_goal_conversations_goal_id ON goal_conversations(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_conversations_type ON goal_conversations(conversation_type);
CREATE INDEX IF NOT EXISTS idx_goal_conversations_activity ON goal_conversations(last_activity_at DESC);

CREATE INDEX IF NOT EXISTS idx_goal_milestones_goal_id ON goal_milestones(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_milestones_parent ON goal_milestones(parent_milestone_id);
CREATE INDEX IF NOT EXISTS idx_goal_milestones_status ON goal_milestones(status);
CREATE INDEX IF NOT EXISTS idx_goal_milestones_target_date ON goal_milestones(target_date);

CREATE INDEX IF NOT EXISTS idx_goal_tasks_goal_id ON goal_tasks(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_tasks_milestone_id ON goal_tasks(milestone_id);
CREATE INDEX IF NOT EXISTS idx_goal_tasks_assigned_agent ON goal_tasks(assigned_agent_id);
CREATE INDEX IF NOT EXISTS idx_goal_tasks_assigned_team ON goal_tasks(assigned_team_id);
CREATE INDEX IF NOT EXISTS idx_goal_tasks_status ON goal_tasks(status);
CREATE INDEX IF NOT EXISTS idx_goal_tasks_due_date ON goal_tasks(due_date);

CREATE INDEX IF NOT EXISTS idx_goal_progress_goal_id ON goal_progress_tracking(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_progress_recorded_at ON goal_progress_tracking(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_goal_progress_type ON goal_progress_tracking(progress_type);

CREATE INDEX IF NOT EXISTS idx_goal_dependencies_source ON goal_dependencies(source_goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_dependencies_dependent ON goal_dependencies(dependent_goal_id);

CREATE INDEX IF NOT EXISTS idx_goal_metrics_goal_id ON goal_metrics(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_metrics_type ON goal_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_goal_metrics_status ON goal_metrics(status);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_organization_goals_fts ON organization_goals USING GIN(to_tsvector('english', title || ' ' || description));
CREATE INDEX IF NOT EXISTS idx_goal_milestones_fts ON goal_milestones USING GIN(to_tsvector('english', title || ' ' || description));
CREATE INDEX IF NOT EXISTS idx_goal_tasks_fts ON goal_tasks USING GIN(to_tsvector('english', title || ' ' || description));

-- Views for Common Queries

-- Goal Overview with Progress
CREATE OR REPLACE VIEW goal_overview AS
SELECT 
    g.id,
    g.organization_id,
    g.title,
    g.description,
    g.goal_type,
    g.priority_level,
    g.target_value,
    g.target_unit,
    g.current_value,
    g.start_date,
    g.target_deadline,
    g.status,
    g.progress_percentage,
    g.completion_confidence,
    -- Calculated fields
    CASE 
        WHEN g.target_deadline < CURRENT_DATE AND g.status NOT IN ('completed', 'cancelled') THEN 'overdue'
        WHEN g.target_deadline <= CURRENT_DATE + INTERVAL '7 days' AND g.status = 'active' THEN 'due_soon'
        ELSE g.status
    END as calculated_status,
    (g.target_deadline - CURRENT_DATE) as days_remaining,
    -- Milestone and task counts
    (SELECT COUNT(*) FROM goal_milestones WHERE goal_id = g.id) as total_milestones,
    (SELECT COUNT(*) FROM goal_milestones WHERE goal_id = g.id AND status = 'completed') as completed_milestones,
    (SELECT COUNT(*) FROM goal_tasks WHERE goal_id = g.id) as total_tasks,
    (SELECT COUNT(*) FROM goal_tasks WHERE goal_id = g.id AND status = 'completed') as completed_tasks,
    -- Team involvement
    ARRAY_LENGTH(g.assigned_teams, 1) as involved_teams_count,
    g.created_at,
    g.updated_at
FROM organization_goals g;

-- Active Goal Dashboard
CREATE OR REPLACE VIEW active_goals_dashboard AS
SELECT 
    o.name as organization_name,
    g.id as goal_id,
    g.title,
    g.goal_type,
    g.priority_level,
    g.target_value,
    g.target_unit,
    g.current_value,
    CASE 
        WHEN g.target_value > 0 THEN (g.current_value / g.target_value * 100)
        ELSE g.progress_percentage
    END as calculated_progress,
    g.target_deadline,
    g.completion_confidence,
    (g.target_deadline - CURRENT_DATE) as days_remaining,
    -- Risk indicators
    CASE 
        WHEN g.target_deadline < CURRENT_DATE THEN 'overdue'
        WHEN g.completion_confidence < 0.3 THEN 'high_risk'
        WHEN g.target_deadline <= CURRENT_DATE + INTERVAL '14 days' AND g.progress_percentage < 70 THEN 'at_risk'
        ELSE 'on_track'
    END as risk_status,
    g.updated_at
FROM organization_goals g
JOIN organizations o ON g.organization_id = o.id
WHERE g.status = 'active'
ORDER BY g.priority_level DESC, g.target_deadline ASC;

-- Trigger Functions for Automatic Updates

-- Function to update goal progress based on milestone completion
CREATE OR REPLACE FUNCTION update_goal_progress_from_milestones()
RETURNS TRIGGER AS $$
BEGIN
    -- Update goal progress when milestone status changes
    IF (TG_OP = 'UPDATE' AND OLD.status != NEW.status) OR TG_OP = 'INSERT' THEN
        UPDATE organization_goals 
        SET 
            progress_percentage = (
                SELECT COALESCE(
                    SUM(progress_percentage * weight_in_goal) / 100.0,
                    0
                )
                FROM goal_milestones 
                WHERE goal_id = COALESCE(NEW.goal_id, OLD.goal_id)
                AND status != 'cancelled'
            ),
            updated_at = NOW()
        WHERE id = COALESCE(NEW.goal_id, OLD.goal_id);
        
        -- Record progress tracking entry
        INSERT INTO goal_progress_tracking (
            goal_id, milestone_id, progress_type, progress_percentage, 
            progress_notes, recorded_by, data_source
        ) VALUES (
            COALESCE(NEW.goal_id, OLD.goal_id),
            COALESCE(NEW.id, OLD.id),
            'milestone_progress',
            COALESCE(NEW.progress_percentage, OLD.progress_percentage),
            'Milestone status changed to: ' || COALESCE(NEW.status, OLD.status),
            COALESCE(NEW.responsible_agent_id, OLD.responsible_agent_id),
            'system_calculation'
        );
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Trigger for milestone progress updates
DROP TRIGGER IF EXISTS trg_milestone_progress_update ON goal_milestones;
CREATE TRIGGER trg_milestone_progress_update
    AFTER INSERT OR UPDATE ON goal_milestones
    FOR EACH ROW
    EXECUTE FUNCTION update_goal_progress_from_milestones();

-- Function to update milestone progress from task completion
CREATE OR REPLACE FUNCTION update_milestone_progress_from_tasks()
RETURNS TRIGGER AS $$
BEGIN
    -- Update milestone progress when task status changes
    IF NEW.milestone_id IS NOT NULL AND 
       ((TG_OP = 'UPDATE' AND OLD.status != NEW.status) OR TG_OP = 'INSERT') THEN
        
        UPDATE goal_milestones 
        SET 
            progress_percentage = (
                SELECT COALESCE(
                    AVG(CASE WHEN status = 'completed' THEN 100.0 ELSE 0.0 END),
                    0
                )
                FROM goal_tasks 
                WHERE milestone_id = NEW.milestone_id
                AND status != 'cancelled'
            ),
            updated_at = NOW()
        WHERE id = NEW.milestone_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for task completion updates
DROP TRIGGER IF EXISTS trg_task_completion_update ON goal_tasks;
CREATE TRIGGER trg_task_completion_update
    AFTER INSERT OR UPDATE ON goal_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_milestone_progress_from_tasks();

-- Function to automatically update goal status based on deadlines and progress
CREATE OR REPLACE FUNCTION update_goal_status_automatically()
RETURNS void AS $$
BEGIN
    -- Mark goals as overdue
    UPDATE organization_goals 
    SET status = 'overdue', updated_at = NOW()
    WHERE status = 'active' 
    AND target_deadline < CURRENT_DATE;
    
    -- Mark goals as completed if progress is 100%
    UPDATE organization_goals 
    SET status = 'completed', 
        actual_completion_date = CURRENT_DATE,
        updated_at = NOW()
    WHERE status IN ('active', 'overdue') 
    AND progress_percentage >= 100.0
    AND actual_completion_date IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Sample Data for WCG Organization
-- Insert sample goal for WCG to reach $100k MRR in 6 months
DO $$
DECLARE
    wcg_org_id UUID;
    wcg_goal_id UUID;
    ceo_agent_id UUID;
BEGIN
    -- Get WCG organization ID
    SELECT id INTO wcg_org_id FROM organizations WHERE name = 'WCG' LIMIT 1;
    
    -- Get CEO agent ID (IzzyAI)
    SELECT id INTO ceo_agent_id FROM agents WHERE name = 'IzzyAI' LIMIT 1;
    
    -- Only insert if WCG exists
    IF wcg_org_id IS NOT NULL THEN
        -- Insert the main goal
        INSERT INTO organization_goals (
            organization_id,
            title,
            description,
            goal_type,
            priority_level,
            target_value,
            target_unit,
            target_deadline,
            status,
            goal_owner_agent_id,
            created_by,
            success_criteria,
            metadata
        ) VALUES (
            wcg_org_id,
            'Reach $100K Monthly Recurring Revenue (MRR)',
            'Achieve sustainable $100,000 monthly recurring revenue within 6 months through product development, marketing, and sales optimization.',
            'business',
            10, -- Highest priority
            100000.00,
            'USD',
            CURRENT_DATE + INTERVAL '6 months',
            'active',
            ceo_agent_id,
            ceo_agent_id,
            '{"revenue_target": 100000, "sustainability": "3_consecutive_months", "growth_rate": "month_over_month_positive", "customer_satisfaction": "above_4_stars"}'::JSONB,
            '{"initiative_type": "growth", "business_critical": true, "board_visibility": true}'::JSONB
        ) RETURNING id INTO wcg_goal_id;
        
        -- Add initial metrics tracking
        INSERT INTO goal_metrics (goal_id, metric_name, metric_type, metric_unit, current_value, target_value, baseline_value, update_frequency, data_source) VALUES
        (wcg_goal_id, 'Monthly Recurring Revenue', 'financial', 'USD', 0, 100000, 0, 'daily', 'revenue_system'),
        (wcg_goal_id, 'Customer Acquisition Rate', 'operational', 'customers_per_month', 0, 500, 0, 'daily', 'crm_system'),
        (wcg_goal_id, 'Customer Churn Rate', 'operational', 'percentage', 0, 2.0, 0, 'weekly', 'analytics_system'),
        (wcg_goal_id, 'Average Revenue Per User', 'financial', 'USD', 0, 200, 0, 'daily', 'revenue_system');
        
        -- Create initial conversation for goal planning
        INSERT INTO goal_conversations (
            goal_id,
            conversation_type,
            conversation_title,
            conversation_summary,
            created_by,
            participants,
            messages,
            action_items
        ) VALUES (
            wcg_goal_id,
            'planning',
            'Strategic Planning: Path to $100K MRR',
            'Initial strategic planning conversation to break down the $100K MRR goal into actionable milestones and tasks across all business functions.',
            ceo_agent_id,
            '[{"type": "agent", "id": "' || ceo_agent_id::text || '", "name": "IzzyAI", "role": "CEO"}]'::JSONB,
            '[{"id": "msg_1", "type": "system", "content": "Goal created: Reach $100K MRR in 6 months. Ready to begin strategic planning conversation.", "timestamp": "' || NOW()::text || '"}]'::JSONB,
            '[{"id": "action_1", "description": "Create monthly milestones breaking down revenue targets", "assigned_to": "system", "status": "pending"}]'::JSONB
        );
        
        RAISE NOTICE 'Successfully created $100K MRR goal for WCG organization with ID: %', wcg_goal_id;
    ELSE
        RAISE NOTICE 'WCG organization not found - skipping sample goal creation';
    END IF;
END;
$$;

COMMIT;