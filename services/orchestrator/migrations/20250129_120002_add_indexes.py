"""
Migration: Add Database Indexes
Created: 2025-01-29T12:00:02
Description: Creates performance indexes and constraints for better query performance
"""

async def upgrade(conn):
    """Apply the migration"""
    
    # Vector search index (requires vector extension)
    await conn.execute("""
        CREATE INDEX idx_interactions_embedding 
        ON interactions USING ivfflat (embedding vector_cosine_ops);
    """)
    
    # Performance indexes
    await conn.execute("CREATE INDEX idx_tasks_status ON tasks(status);")
    await conn.execute("CREATE INDEX idx_agents_status ON agents(status);")
    await conn.execute("CREATE INDEX idx_agents_team_id ON agents(team_id);")
    await conn.execute("CREATE INDEX idx_teams_organization_id ON teams(organization_id);")
    await conn.execute("CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);")
    await conn.execute("CREATE INDEX idx_tasks_created_by ON tasks(created_by);")
    await conn.execute("CREATE INDEX idx_interactions_agent_id ON interactions(agent_id);")
    
    # Unique constraints
    await conn.execute("""
        CREATE UNIQUE INDEX idx_teams_name_per_org 
        ON teams(organization_id, name);
    """)
    
    # Composite indexes for common queries
    await conn.execute("""
        CREATE INDEX idx_agents_team_status 
        ON agents(team_id, status);
    """)
    
    await conn.execute("""
        CREATE INDEX idx_tasks_agent_status 
        ON tasks(assigned_to, status);
    """)
    
    print("✅ Created all database indexes")

async def downgrade(conn):
    """Rollback the migration"""
    
    # Drop all created indexes
    await conn.execute("DROP INDEX IF EXISTS idx_interactions_embedding;")
    await conn.execute("DROP INDEX IF EXISTS idx_tasks_status;")
    await conn.execute("DROP INDEX IF EXISTS idx_agents_status;")
    await conn.execute("DROP INDEX IF EXISTS idx_agents_team_id;")
    await conn.execute("DROP INDEX IF EXISTS idx_teams_organization_id;")
    await conn.execute("DROP INDEX IF EXISTS idx_tasks_assigned_to;")
    await conn.execute("DROP INDEX IF EXISTS idx_tasks_created_by;")
    await conn.execute("DROP INDEX IF EXISTS idx_interactions_agent_id;")
    await conn.execute("DROP INDEX IF EXISTS idx_teams_name_per_org;")
    await conn.execute("DROP INDEX IF EXISTS idx_agents_team_status;")
    await conn.execute("DROP INDEX IF EXISTS idx_tasks_agent_status;")
    
    print("✅ Dropped all database indexes")