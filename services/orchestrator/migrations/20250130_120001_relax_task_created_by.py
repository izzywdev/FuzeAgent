"""
Migration: Relax tasks.created_by to a free-form creator identifier
Created: 2025-01-30T12:00:01
Description: The initial schema modeled tasks.created_by as UUID REFERENCES agents(id),
but the task API (TaskCreate.created_by: Optional[str]) treats it as a free-form
creator identifier such as a user id or "system". Convert the column to a nullable
VARCHAR and drop the agents foreign key so non-agent creators are accepted.
"""


async def upgrade(conn):
    """Apply the migration"""

    # Drop the agents FK (auto-named tasks_created_by_fkey in the initial schema).
    await conn.execute(
        "ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_created_by_fkey;"
    )

    # Widen the column from UUID to a free-form string identifier.
    await conn.execute(
        "ALTER TABLE tasks "
        "ALTER COLUMN created_by TYPE VARCHAR(255) USING created_by::text;"
    )

    print("✅ Relaxed tasks.created_by to VARCHAR(255) (dropped agents FK)")


async def downgrade(conn):
    """Rollback the migration"""

    # Restore the UUID column type and the agents foreign key.
    await conn.execute(
        "ALTER TABLE tasks "
        "ALTER COLUMN created_by TYPE UUID USING NULLIF(created_by, '')::uuid;"
    )
    await conn.execute(
        "ALTER TABLE tasks ADD CONSTRAINT tasks_created_by_fkey "
        "FOREIGN KEY (created_by) REFERENCES agents(id);"
    )

    print("✅ Restored tasks.created_by to UUID REFERENCES agents(id)")
