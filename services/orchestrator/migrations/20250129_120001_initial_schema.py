"""
Migration: Initial Schema Setup
Created: 2025-01-29T12:00:01
Description: Creates the foundational database schema with organizations, teams, agents, tasks, and interactions
"""


async def upgrade(conn):
    """Apply the migration"""

    # Enable vector extension
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create organizations table
    await conn.execute(
        """
        CREATE TABLE organizations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            settings JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )

    # Create teams table
    await conn.execute(
        """
        CREATE TABLE teams (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            team_type VARCHAR(50) DEFAULT 'general', 
            settings JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )

    # Create agents table
    await conn.execute(
        """
        CREATE TABLE agents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            role VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'inactive',
            config JSONB,
            template_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )

    # Create agent interactions table
    await conn.execute(
        """
        CREATE TABLE interactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID REFERENCES agents(id),
            content TEXT NOT NULL,
            embedding vector(1536),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )

    # Create tasks table
    await conn.execute(
        """
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
    """
    )

    # Create agent hierarchy table
    await conn.execute(
        """
        CREATE TABLE agent_hierarchy (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            parent_id UUID REFERENCES agents(id),
            child_id UUID REFERENCES agents(id),
            relationship_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )

    print("✅ Created all base tables")


async def downgrade(conn):
    """Rollback the migration"""

    # Drop tables in reverse dependency order
    await conn.execute("DROP TABLE IF EXISTS agent_hierarchy CASCADE;")
    await conn.execute("DROP TABLE IF EXISTS tasks CASCADE;")
    await conn.execute("DROP TABLE IF EXISTS interactions CASCADE;")
    await conn.execute("DROP TABLE IF EXISTS agents CASCADE;")
    await conn.execute("DROP TABLE IF EXISTS teams CASCADE;")
    await conn.execute("DROP TABLE IF EXISTS organizations CASCADE;")

    print("✅ Dropped all base tables")
