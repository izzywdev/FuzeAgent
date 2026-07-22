import pytest

# QUARANTINED — see izzywdev/FuzeAgent#80.
# These tests assert an aspirational MigrationManager API that was never built:
# a `db_pool` pool attribute, `initialize()`/`close()`, `discover_migration_files()`
# returning dicts, `apply_migration(dict)`/`migrate_up()`/`get_applied_migrations()`
# returning dicts. The real manager uses a per-call `_get_connection()`, takes
# `Migration` objects, and returns `List[str]`. Un-skipping requires freezing the
# intended MigrationManager contract (contract-designer) and implementing it without
# breaking current callers (main_with_hierarchy.py, migrate.py) — a product decision,
# not a test rewrite. Skipped at collection to track the debt honestly.
pytestmark = pytest.mark.skip(
    reason="aspirational MigrationManager API not yet built; see #80"
)

"""
Test cases for Migration Manager functionality
"""

import os
import tempfile
from unittest.mock import AsyncMock, patch

from migration_manager import MigrationManager


@pytest.mark.database
@pytest.mark.asyncio
class TestMigrationManager:
    """Test Migration Manager functionality"""

    @pytest.fixture
    async def migration_manager_clean(self):
        """Clean migration manager for testing"""
        database_url = "postgresql://postgres:password@localhost:5434/ai_context_test"
        manager = MigrationManager(database_url)

        # Clean the migrations table for fresh testing
        async with manager.db_pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")

        yield manager

        # Cleanup
        async with manager.db_pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")

        await manager.close()

    async def test_initialize_creates_migrations_table(self, migration_manager_clean):
        """Test that initialization creates the migrations table"""
        manager = migration_manager_clean

        await manager.initialize()

        # Check that migrations table exists
        async with manager.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'schema_migrations'
                );
            """)
            assert result["exists"] is True

    async def test_get_applied_migrations_empty(self, migration_manager_clean):
        """Test getting applied migrations when none exist"""
        manager = migration_manager_clean
        await manager.initialize()

        applied = await manager.get_applied_migrations()
        assert applied == []

    async def test_discover_migration_files(
        self, migration_manager_clean, temp_directory
    ):
        """Test discovering migration files from directory"""
        manager = migration_manager_clean

        # Create temporary migration files
        migration_files = [
            "20250129_140001_create_tables.py",
            "20250129_140002_add_indexes.py",
            "20250129_140003_alter_columns.py",
        ]

        for filename in migration_files:
            filepath = os.path.join(temp_directory, filename)
            with open(filepath, "w") as f:
                f.write(f"""
\"\"\"
Migration: {filename}
\"\"\"

async def up(conn):
    await conn.execute("SELECT 1")

async def down(conn):
    await conn.execute("SELECT 1")
