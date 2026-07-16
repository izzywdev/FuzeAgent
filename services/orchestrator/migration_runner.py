#!/usr/bin/env python3
"""
Database Migration Runner for FuzeAgent Autonomous Execution
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List

import asyncpg

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationRunner:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.migrations_dir = Path(__file__).parent / "migrations"

    async def create_migrations_table(self, conn):
        """Create migrations tracking table if it doesn't exist"""
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(255) PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """
        )

    async def get_applied_migrations(self, conn) -> List[str]:
        """Get list of already applied migrations"""
        rows = await conn.fetch(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
        return [row["version"] for row in rows]

    async def get_pending_migrations(self, conn) -> List[Path]:
        """Get list of pending migration files"""
        applied = await self.get_applied_migrations(conn)

        migration_files = []
        if self.migrations_dir.exists():
            for file_path in sorted(self.migrations_dir.glob("*.sql")):
                # Extract version from filename (e.g., "001_add_schema.sql" -> "001")
                version = file_path.stem.split("_")[0]
                if version not in applied:
                    migration_files.append(file_path)

        return migration_files

    async def apply_migration(self, conn, migration_file: Path):
        """Apply a single migration file"""
        version = migration_file.stem.split("_")[0]

        logger.info(f"Applying migration {migration_file.name}...")

        try:
            # Read and execute migration SQL
            sql_content = migration_file.read_text()
            await conn.execute(sql_content)

            # Record migration as applied
            await conn.execute(
                """
                INSERT INTO schema_migrations (version, filename) 
                VALUES ($1, $2)
            """,
                version,
                migration_file.name,
            )

            logger.info(f"✅ Migration {migration_file.name} applied successfully")

        except Exception as e:
            logger.error(f"❌ Failed to apply migration {migration_file.name}: {e}")
            raise

    async def run_migrations(self):
        """Run all pending migrations"""
        conn = await asyncpg.connect(self.database_url)

        try:
            # Create migrations table
            await self.create_migrations_table(conn)

            # Get pending migrations
            pending_migrations = await self.get_pending_migrations(conn)

            if not pending_migrations:
                logger.info("✅ No pending migrations found")
                return

            logger.info(f"Found {len(pending_migrations)} pending migrations")

            # Apply each migration in order
            for migration_file in pending_migrations:
                await self.apply_migration(conn, migration_file)

            logger.info("✅ All migrations applied successfully")

        finally:
            await conn.close()

    async def rollback_migration(self, version: str):
        """Rollback a specific migration (if rollback file exists)"""
        conn = await asyncpg.connect(self.database_url)

        try:
            rollback_file = self.migrations_dir / f"{version}_rollback.sql"
            if not rollback_file.exists():
                logger.error(f"❌ Rollback file not found: {rollback_file}")
                return

            logger.info(f"Rolling back migration {version}...")

            # Execute rollback SQL
            sql_content = rollback_file.read_text()
            await conn.execute(sql_content)

            # Remove from migrations table
            await conn.execute(
                """
                DELETE FROM schema_migrations WHERE version = $1
            """,
                version,
            )

            logger.info(f"✅ Migration {version} rolled back successfully")

        except Exception as e:
            logger.error(f"❌ Failed to rollback migration {version}: {e}")
            raise
        finally:
            await conn.close()

    async def show_migration_status(self):
        """Show current migration status"""
        conn = await asyncpg.connect(self.database_url)

        try:
            await self.create_migrations_table(conn)

            applied = await self.get_applied_migrations(conn)
            pending = await self.get_pending_migrations(conn)

            print("\n📊 Migration Status:")
            print(f"Applied migrations: {len(applied)}")
            for version in applied:
                print(f"  ✅ {version}")

            print(f"\nPending migrations: {len(pending)}")
            for migration_file in pending:
                version = migration_file.stem.split("_")[0]
                print(f"  ⏳ {version} - {migration_file.name}")

        finally:
            await conn.close()


async def main():
    """Main CLI interface"""
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@localhost:5434/ai_context"
    )

    if len(sys.argv) < 2:
        print("Usage: python migration_runner.py [migrate|rollback|status]")
        print("  migrate - Apply all pending migrations")
        print("  rollback <version> - Rollback specific migration")
        print("  status - Show migration status")
        sys.exit(1)

    command = sys.argv[1]
    runner = MigrationRunner(database_url)

    try:
        if command == "migrate":
            await runner.run_migrations()
        elif command == "rollback":
            if len(sys.argv) < 3:
                print("Error: rollback requires version argument")
                sys.exit(1)
            version = sys.argv[2]
            await runner.rollback_migration(version)
        elif command == "status":
            await runner.show_migration_status()
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
