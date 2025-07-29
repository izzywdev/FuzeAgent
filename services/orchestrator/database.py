import asyncpg
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/ai_context")

@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database connection with automatic cleanup"""
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
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
    
    @staticmethod
    async def insert_agent(name: str, role: str, type: str, config: dict) -> str:
        """Insert a new agent"""
        async with get_db_connection() as conn:
            agent_id = await conn.fetchval(
                """
                INSERT INTO agents (name, role, type, status, config)
                VALUES ($1, $2, $3, 'active', $4)
                RETURNING id
                """,
                name, role, type, config
            )
            return str(agent_id)
    
    @staticmethod
    async def get_agents():
        """Get all agents"""
        async with get_db_connection() as conn:
            rows = await conn.fetch("SELECT * FROM agents ORDER BY created_at DESC")
            return [dict(row) for row in rows]
    
    @staticmethod
    async def update_agent_status(agent_id: str, status: str):
        """Update agent status"""
        async with get_db_connection() as conn:
            await conn.execute(
                "UPDATE agents SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                status, agent_id
            )
    
    @staticmethod 
    async def insert_task(title: str, description: str, assigned_to: str = None, created_by: str = None) -> str:
        """Insert a new task"""
        async with get_db_connection() as conn:
            task_id = await conn.fetchval(
                """
                INSERT INTO tasks (title, description, assigned_to, created_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                title, description, assigned_to, created_by
            )
            return str(task_id)
    
    @staticmethod
    async def get_tasks():
        """Get all tasks"""
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT t.*, a.name as assigned_agent_name
                FROM tasks t
                LEFT JOIN agents a ON t.assigned_to = a.id
                ORDER BY t.created_at DESC
                """
            )
            return [dict(row) for row in rows]
    
    @staticmethod
    async def update_task_status(task_id: str, status: str, result: dict = None):
        """Update task status and result"""
        async with get_db_connection() as conn:
            if status == 'completed':
                await conn.execute(
                    """
                    UPDATE tasks 
                    SET status = $1, result = $2, completed_at = CURRENT_TIMESTAMP 
                    WHERE id = $3
                    """,
                    status, result, task_id
                )
            else:
                await conn.execute(
                    "UPDATE tasks SET status = $1 WHERE id = $2",
                    status, task_id
                )