""")

        # Update migrations directory for testing
        original_dir = manager.migrations_dir
        manager.migrations_dir = temp_directory

        try:
            migrations = await manager.discover_migration_files()
            assert len(migrations) == 3

            # Check they're sorted by timestamp
            timestamps = [m["timestamp"] for m in migrations]
            assert timestamps == sorted(timestamps)

            # Check first migration details
            first_migration = migrations[0]
            assert first_migration["filename"] == "20250129_140001_create_tables.py"
            assert first_migration["version"] == "20250129_140001"
            assert first_migration["description"] == "create_tables"
        finally:
            manager.migrations_dir = original_dir

    async def test_apply_single_migration(
        self, migration_manager_clean, temp_directory
    ):
        """Test applying a single migration"""
        manager = migration_manager_clean
        await manager.initialize()

        # Create test migration file
        migration_content = '''
"""
Test migration
"""

async def up(conn):
    await conn.execute("""
        CREATE TABLE test_migration_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        )
    """)

async def down(conn):
    await conn.execute("DROP TABLE IF EXISTS test_migration_table")
'''

        migration_file = os.path.join(
            temp_directory, "20250129_140001_test_migration.py"
        )
        with open(migration_file, "w") as f:
            f.write(migration_content)

        # Apply migration
        migration_info = {
            "filepath": migration_file,
            "version": "20250129_140001",
            "description": "test_migration",
            "filename": "20250129_140001_test_migration.py",
        }

        result = await manager.apply_migration(migration_info)

        assert result["success"] is True
        assert result["version"] == "20250129_140001"

        # Verify table was created
        async with manager.db_pool.acquire() as conn:
            table_exists = await conn.fetchrow("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'test_migration_table'
                );
            """)
            assert table_exists["exists"] is True

        # Verify migration was recorded
        applied = await manager.get_applied_migrations()
        assert len(applied) == 1
        assert applied[0]["version"] == "20250129_140001"

    async def test_rollback_migration(self, migration_manager_clean, temp_directory):
        """Test rolling back a migration"""
        manager = migration_manager_clean
        await manager.initialize()

        # Create and apply migration first
        migration_content = '''
"""
Rollback test migration
"""

async def up(conn):
    await conn.execute("""
        CREATE TABLE rollback_test_table (
            id SERIAL PRIMARY KEY,
            data TEXT
        )
    """)

async def down(conn):
    await conn.execute("DROP TABLE IF EXISTS rollback_test_table")
'''

        migration_file = os.path.join(
            temp_directory, "20250129_140001_rollback_test.py"
        )
        with open(migration_file, "w") as f:
            f.write(migration_content)

        migration_info = {
            "filepath": migration_file,
            "version": "20250129_140001",
            "description": "rollback_test",
            "filename": "20250129_140001_rollback_test.py",
        }

        # Apply migration
        await manager.apply_migration(migration_info)

        # Verify table exists
        async with manager.db_pool.acquire() as conn:
            table_exists = await conn.fetchrow("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'rollback_test_table'
                );
            """)
            assert table_exists["exists"] is True

        # Rollback migration
        result = await manager.rollback_migration("20250129_140001", migration_file)

        assert result["success"] is True
        assert result["version"] == "20250129_140001"

        # Verify table was dropped
        async with manager.db_pool.acquire() as conn:
            table_exists = await conn.fetchrow("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'rollback_test_table'
                );
            """)
            assert table_exists["exists"] is False

        # Verify migration was removed from applied list
        applied = await manager.get_applied_migrations()
        assert len(applied) == 0

    async def test_migrate_up_multiple_migrations(
        self, migration_manager_clean, temp_directory
    ):
        """Test applying multiple pending migrations"""
        manager = migration_manager_clean
        await manager.initialize()

        # Create multiple migration files
        migration_contents = [
            (
                "20250129_140001_first.py",
                """
async def up(conn):
    await conn.execute("CREATE TABLE first_table (id SERIAL PRIMARY KEY)")

async def down(conn):
    await conn.execute("DROP TABLE IF EXISTS first_table")
""",
            ),
            (
                "20250129_140002_second.py",
                """
async def up(conn):
    await conn.execute("CREATE TABLE second_table (id SERIAL PRIMARY KEY)")

async def down(conn):
    await conn.execute("DROP TABLE IF EXISTS second_table")
""",
            ),
            (
                "20250129_140003_third.py",
                """
async def up(conn):
    await conn.execute("CREATE TABLE third_table (id SERIAL PRIMARY KEY)")

async def down(conn):
    await conn.execute("DROP TABLE IF EXISTS third_table")
""",
            ),
        ]

        for filename, content in migration_contents:
            filepath = os.path.join(temp_directory, filename)
            with open(filepath, "w") as f:
                f.write(content)

        # Update migrations directory
        original_dir = manager.migrations_dir
        manager.migrations_dir = temp_directory

        try:
            # Apply all migrations
            result = await manager.migrate_up()

            assert result["success"] is True
            assert result["applied_count"] == 3

            # Verify all tables were created
            async with manager.db_pool.acquire() as conn:
                for table_name in ["first_table", "second_table", "third_table"]:
                    table_exists = await conn.fetchrow(
                        """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = $1
                        );
                    """,
                        table_name,
                    )
                    assert table_exists["exists"] is True

            # Verify all migrations were recorded
            applied = await manager.get_applied_migrations()
            assert len(applied) == 3

        finally:
            manager.migrations_dir = original_dir

    async def test_migrate_up_with_target_version(
        self, migration_manager_clean, temp_directory
    ):
        """Test migrating up to a specific version"""
        manager = migration_manager_clean
        await manager.initialize()

        # Create multiple migration files
        migration_files = [
            "20250129_140001_first.py",
            "20250129_140002_second.py",
            "20250129_140003_third.py",
        ]

        for filename in migration_files:
            filepath = os.path.join(temp_directory, filename)
            table_name = filename.split("_")[2].replace(".py", "") + "_table"
            content = f"""
async def up(conn):
    await conn.execute("CREATE TABLE {table_name} (id SERIAL PRIMARY KEY)")

async def down(conn):
    await conn.execute("DROP TABLE IF EXISTS {table_name}")
"""
            with open(filepath, "w") as f:
                f.write(content)

        original_dir = manager.migrations_dir
        manager.migrations_dir = temp_directory

        try:
            # Migrate up to second version only
            result = await manager.migrate_up(target_version="20250129_140002")

            assert result["success"] is True
            assert result["applied_count"] == 2

            # Verify only first two tables exist
            async with manager.db_pool.acquire() as conn:
                first_exists = await conn.fetchrow("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'first_table'
                    );
                """)
                second_exists = await conn.fetchrow("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'second_table'
                    );
                """)
                third_exists = await conn.fetchrow("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'third_table'
                    );
                """)

                assert first_exists["exists"] is True
                assert second_exists["exists"] is True
                assert third_exists["exists"] is False

        finally:
            manager.migrations_dir = original_dir

    async def test_get_migration_status(self, migration_manager_clean, temp_directory):
        """Test getting migration status"""
        manager = migration_manager_clean
        await manager.initialize()

        # Create migration files
        migration_files = ["20250129_140001_test.py", "20250129_140002_test2.py"]

        for filename in migration_files:
            filepath = os.path.join(temp_directory, filename)
            with open(filepath, "w") as f:
                f.write("""
