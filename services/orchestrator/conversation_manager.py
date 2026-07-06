"""
Conversation Manager for FuzeAgent Claude Code Integration

Manages and stores complete conversations between agents and Claude Code,
providing comprehensive audit trails, debugging capabilities, and learning data.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .database import get_db_connection

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    USER_PROMPT = "user_prompt"
    CLAUDE_RESPONSE = "claude_response"
    SYSTEM_MESSAGE = "system_message"
    ERROR_MESSAGE = "error_message"
    CODE_EXECUTION = "code_execution"
    TEST_RESULT = "test_result"


class InteractionType(str, Enum):
    QUESTION = "question"
    CLARIFICATION = "clarification"
    APPROVAL_REQUEST = "approval_request"
    ERROR_REPORT = "error_report"
    PROGRESS_UPDATE = "progress_update"


@dataclass
class ConversationMessage:
    """Represents a single message in a Claude Code conversation"""

    task_id: str
    iteration_number: int
    message_type: MessageType
    content: str
    token_count: Optional[int] = None
    model_used: Optional[str] = None
    temperature: Optional[float] = None
    response_time_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConversationSession:
    """Represents a complete conversation session"""

    agent_id: str
    task_id: str
    sandbox_id: str
    session_started_at: datetime
    session_ended_at: Optional[datetime] = None
    total_messages: int = 0
    total_tokens: int = 0
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None


class ConversationManager:
    """
    Manages Claude Code conversations and provides comprehensive tracking.

    Features:
    - Full conversation storage and retrieval
    - Token usage tracking and cost analysis
    - Human interaction management
    - Code generation tracking
    - Performance metrics collection
    """

    def __init__(self):
        self.active_sessions: Dict[str, ConversationSession] = {}

    async def start_conversation_session(
        self,
        agent_id: str,
        task_id: str,
        sandbox_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a new conversation session for an agent"""

        session = ConversationSession(
            agent_id=agent_id,
            task_id=task_id,
            sandbox_id=sandbox_id,
            session_started_at=datetime.now(),
            metadata=metadata or {},
        )

        # Store session in database
        session_id = await self._store_conversation_session(session)
        session.metadata = session.metadata or {}
        session.metadata["session_id"] = session_id

        # Track active session
        self.active_sessions[session_id] = session

        logger.info(
            f"Started conversation session {session_id} for agent {agent_id}, task {task_id}"
        )
        return session_id

    async def end_conversation_session(self, session_id: str) -> bool:
        """End a conversation session"""

        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found in active sessions")
            return False

        session.session_ended_at = datetime.now()
        session.status = "completed"

        # Update database
        await self._update_conversation_session(session_id, session)

        # Remove from active sessions
        del self.active_sessions[session_id]

        logger.info(f"Ended conversation session {session_id}")
        return True

    async def store_message(
        self,
        session_id: str,
        message: ConversationMessage,
        start_time: Optional[float] = None,
    ) -> str:
        """Store a conversation message"""

        # Calculate response time if start_time provided
        if start_time and message.message_type == MessageType.CLAUDE_RESPONSE:
            message.response_time_ms = int((time.time() - start_time) * 1000)

        # Store message in database
        message_id = await self._store_claude_conversation(message)

        # Update session statistics
        session = self.active_sessions.get(session_id)
        if session:
            session.total_messages += 1
            if message.token_count:
                session.total_tokens += message.token_count

        logger.debug(f"Stored message {message_id} for session {session_id}")
        return message_id

    async def store_user_prompt(
        self,
        session_id: str,
        task_id: str,
        iteration_number: int,
        prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.3,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a user prompt to Claude"""

        message = ConversationMessage(
            task_id=task_id,
            iteration_number=iteration_number,
            message_type=MessageType.USER_PROMPT,
            content=prompt,
            model_used=model,
            temperature=temperature,
            metadata=metadata or {},
        )

        return await self.store_message(session_id, message)

    async def store_claude_response(
        self,
        session_id: str,
        task_id: str,
        iteration_number: int,
        response: str,
        token_count: Optional[int] = None,
        model: str = "claude-3-5-sonnet-20241022",
        start_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store Claude's response"""

        message = ConversationMessage(
            task_id=task_id,
            iteration_number=iteration_number,
            message_type=MessageType.CLAUDE_RESPONSE,
            content=response,
            token_count=token_count,
            model_used=model,
            metadata=metadata or {},
        )

        return await self.store_message(session_id, message, start_time)

    async def store_code_generation(
        self,
        task_id: str,
        iteration_number: int,
        file_path: str,
        file_type: str,
        language: str,
        content: str,
        commit_hash: Optional[str] = None,
        test_results: Optional[Dict[str, Any]] = None,
        quality_metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store generated code with metadata"""

        async with get_db_connection() as conn:
            code_id = await conn.fetchval(
                """
                INSERT INTO code_generations (
                    task_id, iteration_number, file_path, file_type, language,
                    content, commit_hash, test_results, quality_metrics
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """,
                task_id,
                iteration_number,
                file_path,
                file_type,
                language,
                content,
                commit_hash,
                json.dumps(test_results) if test_results else None,
                json.dumps(quality_metrics) if quality_metrics else None,
            )

        logger.info(f"Stored code generation {code_id} for task {task_id}")
        return str(code_id)

    async def store_human_interaction(
        self,
        task_id: str,
        iteration_number: int,
        interaction_type: InteractionType,
        agent_message: str,
        human_response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store human-in-the-loop interaction"""

        async with get_db_connection() as conn:
            interaction_id = await conn.fetchval(
                """
                INSERT INTO human_interactions (
                    task_id, iteration_number, interaction_type, 
                    agent_message, human_response, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """,
                task_id,
                iteration_number,
                interaction_type.value,
                agent_message,
                human_response,
                json.dumps(metadata) if metadata else {},
            )

        logger.info(f"Stored human interaction {interaction_id} for task {task_id}")
        return str(interaction_id)

    async def update_human_response(
        self, interaction_id: str, human_response: str
    ) -> bool:
        """Update human response to an interaction"""

        async with get_db_connection() as conn:
            result = await conn.execute(
                """
                UPDATE human_interactions 
                SET human_response = $1, 
                    responded_at = CURRENT_TIMESTAMP,
                    response_time_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - asked_at))
                WHERE id = $2
            """,
                human_response,
                interaction_id,
            )

        success = result != "UPDATE 0"
        if success:
            logger.info(f"Updated human response for interaction {interaction_id}")
        return success

    async def store_performance_metric(
        self,
        agent_id: str,
        task_id: str,
        metric_type: str,
        metric_value: float,
        metric_unit: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store agent performance metric"""

        async with get_db_connection() as conn:
            metric_id = await conn.fetchval(
                """
                INSERT INTO agent_performance_metrics (
                    agent_id, task_id, metric_type, metric_value, 
                    metric_unit, context
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """,
                agent_id,
                task_id,
                metric_type,
                metric_value,
                metric_unit,
                json.dumps(context) if context else {},
            )

        logger.debug(
            f"Stored performance metric {metric_id}: {metric_type}={metric_value}"
        )
        return str(metric_id)

    async def get_conversation_history(
        self,
        task_id: str,
        iteration_number: Optional[int] = None,
        message_types: Optional[List[MessageType]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get conversation history for a task"""

        conditions = ["task_id = $1"]
        params = [task_id]
        param_count = 1

        if iteration_number is not None:
            param_count += 1
            conditions.append(f"iteration_number = ${param_count}")
            params.append(iteration_number)

        if message_types:
            param_count += 1
            conditions.append(f"message_type = ANY(${param_count})")
            params.append([mt.value for mt in message_types])

        where_clause = " AND ".join(conditions)
        limit_clause = f"LIMIT {limit}" if limit else ""

        async with get_db_connection() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM claude_conversations 
                WHERE {where_clause}
                ORDER BY created_at ASC
                {limit_clause}
            """,
                *params,
            )

        return [dict(row) for row in rows]

    async def get_conversation_summary(self, task_id: str) -> Dict[str, Any]:
        """Get conversation summary with statistics"""

        async with get_db_connection() as conn:
            # Get message statistics
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_messages,
                    SUM(token_count) as total_tokens,
                    AVG(response_time_ms) as avg_response_time,
                    MAX(iteration_number) as max_iteration
                FROM claude_conversations 
                WHERE task_id = $1
            """,
                task_id,
            )

            # Get message type breakdown
            type_breakdown = await conn.fetch(
                """
                SELECT message_type, COUNT(*) as count
                FROM claude_conversations 
                WHERE task_id = $1
                GROUP BY message_type
            """,
                task_id,
            )

            # Get human interactions
            human_interactions = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_interactions,
                    COUNT(human_response) as responded_interactions,
                    AVG(response_time_seconds) as avg_response_time
                FROM human_interactions 
                WHERE task_id = $1
            """,
                task_id,
            )

        return {
            "task_id": task_id,
            "total_messages": stats["total_messages"] or 0,
            "total_tokens": stats["total_tokens"] or 0,
            "avg_response_time_ms": float(stats["avg_response_time"] or 0),
            "max_iteration": stats["max_iteration"] or 0,
            "message_types": {
                row["message_type"]: row["count"] for row in type_breakdown
            },
            "human_interactions": {
                "total": human_interactions["total_interactions"] or 0,
                "responded": human_interactions["responded_interactions"] or 0,
                "avg_response_time_seconds": float(
                    human_interactions["avg_response_time"] or 0
                ),
            },
        }

    async def get_code_generations(
        self,
        task_id: str,
        iteration_number: Optional[int] = None,
        file_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get code generations for a task"""

        conditions = ["task_id = $1"]
        params = [task_id]
        param_count = 1

        if iteration_number is not None:
            param_count += 1
            conditions.append(f"iteration_number = ${param_count}")
            params.append(iteration_number)

        if file_type:
            param_count += 1
            conditions.append(f"file_type = ${param_count}")
            params.append(file_type)

        if language:
            param_count += 1
            conditions.append(f"language = ${param_count}")
            params.append(language)

        where_clause = " AND ".join(conditions)

        async with get_db_connection() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM code_generations 
                WHERE {where_clause}
                ORDER BY generated_at ASC
            """,
                *params,
            )

        return [dict(row) for row in rows]

    async def get_agent_performance_metrics(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metric_types: Optional[List[str]] = None,
        time_range_hours: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get agent performance metrics"""

        conditions = []
        params = []
        param_count = 0

        if agent_id:
            param_count += 1
            conditions.append(f"agent_id = ${param_count}")
            params.append(agent_id)

        if task_id:
            param_count += 1
            conditions.append(f"task_id = ${param_count}")
            params.append(task_id)

        if metric_types:
            param_count += 1
            conditions.append(f"metric_type = ANY(${param_count})")
            params.append(metric_types)

        if time_range_hours:
            param_count += 1
            conditions.append(
                f"measured_at >= NOW() - INTERVAL '{time_range_hours} hours'"
            )

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        async with get_db_connection() as conn:
            rows = await conn.fetch(
                f"""
                SELECT * FROM agent_performance_metrics 
                {where_clause}
                ORDER BY measured_at DESC
            """,
                *params,
            )

        return [dict(row) for row in rows]

    # Private methods

    async def _store_conversation_session(self, session: ConversationSession) -> str:
        """Store conversation session in database"""

        async with get_db_connection() as conn:
            session_id = await conn.fetchval(
                """
                INSERT INTO agent_conversation_sessions (
                    agent_id, task_id, sandbox_id, session_started_at, 
                    total_messages, total_tokens, status, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """,
                session.agent_id,
                session.task_id,
                session.sandbox_id,
                session.session_started_at,
                session.total_messages,
                session.total_tokens,
                session.status,
                json.dumps(session.metadata) if session.metadata else {},
            )

        return str(session_id)

    async def _update_conversation_session(
        self, session_id: str, session: ConversationSession
    ):
        """Update conversation session in database"""

        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE agent_conversation_sessions 
                SET session_ended_at = $1, total_messages = $2, 
                    total_tokens = $3, status = $4, metadata = $5
                WHERE id = $6
            """,
                session.session_ended_at,
                session.total_messages,
                session.total_tokens,
                session.status,
                json.dumps(session.metadata) if session.metadata else {},
                session_id,
            )

    async def _store_claude_conversation(self, message: ConversationMessage) -> str:
        """Store Claude conversation message in database"""

        async with get_db_connection() as conn:
            message_id = await conn.fetchval(
                """
                INSERT INTO claude_conversations (
                    task_id, iteration_number, message_type, content,
                    token_count, model_used, temperature, response_time_ms, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """,
                message.task_id,
                message.iteration_number,
                message.message_type.value,
                message.content,
                message.token_count,
                message.model_used,
                message.temperature,
                message.response_time_ms,
                json.dumps(message.metadata) if message.metadata else {},
            )

        return str(message_id)
