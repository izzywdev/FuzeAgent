"""
Migration: Add app_build_sessions
Created: 2026-10-04T12:00:01
Description: Durable record for FuzeFront "build your application" sessions
(services/orchestrator/app_builds). One row per FuzeFront buildSessionId; the full record,
including the transactional status-callback outbox that survives pod restarts, lives in
``data`` (jsonb). ``status`` / ``has_pending_outbox`` are denormalised for the resume queries.
"""


async def upgrade(conn):
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS app_build_sessions (
            build_session_id   TEXT PRIMARY KEY,
            agent_session_ref  TEXT NOT NULL UNIQUE,
            status             TEXT NOT NULL,
            has_pending_outbox BOOLEAN NOT NULL DEFAULT FALSE,
            data               JSONB NOT NULL,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_app_build_sessions_status ON app_build_sessions(status);"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_app_build_sessions_pending_outbox "
        "ON app_build_sessions(created_at) WHERE has_pending_outbox;"
    )


async def downgrade(conn):
    await conn.execute("DROP TABLE IF EXISTS app_build_sessions;")