async def up(conn):
    await conn.execute("SELECT 1")

async def down(conn):
    await conn.execute("SELECT 1")
""")

        original_dir = manager.migrations_dir
        manager.migrations_dir = temp_directory

        try:
            # Apply first migration only
            migration_info = {
                "filepath": os.path.join(temp_directory, "20250129_140001_test.py"),
                "version": "20250129_140001",
                "description": "test",
                "filename": "20250129_140001_test.py",
            }
            await manager.apply_migration(migration_info)

            # Get status
            status = await manager.get_migration_status()

            assert "applied_migrations" in status
            assert "pending_migrations" in status
            assert "total_migrations" in status

            assert len(status["applied_migrations"]) == 1
            assert len(status["pending_migrations"]) == 1
            assert status["total_migrations"] == 2

            # Check applied migration details
            applied = status["applied_migrations"][0]
            assert applied["version"] == "20250129_140001"
            assert "applied_at" in applied

            # Check pending migration details
            pending = status["pending_migrations"][0]
            assert pending["version"] == "20250129_140002"

        finally:
            manager.migrations_dir = original_dir

    async def test_migration_error_handling(
        self, migration_manager_clean, temp_directory
    ):
        """Test migration error handling"""
        manager = migration_manager_clean
        await manager.initialize()

        # Create migration with syntax error
        bad_migration = """
async def up(conn):
    await conn.execute("CREATE TABLE bad_syntax_table ()")
    # This will cause a syntax error
    await conn.execute("INVALID SQL STATEMENT")

async def down(conn):
    await conn.execute("DROP TABLE IF EXISTS bad_syntax_table")
"""

        migration_file = os.path.join(
            temp_directory, "20250129_140001_bad_migration.py"
        )
        with open(migration_file, "w") as f:
            f.write(bad_migration)

        migration_info = {
            "filepath": migration_file,
            "version": "20250129_140001",
            "description": "bad_migration",
            "filename": "20250129_140001_bad_migration.py",
        }

        # Attempt to apply bad migration
        result = await manager.apply_migration(migration_info)

        assert result["success"] is False
        assert "error" in result

        # Verify migration was not recorded as applied
        applied = await manager.get_applied_migrations()
        assert len(applied) == 0

    async def test_migration_dependency_validation(self, migration_manager_clean):
        """Test migration dependency validation"""
        manager = migration_manager_clean
        await manager.initialize()

        # Try to rollback non-existent migration
        result = await manager.rollback_migration("20250129_999999", "/fake/path.py")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    async def test_concurrent_migration_safety(
        self, migration_manager_clean, temp_directory
    ):
        """Test that concurrent migrations are handled safely"""
        import asyncio

        manager = migration_manager_clean
        await manager.initialize()

        # Create migration file
        migration_content = """
async def up(conn):
    await conn.execute("CREATE TABLE concurrent_test (id SERIAL PRIMARY KEY)")

async def down(conn):
    await conn.execute("DROP TABLE IF EXISTS concurrent_test")
"""

        migration_file = os.path.join(temp_directory, "20250129_140001_concurrent.py")
        with open(migration_file, "w") as f:
            f.write(migration_content)

        migration_info = {
            "filepath": migration_file,
            "version": "20250129_140001",
            "description": "concurrent",
            "filename": "20250129_140001_concurrent.py",
        }

        # Try to apply same migration concurrently
        tasks = [
            manager.apply_migration(migration_info),
            manager.apply_migration(migration_info),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # One should succeed, one should fail or be skipped
        successful_results = [
            r
            for r in results
            if not isinstance(r, Exception) and r.get("success", False)
        ]
        assert len(successful_results) == 1

        # Verify migration was applied only once
        applied = await manager.get_applied_migrations()
        assert len(applied) == 1
