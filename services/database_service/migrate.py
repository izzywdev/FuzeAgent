#!/usr/bin/env python3
"""
FuzeAgent Database Migration Script

This script helps with database migrations and schema updates.
"""

import asyncio
import asyncpg
import os
from typing import List

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

async def get_current_schema_version(conn) -> int:
    """Get the current schema version from the database"""
    try:
        # Check if migrations table exists
        exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'schema_migrations'
            )
            """
        )
        
        if not exists:
            # Create migrations table
            await conn.execute(
                """
                CREATE TABLE schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version INTEGER NOT NULL UNIQUE,
                    description TEXT,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """
            )
            print("✅ Created schema_migrations table")
            return 0
        
        # Get the latest version
        version = await conn.fetchval(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        )
        return version or 0
        
    except Exception as e:
        print(f"❌ Failed to get schema version: {e}")
        return 0

async def apply_migration(conn, version: int, description: str, sql: str):
    """Apply a migration to the database"""
    try:
        # Start transaction
        async with conn.transaction():
            # Execute migration SQL
            await conn.execute(sql)
            
            # Record migration
            await conn.execute(
                """
                INSERT INTO schema_migrations (version, description)
                VALUES ($1, $2)
                """,
                version,
                description
            )
            
        print(f"✅ Applied migration {version}: {description}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to apply migration {version}: {e}")
        return False

async def list_applied_migrations(conn) -> List[dict]:
    """List all applied migrations"""
    try:
        rows = await conn.fetch(
            """
            SELECT version, description, applied_at
            FROM schema_migrations
            ORDER BY version
            """
        )
        migrations = [dict(row) for row in rows]
        return migrations
        
    except Exception as e:
        print(f"❌ Failed to list migrations: {e}")
        return []

# Example migrations
MIGRATIONS = [
    {
        "version": 1,
        "description": "Add indexes for better query performance",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);
            CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type);
            CREATE INDEX IF NOT EXISTS idx_teams_type ON teams(team_type);
        """
    },
    {
        "version": 2,
        "description": "Add task complexity and estimated hours fields",
        "sql": """
            ALTER TABLE tasks 
            ADD COLUMN IF NOT EXISTS complexity VARCHAR(20) DEFAULT 'medium',
            ADD COLUMN IF NOT EXISTS estimated_hours DECIMAL(5,2),
            ADD COLUMN IF NOT EXISTS actual_hours DECIMAL(5,2);
        """
    },
    {
        "version": 3,
        "description": "Add agent expertise tracking",
        "sql": """
            ALTER TABLE agents
            ADD COLUMN IF NOT EXISTS expertise_tags JSONB DEFAULT '[]',
            ADD COLUMN IF NOT EXISTS performance_score DECIMAL(3,2) DEFAULT 0.0;
        """
    }
]

async def main():
    """Main function to handle database migrations"""
    print("🚀 FuzeAgent Database Migration Script")
    print("=" * 50)
    
    # Connect to the database
    conn = await connect_to_database()
    if not conn:
        return
    
    try:
        # Get current schema version
        current_version = await get_current_schema_version(conn)
        print(f"📊 Current schema version: {current_version}")
        
        # List applied migrations
        applied_migrations = await list_applied_migrations(conn)
        if applied_migrations:
            print("\n📋 Applied migrations:")
            for migration in applied_migrations:
                print(f"  v{migration['version']} - {migration['description']} "
                      f"({migration['applied_at']})")
        else:
            print("\n📋 No migrations have been applied yet")
        
        # Check for pending migrations
        pending_migrations = [m for m in MIGRATIONS if m["version"] > current_version]
        
        if pending_migrations:
            print(f"\n🆕 {len(pending_migrations)} pending migrations found:")
            for migration in pending_migrations:
                print(f"  v{migration['version']} - {migration['description']}")
            
            # Ask user if they want to apply migrations
            response = input("\nDo you want to apply these migrations? (y/N): ")
            if response.lower() in ['y', 'yes']:
                print("\n🔄 Applying migrations...")
                for migration in pending_migrations:
                    success = await apply_migration(
                        conn,
                        migration["version"],
                        migration["description"],
                        migration["sql"]
                    )
                    if not success:
                        print("❌ Migration process aborted due to error")
                        return
                print("\n🎉 All migrations applied successfully!")
            else:
                print("ℹ️  Migration process cancelled by user")
        else:
            print("\n✅ Database schema is up to date")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        # Close the connection
        await conn.close()
        print("\n🔒 Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())