"""
Database Migration Manager for FuzeAgent

Handles schema migrations, data seeding, and version tracking.
"""

import asyncpg
import os
import re
import importlib.util
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationError(Exception):
    """Custom exception for migration errors"""

    pass


class Migration:
    """Represents a single database migration"""

    def __init__(self, version: str, name: str, file_path: str):
        self.version = version
        self.name = name
        self.file_path = file_path
        self.timestamp = self._extract_timestamp(version)

    def _extract_timestamp(self, version: str) -> datetime:
        """Extract timestamp from version string (format: YYYYMMDD_HHMMSS)"""
        try:
            return datetime.strptime(version, "%Y%m%d_%H%M%S")
        except ValueError:
            # Fallback for simple numeric versions
            return datetime.fromtimestamp(int(version) if version.isdigit() else 0)

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __str__(self):
        return f"Migration({self.version}_{self.name})"


class MigrationManager:
    """Manages database migrations and schema versioning"""

    def __init__(self, database_url: str, migrations_dir: str = None):
        self.database_url = database_url
        self.migrations_dir = migrations_dir or str(
            Path(__file__).parent / "migrations"
        )

    async def _get_connection(self) -> asyncpg.Connection:
        """Get database connection"""
        return await asyncpg.connect(self.database_url)

    async def _ensure_migrations_table(self, conn: asyncpg.Connection):
        """Create migrations tracking table if it doesn't exist"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(50) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum VARCHAR(64),
                execution_time_ms INTEGER
            )
        """)
        logger.info("Ensured schema_migrations table exists")

    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions"""
        async with await self._get_connection() as conn:
            await self._ensure_migrations_table(conn)
            rows = await conn.fetch(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return [row["version"] for row in rows]

    def discover_migrations(self) -> List[Migration]:
        """Discover all migration files in the migrations directory"""
        migrations = []
        migrations_path = Path(self.migrations_dir)

        if not migrations_path.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations

        # Pattern: YYYYMMDD_HHMMSS_migration_name.py
        pattern = re.compile(r"^(\d{8}_\d{6})_(.+)\.py$")

        for file_path in migrations_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue

            match = pattern.match(file_path.name)
            if match:
                version, name = match.groups()
                migrations.append(Migration(version, name, str(file_path)))
            else:
                logger.warning(
                    f"Skipping migration file with invalid name format: {file_path.name}"
                )

        return sorted(migrations)

    async def load_migration_module(self, migration: Migration):
        """Load a migration module dynamically"""
        spec = importlib.util.spec_from_file_location(
            f"migration_{migration.version}", migration.file_path
        )
        if spec is None or spec.loader is None:
            raise MigrationError(f"Could not load migration {migration}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    async def apply_migration(
        self, migration: Migration, conn: asyncpg.Connection
    ) -> int:
        """Apply a single migration"""
        logger.info(f"Applying migration: {migration}")

        try:
            # Load migration module
            module = await self.load_migration_module(migration)

            if not hasattr(module, "upgrade"):
                raise MigrationError(
                    f"Migration {migration} missing 'upgrade' function"
                )

            # Start timing
            start_time = datetime.now()

            # Apply migration in transaction
            async with conn.transaction():
                await module.upgrade(conn)

                # Record migration as applied
                execution_time = int(
                    (datetime.now() - start_time).total_seconds() * 1000
                )
                await conn.execute(
                    """
                    INSERT INTO schema_migrations (version, name, applied_at, execution_time_ms)
                    VALUES ($1, $2, $3, $4)
                """,
                    migration.version,
                    migration.name,
                    datetime.now(),
                    execution_time,
                )

            logger.info(
                f"Successfully applied migration: {migration} ({execution_time}ms)"
            )
            return execution_time

        except Exception as e:
            logger.error(f"Failed to apply migration {migration}: {str(e)}")
            raise MigrationError(f"Migration {migration} failed: {str(e)}")

    async def rollback_migration(self, migration: Migration, conn: asyncpg.Connection):
        """Rollback a single migration"""
        logger.info(f"Rolling back migration: {migration}")

        try:
            # Load migration module
            module = await self.load_migration_module(migration)

            if not hasattr(module, "downgrade"):
                raise MigrationError(
                    f"Migration {migration} missing 'downgrade' function"
                )

            # Rollback migration in transaction
            async with conn.transaction():
                await module.downgrade(conn)

                # Remove migration from tracking table
                await conn.execute(
                    "DELETE FROM schema_migrations WHERE version = $1",
                    migration.version,
                )

            logger.info(f"Successfully rolled back migration: {migration}")

        except Exception as e:
            logger.error(f"Failed to rollback migration {migration}: {str(e)}")
            raise MigrationError(f"Migration rollback {migration} failed: {str(e)}")

    async def migrate_up(self, target_version: str = None) -> List[str]:
        """Apply all pending migrations up to target version"""
        logger.info("Starting database migration...")

        async with await self._get_connection() as conn:
            await self._ensure_migrations_table(conn)

            # Get applied and available migrations
            applied_versions = set(await self.get_applied_migrations())
            available_migrations = self.discover_migrations()

            # Filter pending migrations
            pending_migrations = [
                m
                for m in available_migrations
                if m.version not in applied_versions
                and (target_version is None or m.version <= target_version)
            ]

            if not pending_migrations:
                logger.info("No pending migrations found")
                return []

            applied_migrations = []
            total_time = 0

            for migration in pending_migrations:
                execution_time = await self.apply_migration(migration, conn)
                applied_migrations.append(migration.version)
                total_time += execution_time

            logger.info(
                f"Applied {len(applied_migrations)} migrations in {total_time}ms"
            )
            return applied_migrations

    async def migrate_down(self, target_version: str) -> List[str]:
        """Rollback migrations down to target version"""
        logger.info(f"Rolling back migrations to version: {target_version}")

        async with await self._get_connection() as conn:
            await self._ensure_migrations_table(conn)

            # Get applied migrations
            applied_versions = await self.get_applied_migrations()
            available_migrations = {m.version: m for m in self.discover_migrations()}

            # Find migrations to rollback (in reverse order)
            rollback_versions = [
                v for v in reversed(applied_versions) if v > target_version
            ]

            if not rollback_versions:
                logger.info(f"No migrations to rollback to version {target_version}")
                return []

            rolled_back = []

            for version in rollback_versions:
                if version in available_migrations:
                    migration = available_migrations[version]
                    await self.rollback_migration(migration, conn)
                    rolled_back.append(version)
                else:
                    logger.warning(f"Migration file not found for version {version}")

            logger.info(f"Rolled back {len(rolled_back)} migrations")
            return rolled_back

    async def get_migration_status(self) -> Dict:
        """Get current migration status"""
        async with await self._get_connection() as conn:
            await self._ensure_migrations_table(conn)

            applied_versions = set(await self.get_applied_migrations())
            available_migrations = self.discover_migrations()

            pending_migrations = [
                m for m in available_migrations if m.version not in applied_versions
            ]

            # Get last applied migration info
            last_applied = None
            if applied_versions:
                last_applied_row = await conn.fetchrow("""
                    SELECT version, name, applied_at, execution_time_ms 
                    FROM schema_migrations 
                    ORDER BY version DESC 
                    LIMIT 1
                """)
                if last_applied_row:
                    last_applied = dict(last_applied_row)

            return {
                "total_migrations": len(available_migrations),
                "applied_count": len(applied_versions),
                "pending_count": len(pending_migrations),
                "last_applied": last_applied,
                "pending_migrations": [
                    {"version": m.version, "name": m.name} for m in pending_migrations
                ],
            }

    async def reset_database(self):
        """Reset database by dropping all tables (DANGER!)"""
        logger.warning("RESETTING DATABASE - ALL DATA WILL BE LOST!")

        async with await self._get_connection() as conn:
            # Get all table names
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)

            # Drop all tables
            for table in tables:
                await conn.execute(
                    f'DROP TABLE IF EXISTS "{table["tablename"]}" CASCADE'
                )
                logger.info(f"Dropped table: {table['tablename']}")

            logger.info("Database reset complete")


# CLI-style functions for easy usage
async def migrate(database_url: str, target_version: str = None):
    """Run migrations"""
    manager = MigrationManager(database_url)
    return await manager.migrate_up(target_version)


async def rollback(database_url: str, target_version: str):
    """Rollback to target version"""
    manager = MigrationManager(database_url)
    return await manager.migrate_down(target_version)


async def status(database_url: str):
    """Get migration status"""
    manager = MigrationManager(database_url)
    return await manager.get_migration_status()


async def reset(database_url: str):
    """Reset database (DANGER!)"""
    manager = MigrationManager(database_url)
    await manager.reset_database()
