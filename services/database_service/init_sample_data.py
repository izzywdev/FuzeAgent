#!/usr/bin/env python3
"""
FuzeAgent Database Initialization Script

This script initializes the database with sample data for testing and development.
"""

import asyncio
import asyncpg
import os
from datetime import datetime
from uuid import uuid4

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

async def initialize_sample_data(conn):
    """Initialize the database with sample data"""
    try:
        # Create sample organizations
        org_ids = []
        for i in range(3):
            org_id = await conn.fetchval(
                """
                INSERT INTO organizations (name, description, settings)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                f"Organization {i+1}",
                f"Description for Organization {i+1}",
                {"created_by": "init_script", "created_at": datetime.now().isoformat()}
            )
            org_ids.append(org_id)
            print(f"✅ Created organization: Organization {i+1} (ID: {org_id})")
        
        # Create sample teams
        team_ids = []
        for i, org_id in enumerate(org_ids):
            for j in range(2):
                team_id = await conn.fetchval(
                    """
                    INSERT INTO teams (organization_id, name, description, team_type, settings)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    org_id,
                    f"Team {j+1} Org {i+1}",
                    f"Description for Team {j+1} in Organization {i+1}",
                    "development" if j == 0 else "research",
                    {"created_by": "init_script", "created_at": datetime.now().isoformat()}
                )
                team_ids.append(team_id)
                print(f"✅ Created team: Team {j+1} Org {i+1} (ID: {team_id})")
        
        # Create sample agents
        agent_ids = []
        agent_types = ["developer", "researcher", "analyst", "tester"]
        agent_roles = [
            "Senior Python Developer",
            "Machine Learning Researcher", 
            "Data Analyst",
            "QA Engineer"
        ]
        
        for i, team_id in enumerate(team_ids):
            for j in range(3):
                agent_id = await conn.fetchval(
                    """
                    INSERT INTO agents (team_id, name, role, type, status, config)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    team_id,
                    f"Agent {j+1} Team {((i//2)+1)}",
                    agent_roles[j % len(agent_roles)],
                    agent_types[j % len(agent_types)],
                    "active",
                    {
                        "model": "claude-sonnet-4-20250514",
                        "temperature": 0.7,
                        "created_by": "init_script",
                        "created_at": datetime.now().isoformat()
                    }
                )
                agent_ids.append(agent_id)
                print(f"✅ Created agent: Agent {j+1} Team {((i//2)+1)} (ID: {agent_id})")
        
        # Create sample tasks
        task_statuses = ["pending", "in_progress", "completed", "failed"]
        task_priorities = ["low", "medium", "high"]
        
        for i, agent_id in enumerate(agent_ids[:10]):  # Create tasks for first 10 agents
            for j in range(2):
                task_id = await conn.fetchval(
                    """
                    INSERT INTO tasks (title, description, status, priority, assigned_to, created_by, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                    """,
                    f"Task {j+1} for Agent {i+1}",
                    f"Detailed description for Task {j+1} assigned to Agent {i+1}",
                    task_statuses[(i+j) % len(task_statuses)],
                    task_priorities[(i+j) % len(task_priorities)],
                    agent_id,
                    agent_id,
                    {
                        "created_by": "init_script",
                        "created_at": datetime.now().isoformat(),
                        "tags": ["sample", "test", f"agent-{i+1}"]
                    }
                )
                print(f"✅ Created task: Task {j+1} for Agent {i+1} (ID: {task_id})")
                
                # Update some tasks as completed
                if task_statuses[(i+j) % len(task_statuses)] == "completed":
                    await conn.execute(
                        """
                        UPDATE tasks 
                        SET completed_at = $1, result = $2
                        WHERE id = $3
                        """,
                        datetime.now(),
                        {"success": True, "output": "Task completed successfully"},
                        task_id
                    )
        
        # Create sample chat sessions and conversations
        for i, agent_id in enumerate(agent_ids[:5]):  # Create chats for first 5 agents
            # Create chat session
            session_id = await conn.fetchval(
                """
                INSERT INTO chat_sessions (agent_id, session_name, context, status)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                agent_id,
                f"Chat Session {i+1}",
                {"topic": "Sample conversation", "created_by": "init_script"},
                "active"
            )
            print(f"✅ Created chat session for Agent {i+1} (ID: {session_id})")
            
            # Create sample messages
            for j in range(3):
                await conn.execute(
                    """
                    INSERT INTO agent_conversations (session_id, agent_id, message_type, content, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    session_id,
                    agent_id,
                    "user" if j % 2 == 0 else "agent",
                    f"Sample message {j+1} in chat session {i+1}",
                    {
                        "created_by": "init_script",
                        "created_at": datetime.now().isoformat(),
                        "message_number": j+1
                    }
                )
            print(f"✅ Created 3 sample messages for chat session {i+1}")
        
        print("\n🎉 Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize sample data: {e}")
        return False

async def main():
    """Main function to initialize the database"""
    print("🚀 FuzeAgent Database Initialization Script")
    print("=" * 50)
    
    # Connect to the database
    conn = await connect_to_database()
    if not conn:
        return
    
    try:
        # Initialize sample data
        print("\n📝 Initializing database with sample data...")
        success = await initialize_sample_data(conn)
        
        if success:
            print("\n✅ Sample data initialization completed!")
        else:
            print("\n❌ Sample data initialization failed!")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        # Close the connection
        await conn.close()
        print("\n🔒 Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())