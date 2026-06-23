"""
Migration: Seed Initial Data
Created: 2025-01-29T12:00:03
Description: Seeds the database with default organization, team, and essential data
"""

# Default IDs for consistent referencing
DEFAULT_ORG_ID = "550e8400-e29b-41d4-a716-446655440000"
DEFAULT_TEAM_ID = "550e8400-e29b-41d4-a716-446655440001"


async def upgrade(conn):
    """Apply the migration"""

    # Insert default organization
    await conn.execute(
        """
        INSERT INTO organizations (id, name, description, settings) 
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (id) DO NOTHING;
    """,
        DEFAULT_ORG_ID,
        "Default Organization",
        "Default organization for initial setup",
        {
            "created_by": "system",
            "is_default": True,
            "features": ["agents", "teams", "tasks", "templates"],
        },
    )

    # Insert default team
    await conn.execute(
        """
        INSERT INTO teams (id, organization_id, name, description, team_type, settings) 
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (id) DO NOTHING;
    """,
        DEFAULT_TEAM_ID,
        DEFAULT_ORG_ID,
        "Default Team",
        "Default team for initial setup",
        "general",
        {"created_by": "system", "is_default": True, "max_agents": 50},
    )

    # Insert sample AI CEO agent for demonstration
    await conn.execute(
        """
        INSERT INTO agents (team_id, name, role, type, status, config, template_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT DO NOTHING;
    """,
        DEFAULT_TEAM_ID,
        "IzzyAI CEO",
        "Digital Chief Executive Officer",
        "executive",
        "active",
        {
            "goal": "Lead the organization with strategic vision and efficient resource allocation",
            "backstory": "An AI executive with expertise in strategic planning, team management, and business operations",
            "model": "claude-sonnet-4-20250514",
            "temperature": 0.7,
            "tools": [
                "strategic_planning",
                "resource_allocation",
                "team_management",
                "decision_making",
            ],
            "skills": ["leadership", "strategy", "communication", "analysis"],
            "personality": "Strategic, decisive, and collaborative",
        },
        "ai_human_manager",
    )

    print("✅ Seeded initial organization, team, and sample agent")


async def downgrade(conn):
    """Rollback the migration"""

    # Remove seeded data in reverse dependency order
    await conn.execute(
        "DELETE FROM agents WHERE template_id = 'ai_human_manager' AND name = 'IzzyAI CEO';"
    )
    await conn.execute(f"DELETE FROM teams WHERE id = '{DEFAULT_TEAM_ID}';")
    await conn.execute(f"DELETE FROM organizations WHERE id = '{DEFAULT_ORG_ID}';")

    print("✅ Removed seeded initial data")
