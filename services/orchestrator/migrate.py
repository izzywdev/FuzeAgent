#!/usr/bin/env python3
"""
Database Migration CLI for FuzeAgent

Usage:
    python migrate.py status                    # Show migration status
    python migrate.py up                        # Apply all pending migrations
    python migrate.py up 20250129_120000        # Apply migrations up to version
    python migrate.py down 20250129_100000      # Rollback to version
    python migrate.py create migration_name     # Create new migration file
    python migrate.py reset                     # Reset database (DANGER!)
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
import argparse

from migration_manager import MigrationManager, migrate, rollback, status, reset

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5434/ai_context")

def create_migration_template(name: str) -> str:
    """Create a new migration file template"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{name}.py"
    
    template = f'''"""
Migration: {name}
Created: {datetime.now().isoformat()}
"""

async def upgrade(conn):
    """Apply the migration"""
    # Add your schema changes here
    await conn.execute("""
        -- Your SQL commands here
        -- Example:
        -- CREATE TABLE example (
        --     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        --     name VARCHAR(255) NOT NULL,
        --     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        -- );
    """)
    print(f"Applied migration: {name}")

async def downgrade(conn):
    """Rollback the migration"""
    # Add your rollback commands here
    await conn.execute("""
        -- Your rollback SQL commands here
        -- Example:
        -- DROP TABLE IF EXISTS example;
    """)
    print(f"Rolled back migration: {name}")
'''
    
    return filename, template

async def main():
    parser = argparse.ArgumentParser(description="FuzeAgent Database Migration Tool")
    parser.add_argument("command", choices=["status", "up", "down", "create", "reset"],
                       help="Migration command to run")
    parser.add_argument("target", nargs="?", help="Target version or migration name")
    parser.add_argument("--database-url", default=DATABASE_URL,
                       help="Database connection URL")
    
    args = parser.parse_args()
    
    try:
        if args.command == "status":
            print("🔍 Checking migration status...")
            migration_status = await status(args.database_url)
            
            print(f"📊 Migration Status:")
            print(f"   Total migrations: {migration_status['total_migrations']}")
            print(f"   Applied: {migration_status['applied_count']}")
            print(f"   Pending: {migration_status['pending_count']}")
            
            if migration_status['last_applied']:
                last = migration_status['last_applied']
                print(f"   Last applied: {last['version']}_{last['name']} ({last['applied_at']})")
            
            if migration_status['pending_migrations']:
                print(f"\n⏳ Pending migrations:")
                for migration in migration_status['pending_migrations']:
                    print(f"   - {migration['version']}_{migration['name']}")
            else:
                print(f"\n✅ Database is up to date!")
        
        elif args.command == "up":
            print("⬆️  Applying migrations...")
            applied = await migrate(args.database_url, args.target)
            
            if applied:
                print(f"✅ Applied {len(applied)} migrations:")
                for version in applied:
                    print(f"   - {version}")
            else:
                print("✅ No migrations to apply - database is up to date!")
        
        elif args.command == "down":
            if not args.target:
                print("❌ Target version required for rollback")
                sys.exit(1)
            
            print(f"⬇️  Rolling back to version: {args.target}")
            rolled_back = await rollback(args.database_url, args.target)
            
            if rolled_back:
                print(f"✅ Rolled back {len(rolled_back)} migrations:")
                for version in rolled_back:
                    print(f"   - {version}")
            else:
                print(f"✅ No migrations to rollback!")
        
        elif args.command == "create":
            if not args.target:
                print("❌ Migration name required")
                sys.exit(1)
            
            migrations_dir = Path(__file__).parent / "migrations"
            migrations_dir.mkdir(exist_ok=True)
            
            filename, template = create_migration_template(args.target)
            file_path = migrations_dir / filename
            
            file_path.write_text(template)
            print(f"✅ Created migration: {file_path}")
            print(f"📝 Edit the file to add your schema changes")
        
        elif args.command == "reset":
            print("⚠️  WARNING: This will DELETE ALL DATA!")
            response = input("Type 'yes' to confirm database reset: ")
            
            if response.lower() == "yes":
                print("🗑️  Resetting database...")  
                await reset(args.database_url)
                print("✅ Database reset complete!")
            else:
                print("❌ Database reset cancelled")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())