import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@postgres:5432/ai_context"
)


async def _register_connection_codecs(conn: asyncpg.Connection) -> None:
    """Register codecs so DB values round-trip as the API layer expects.

    * ``json``/``jsonb``: asyncpg does not encode Python ``dict``/``list`` objects
      into these columns automatically (it expects a pre-serialized ``str``) and
      returns the raw JSON text on read. These codecs let the DatabaseManager pass
      native dicts to INSERT/UPDATE and get native dicts back from SELECT.
    * ``uuid``: asyncpg decodes UUID columns to ``uuid.UUID`` objects, but the API
      response models (Organization/Team/Agent ``id``, ``organization_id``,
      ``team_id`` …) are typed as ``str``. Decoding/encoding as ``str`` keeps the
      whole layer string-based and accepts the string ids the endpoints pass in.
    """
    for type_name in ("json", "jsonb"):
        await conn.set_type_codec(
            type_name,
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
    await conn.set_type_codec(
        "uuid",
        encoder=str,
        decoder=str,
        schema="pg_catalog",
    )


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database connection with automatic cleanup"""
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await _register_connection_codecs(conn)
        yield conn
    finally:
        if conn:
            await conn.close()


class DatabaseManager:
    """Database operations manager"""

    @staticmethod
    async def create_tables():
        """Create database tables if they don't exist"""
        async with get_db_connection() as conn:
            # Tables are created via init_db.sql in Docker
            await conn.execute("SELECT 1")  # Simple connectivity test

    # Organization Operations
    @staticmethod
    async def create_organization(
        name: str, description: str = None, settings: dict = None
    ) -> str:
        """Create a new organization"""
        async with get_db_connection() as conn:
            org_id = await conn.fetchval(
                """
                INSERT INTO organizations (name, description, settings)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                name,
                description,
                settings or {},
            )
            return str(org_id)

    @staticmethod
    async def get_organizations() -> List[Dict[str, Any]]:
        """Get all organizations with team and agent counts"""
        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT 
                    o.*,
                    COUNT(DISTINCT t.id) as team_count,
                    COUNT(DISTINCT a.id) as agent_count
                FROM organizations o
                LEFT JOIN teams t ON o.id = t.organization_id
                LEFT JOIN agents a ON t.id = a.team_id
                GROUP BY o.id
                ORDER BY o.created_at DESC
                """)
            return [dict(row) for row in rows]

    @staticmethod
    async def get_organization(org_id: str) -> Optional[Dict[str, Any]]:
        """Get organization by ID"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    o.*,
                    COUNT(DISTINCT t.id) as team_count,
                    COUNT(DISTINCT a.id) as agent_count
                FROM organizations o
                LEFT JOIN teams t ON o.id = t.organization_id
                LEFT JOIN agents a ON t.id = a.team_id
                WHERE o.id = $1
                GROUP BY o.id
                """,
                org_id,
            )
            return dict(row) if row else None

    @staticmethod
    async def update_organization(org_id: str, **kwargs) -> bool:
        """Update organization"""
        # Strict allowlist of columns that may be updated. Column identifiers
        # cannot be bound as query params, so validate them against this fixed
        # set (fail-fast, before opening a connection) to prevent SQL injection
        # via **kwargs keys.
        allowed_columns = {"name", "description", "settings"}
        updates = {k: v for k, v in kwargs.items() if v is not None}
        invalid = set(updates) - allowed_columns
        if invalid:
            raise ValueError(
                f"Invalid column(s) for organizations update: {sorted(invalid)}"
            )

        async with get_db_connection() as conn:
            set_clauses = []
            params = []
            param_count = 1

            for key, value in updates.items():
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)
                param_count += 1

            if not set_clauses:
                return False

            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            params.append(org_id)

            query = f"""
                UPDATE organizations
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count + 1}
            """  # nosec B608 -- SET columns validated against a fixed allowlist above; all values bound as $N params

            result = await conn.execute(query, *params)
            return result != "UPDATE 0"

    @staticmethod
    async def delete_organization(org_id: str) -> bool:
        """Delete organization (cascades to teams and agents)"""
        async with get_db_connection() as conn:
            result = await conn.execute(
                "DELETE FROM organizations WHERE id = $1", org_id
            )
            return result != "DELETE 0"

    # Team Operations
    @staticmethod
    async def create_team(
        organization_id: str,
        name: str,
        description: str = None,
        team_type: str = "general",
        settings: dict = None,
    ) -> str:
        """Create a new team"""
        async with get_db_connection() as conn:
            team_id = await conn.fetchval(
                """
                INSERT INTO teams (organization_id, name, description, team_type, settings)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                organization_id,
                name,
                description,
                team_type,
                settings or {},
            )
            return str(team_id)

    @staticmethod
    async def get_teams(organization_id: str = None) -> List[Dict[str, Any]]:
        """Get teams, optionally filtered by organization"""
        async with get_db_connection() as conn:
            if organization_id:
                rows = await conn.fetch(
                    """
                    SELECT 
                        t.*,
                        o.name as organization_name,
                        COUNT(a.id) as agent_count
                    FROM teams t
                    JOIN organizations o ON t.organization_id = o.id
                    LEFT JOIN agents a ON t.id = a.team_id
                    WHERE t.organization_id = $1
                    GROUP BY t.id, o.name
                    ORDER BY t.created_at DESC
                    """,
                    organization_id,
                )
            else:
                rows = await conn.fetch("""
                    SELECT 
                        t.*,
                        o.name as organization_name,
                        COUNT(a.id) as agent_count
                    FROM teams t
                    JOIN organizations o ON t.organization_id = o.id
                    LEFT JOIN agents a ON t.id = a.team_id
                    GROUP BY t.id, o.name
                    ORDER BY t.created_at DESC
                    """)
            return [dict(row) for row in rows]

    @staticmethod
    async def get_team(team_id: str) -> Optional[Dict[str, Any]]:
        """Get team by ID"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    t.*,
                    o.name as organization_name,
                    COUNT(a.id) as agent_count
                FROM teams t
                JOIN organizations o ON t.organization_id = o.id
                LEFT JOIN agents a ON t.id = a.team_id
                WHERE t.id = $1
                GROUP BY t.id, o.name
                """,
                team_id,
            )
            return dict(row) if row else None

    @staticmethod
    async def update_team(team_id: str, **kwargs) -> bool:
        """Update team"""
        # Strict allowlist of columns that may be updated. Column identifiers
        # cannot be bound as query params, so validate them against this fixed
        # set (fail-fast, before opening a connection) to prevent SQL injection
        # via **kwargs keys.
        allowed_columns = {
            "organization_id",
            "name",
            "description",
            "team_type",
            "settings",
        }
        updates = {k: v for k, v in kwargs.items() if v is not None}
        invalid = set(updates) - allowed_columns
        if invalid:
            raise ValueError(f"Invalid column(s) for teams update: {sorted(invalid)}")

        async with get_db_connection() as conn:
            set_clauses = []
            params = []
            param_count = 1

            for key, value in updates.items():
                set_clauses.append(f"{key} = ${param_count}")
                params.append(value)
                param_count += 1

            if not set_clauses:
                return False

            set_clauses.append(f"updated_at = ${param_count}")
            params.append(datetime.utcnow())
            params.append(team_id)

            query = f"""
                UPDATE teams
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count + 1}
            """  # nosec B608 -- SET columns validated against a fixed allowlist above; all values bound as $N params

            result = await conn.execute(query, *params)
            return result != "UPDATE 0"

    @staticmethod
    async def delete_team(team_id: str) -> bool:
        """Delete team (cascades to agents)"""
        async with get_db_connection() as conn:
            result = await conn.execute("DELETE FROM teams WHERE id = $1", team_id)
            return result != "DELETE 0"

    @staticmethod
    async def insert_agent(
        team_id: str,
        name: str,
        role: str,
        type: str,
        config: dict,
        template_id: str = None,
    ) -> str:
        """Insert a new agent"""
        async with get_db_connection() as conn:
            agent_id = await conn.fetchval(
                """
                INSERT INTO agents (team_id, name, role, type, status, config, template_id)
                VALUES ($1, $2, $3, $4, 'active', $5, $6)
                RETURNING id
                """,
                team_id,
                name,
                role,
                type,
                config,
                template_id,
            )
            return str(agent_id)

    @staticmethod
    async def get_agents(team_id: str = None):
        """Get all agents, optionally filtered by team"""
        async with get_db_connection() as conn:
            if team_id:
                rows = await conn.fetch(
                    """
                    SELECT 
                        a.*,
                        t.name as team_name,
                        t.organization_id,
                        o.name as organization_name
                    FROM agents a
                    JOIN teams t ON a.team_id = t.id
                    JOIN organizations o ON t.organization_id = o.id
                    WHERE a.team_id = $1
                    ORDER BY a.created_at DESC
                    """,
                    team_id,
                )
            else:
                rows = await conn.fetch("""
                    SELECT 
                        a.*,
                        t.name as team_name,
                        t.organization_id,
                        o.name as organization_name
                    FROM agents a
                    JOIN teams t ON a.team_id = t.id
                    JOIN organizations o ON t.organization_id = o.id
                    ORDER BY a.created_at DESC
                    """)
            return [dict(row) for row in rows]

    @staticmethod
    async def get_agent(agent_id: str):
        """Get agent by ID with team and organization info"""
        async with get_db_connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    a.*,
                    t.name as team_name,
                    t.organization_id,
                    o.name as organization_name
                FROM agents a
                JOIN teams t ON a.team_id = t.id
                JOIN organizations o ON t.organization_id = o.id
                WHERE a.id = $1
                """,
                agent_id,
            )
            return dict(row) if row else None

    @staticmethod
    async def update_agent_status(agent_id: str, status: str):
        """Update agent status"""
        async with get_db_connection() as conn:
            await conn.execute(
                "UPDATE agents SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                status,
                agent_id,
            )

    @staticmethod
    async def insert_task(
        title: str, description: str, assigned_to: str = None, created_by: str = None
    ) -> str:
        """Insert a new task"""
        async with get_db_connection() as conn:
            task_id = await conn.fetchval(
                """
                INSERT INTO tasks (title, description, assigned_to, created_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                title,
                description,
                assigned_to,
                created_by,
            )
            return str(task_id)

    @staticmethod
    async def get_tasks():
        """Get all tasks"""
        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT t.*, a.name as assigned_agent_name
                FROM tasks t
                LEFT JOIN agents a ON t.assigned_to = a.id
                ORDER BY t.created_at DESC
                """)
            return [dict(row) for row in rows]

    @staticmethod
    async def update_task_status(task_id: str, status: str, result: dict = None):
        """Update task status and result"""
        async with get_db_connection() as conn:
            if status == "completed":
                await conn.execute(
                    """
                    UPDATE tasks 
                    SET status = $1, result = $2, completed_at = CURRENT_TIMESTAMP 
                    WHERE id = $3
                    """,
                    status,
                    result,
                    task_id,
                )
            else:
                await conn.execute(
                    "UPDATE tasks SET status = $1 WHERE id = $2", status, task_id
                )
