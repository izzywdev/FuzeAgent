-- Migration: Create Organizations and Teams Tables
-- This migration creates the basic organizational structure tables

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organizations Table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Teams Table
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    team_type VARCHAR(50) DEFAULT 'general',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(name);
CREATE INDEX IF NOT EXISTS idx_teams_organization_id ON teams(organization_id);
CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(name);

-- Insert some sample data
INSERT INTO organizations (id, name, description) VALUES 
    (uuid_generate_v4(), 'Acme Corp', 'A leading technology company'),
    (uuid_generate_v4(), 'TechStart Inc', 'Innovative startup in AI')
ON CONFLICT (name) DO NOTHING;

-- Get the organization IDs for teams
DO $$
DECLARE
    acme_id UUID;
    techstart_id UUID;
BEGIN
    SELECT id INTO acme_id FROM organizations WHERE name = 'Acme Corp';
    SELECT id INTO techstart_id FROM organizations WHERE name = 'TechStart Inc';
    
    IF acme_id IS NOT NULL THEN
        INSERT INTO teams (organization_id, name, description, team_type) VALUES 
            (acme_id, 'Engineering', 'Core engineering team', 'technical'),
            (acme_id, 'Product', 'Product management team', 'business')
        ON CONFLICT (organization_id, name) DO NOTHING;
    END IF;
    
    IF techstart_id IS NOT NULL THEN
        INSERT INTO teams (organization_id, name, description, team_type) VALUES 
            (techstart_id, 'AI Research', 'AI research and development', 'technical'),
            (techstart_id, 'Business Development', 'Business development and partnerships', 'business')
        ON CONFLICT (organization_id, name) DO NOTHING;
    END IF;
END $$;
