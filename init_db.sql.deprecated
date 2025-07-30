-- init_db.sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Teams
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    team_type VARCHAR(50) DEFAULT 'general', -- 'development', 'qa', 'design', 'management', 'general'
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Registry
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'executive', 'developer', 'qa', etc.
    status VARCHAR(50) DEFAULT 'inactive',
    config JSONB,
    template_id VARCHAR(100), -- Reference to agent template used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Interactions
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    assigned_to UUID REFERENCES agents(id),
    created_by UUID REFERENCES agents(id),
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Agent Relationships
CREATE TABLE agent_hierarchy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID REFERENCES agents(id),
    child_id UUID REFERENCES agents(id),
    relationship_type VARCHAR(50), -- 'manages', 'collaborates', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_interactions_embedding ON interactions USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_team_id ON agents(team_id);
CREATE INDEX idx_teams_organization_id ON teams(organization_id);

-- Create unique constraint for team names within organization
CREATE UNIQUE INDEX idx_teams_name_per_org ON teams(organization_id, name);

-- Insert default organization and team for existing setup
INSERT INTO organizations (id, name, description) 
VALUES ('550e8400-e29b-41d4-a716-446655440000', 'Default Organization', 'Default organization for initial setup');

INSERT INTO teams (id, organization_id, name, description, team_type) 
VALUES ('550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440000', 'Default Team', 'Default team for initial setup', 'general');