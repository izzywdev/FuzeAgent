#!/usr/bin/env python3
"""
FuzeAgent Database Connection Example

This script demonstrates how to connect to the FuzeAgent database
and perform basic operations.
"""

import asyncio
import asyncpg
import os
from typing import List, Dict, Any

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ai_context")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

async def connect_to_database():
    """Create a connection to the database"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        print("✅ Successfully connected to the database")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to the database: {e}")
        return None

async def create_sample_organization(conn) -> str:
    """Create a sample organization"""
    try:
        org_id = await conn.fetchval(
            """
            INSERT INTO organizations (name, description)
            VALUES ($1, $2)
            RETURNING id
            """,
            "Sample Organization",
            "This is a sample organization for testing"
        )
        print(f"✅ Created organization with ID: {org_id}")
        return str(org_id)
    except Exception as e:
        print(f"❌ Failed to create organization: {e}")
        return None

async def create_sample_team(conn, org_id: str) -> str:
    """Create a sample team"""
    try:
        team_id = await conn.fetchval(
            """
            INSERT INTO teams (organization_id, name, description)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            org_id,
            "Sample Team",
            "This is a sample team for testing"
        )
        print(f"✅ Created team with ID: {team_id}")
        return str(team_id)
    except Exception as e:
        print(f"❌ Failed to create team: {e}")
        return None

async def create_sample_agent(conn, team_id: str) -> str:
    """Create a sample agent"""
    try:
        agent_id = await conn.fetchval(
            """
            INSERT INTO agents (team_id, name, role, type, status)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            team_id,
            "Sample Agent",
            "Test Agent",
            "general",
            "active"
        )
        print(f"✅ Created agent with ID: {agent_id}")
        return str(agent_id)
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return None

async def create_sample_task(conn, agent_id: str) -> str:
    """Create a sample task"""
    try:
        task_id = await conn.fetchval(
            """
            INSERT INTO tasks (title, description, assigned_to, status)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            "Sample Task",
            "This is a sample task for testing",
            agent_id,
            "pending"
        )
        print(f"✅ Created task with ID: {task_id}")
        return str(task_id)
    except Exception as e:
        print(f"❌ Failed to create task: {e}")
        return None

async def list_organizations(conn) -> List[Dict[str, Any]]:
    """List all organizations"""
    try:
        rows = await conn.fetch(
            """
            SELECT id, name, description, created_at
            FROM organizations
            ORDER BY created_at DESC
            """
        )
        organizations = [dict(row) for row in rows]
        print(f"✅ Found {len(organizations)} organizations")
        return organizations
    except Exception as e:
        print(f"❌ Failed to list organizations: {e}")
        return []

async def list_teams(conn, org_id: str = None) -> List[Dict[str, Any]]:
    """List teams, optionally filtered by organization"""
    try:
        if org_id:
            rows = await conn.fetch(
                """
                SELECT t.id, t.name, t.description, t.created_at, o.name as organization_name
                FROM teams t
                JOIN organizations o ON t.organization_id = o.id
                WHERE t.organization_id = $1
                ORDER BY t.created_at DESC
                """,
                org_id
            )
        else:
            rows = await conn.fetch(
                """
                SELECT t.id, t.name, t.description, t.created_at, o.name as organization_name
                FROM teams t
                JOIN organizations o ON t.organization_id = o.id
                ORDER BY t.created_at DESC
                """
            )
        teams = [dict(row) for row in rows]
        print(f"✅ Found {len(teams)} teams")
        return teams
    except Exception as e:
        print(f"❌ Failed to list teams: {e}")
        return []

async def list_agents(conn, team_id: str = None) -> List[Dict[str, Any]]:
    """List agents, optionally filtered by team"""
    try:
        if team_id:
            rows = await conn.fetch(
                """
                SELECT a.id, a.name, a.role, a.type, a.status, a.created_at, t.name as team_name
                FROM agents a
                JOIN teams t ON a.team_id = t.id
                WHERE a.team_id = $1
                ORDER BY a.created_at DESC
                """,
                team_id
            )
        else:
            rows = await conn.fetch(
                """
                SELECT a.id, a.name, a.role, a.type, a.status, a.created_at, t.name as team_name
                FROM agents a
                JOIN teams t ON a.team_id = t.id
                ORDER BY a.created_at DESC
                """
            )
        agents = [dict(row) for row in rows]
        print(f"✅ Found {len(agents)} agents")
        return agents
    except Exception as e:
        print(f"❌ Failed to list agents: {e}")
        return []

async def list_tasks(conn) -> List[Dict[str, Any]]:
    """List all tasks"""
    try:
        rows = await conn.fetch(
            """
            SELECT t.id, t.title, t.description, t.status, t.created_at, 
                   a.name as assigned_agent_name
            FROM tasks t
            LEFT JOIN agents a ON t.assigned_to = a.id
            ORDER BY t.created_at DESC
            """
        )
        tasks = [dict(row) for row in rows]
        print(f"✅ Found {len(tasks)} tasks")
        return tasks
    except Exception as e:
        print(f"❌ Failed to list tasks: {e}")
        return []

async def main():
    """Main function to demonstrate database operations"""
    print("🚀 FuzeAgent Database Connection Example")
    print("=" * 50)
    
    # Connect to the database
    conn = await connect_to_database()
    if not conn:
        return
    
    try:
        # Create sample data
        print("\n📝 Creating sample data...")
        org_id = await create_sample_organization(conn)
        if not org_id:
            return
            
        team_id = await create_sample_team(conn, org_id)
        if not team_id:
            return
            
        agent_id = await create_sample_agent(conn, team_id)
        if not agent_id:
            return
            
        task_id = await create_sample_task(conn, agent_id)
        if not task_id:
            return
            
        # List data
        print("\n📋 Listing data...")
        organizations = await list_organizations(conn)
        for org in organizations:
            print(f"  🏢 {org['name']} (ID: {org['id']})")
            
        teams = await list_teams(conn)
        for team in teams:
            print(f"  👥 {team['name']} (ID: {team['id']}) - Organization: {team['organization_name']}")
            
        agents = await list_agents(conn)
        for agent in agents:
            print(f"  🤖 {agent['name']} (ID: {agent['id']}) - Team: {agent['team_name']}")
            
        tasks = await list_tasks(conn)
        for task in tasks:
            print(f"  ✅ {task['title']} (ID: {task['id']}) - Status: {task['status']}")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        # Close the connection
        await conn.close()
        print("\n🔒 Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())