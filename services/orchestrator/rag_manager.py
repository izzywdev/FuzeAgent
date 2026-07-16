"""
RAG (Retrieval-Augmented Generation) Manager for FuzeAgent

This module provides comprehensive conversation management, vector storage,
and semantic search capabilities for agent chat history and knowledge base.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import numpy as np
import tiktoken

# LangChain imports for conversation summarization
from langchain.memory import ConversationSummaryBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class RAGManager:
    """
    Comprehensive RAG manager for agent conversations and knowledge base
    """

    def __init__(self, database_url: str, anthropic_api_key: str):
        self.database_url = database_url
        self.anthropic_api_key = anthropic_api_key

        # Initialize embedding model
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2

        # Initialize tokenizer for token counting
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # LangChain components for summarization
        self.llm = ChatAnthropic(
            anthropic_api_key=anthropic_api_key,
            model="claude-3-haiku-20240307",  # Fast model for summarization
            temperature=0.3,
        )

        # Conversation memory with token limit
        self.max_tokens = 4000  # Max tokens before summarization
        self.summary_buffer_memory = ConversationSummaryBufferMemory(
            llm=self.llm, max_token_limit=self.max_tokens, return_messages=True
        )

        self.pool = None

    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            self.database_url, min_size=2, max_size=10, command_timeout=60
        )
        logger.info("RAG Manager initialized with database connection pool")

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using sentence transformers"""
        try:
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * self.embedding_dim

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return len(text.split())  # Fallback to word count

    async def create_chat_session(
        self,
        agent_id: str,
        session_name: Optional[str] = None,
        session_type: str = "conversation",
        participants: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new chat session"""

        session_id = str(uuid.uuid4())

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_sessions (
                    id, agent_id, session_name, session_type, 
                    participants, context, started_at, last_activity
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                session_id,
                agent_id,
                session_name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                session_type,
                json.dumps(participants or []),
                json.dumps(context or {}),
                datetime.now(),
                datetime.now(),
            )

        logger.info(f"Created chat session {session_id} for agent {agent_id}")
        return session_id

    async def store_conversation_message(
        self,
        agent_id: str,
        session_id: str,
        message_type: str,  # 'user', 'agent', 'system', 'tool'
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_message_id: Optional[str] = None,
    ) -> str:
        """Store a conversation message with vector embedding"""

        message_id = str(uuid.uuid4())
        embedding = self.generate_embedding(content)

        async with self.pool.acquire() as conn:
            # Store the message
            await conn.execute(
                """
                INSERT INTO agent_conversations (
                    id, agent_id, session_id, message_type, content, 
                    embedding, metadata, parent_message_id, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                message_id,
                agent_id,
                session_id,
                message_type,
                content,
                embedding,
                json.dumps(metadata or {}),
                parent_message_id,
                datetime.now(),
            )

            # Update session message count and last activity
            await conn.execute(
                """
                UPDATE chat_sessions 
                SET message_count = message_count + 1,
                    total_tokens = total_tokens + $1,
                    last_activity = $2
                WHERE id = $3
            """,
                self.count_tokens(content),
                datetime.now(),
                session_id,
            )

        # Check if summarization is needed
        await self._check_and_summarize_session(session_id, agent_id)

        logger.debug(f"Stored message {message_id} in session {session_id}")
        return message_id

    async def _check_and_summarize_session(self, session_id: str, agent_id: str):
        """Check if session needs summarization and create summary if needed"""

        async with self.pool.acquire() as conn:
            # Get session token count
            session_info = await conn.fetchrow(
                """
                SELECT total_tokens, message_count 
                FROM chat_sessions 
                WHERE id = $1
            """,
                session_id,
            )

            if not session_info or session_info["total_tokens"] < self.max_tokens:
                return

            # Check if we already have a recent summary
            recent_summary = await conn.fetchval(
                """
                SELECT id FROM conversation_summaries 
                WHERE session_id = $1 
                ORDER BY created_at DESC 
                LIMIT 1
            """,
                session_id,
            )

            if recent_summary:
                # Get message count since last summary
                last_summary_time = await conn.fetchval(
                    """
                    SELECT created_at FROM conversation_summaries 
                    WHERE id = $1
                """,
                    recent_summary,
                )

                new_messages_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM agent_conversations 
                    WHERE session_id = $1 AND created_at > $2
                """,
                    session_id,
                    last_summary_time,
                )

                # Only summarize if there are enough new messages
                if new_messages_count < 10:
                    return

            # Create summary
            await self._create_conversation_summary(session_id, agent_id)

    async def _create_conversation_summary(self, session_id: str, agent_id: str):
        """Create a conversation summary using LangChain"""

        async with self.pool.acquire() as conn:
            # Get recent messages that haven't been summarized
            last_summary_time = await conn.fetchval(
                """
                SELECT MAX(created_at) FROM conversation_summaries 
                WHERE session_id = $1
            """,
                session_id,
            )

            if last_summary_time:
                messages = await conn.fetch(
                    """
                    SELECT message_type, content, created_at 
                    FROM agent_conversations 
                    WHERE session_id = $1 AND created_at > $2
                    ORDER BY created_at ASC
                """,
                    session_id,
                    last_summary_time,
                )
            else:
                # Get all messages if no previous summary
                messages = await conn.fetch(
                    """
                    SELECT message_type, content, created_at 
                    FROM agent_conversations 
                    WHERE session_id = $1
                    ORDER BY created_at ASC
                    LIMIT 50  -- Limit to prevent overwhelming the summarizer
                """,
                    session_id,
                )

            if len(messages) < 3:  # Not enough messages to summarize
                return

            # Convert to LangChain message format
            langchain_messages = []
            for msg in messages:
                if msg["message_type"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["message_type"] == "agent":
                    langchain_messages.append(AIMessage(content=msg["content"]))
                elif msg["message_type"] == "system":
                    langchain_messages.append(SystemMessage(content=msg["content"]))

            # Create summary using LangChain
            try:
                # Use LangChain's summarization capability
                summary_prompt = PromptTemplate(
                    template="""
                    Summarize the following conversation between a user and an AI agent. 
                    Focus on key decisions, important information, and action items.
                    Keep the summary concise but comprehensive.
                    
                    Conversation:
                    {conversation}
                    
                    Summary:
                    """,
                    input_variables=["conversation"],
                )

                # Format conversation for summarization
                conversation_text = ""
                for msg in langchain_messages:
                    role = "User" if isinstance(msg, HumanMessage) else "Agent"
                    conversation_text += f"{role}: {msg.content}\n\n"

                # Generate summary
                formatted_prompt = summary_prompt.format(conversation=conversation_text)
                summary_response = await self.llm.ainvoke(
                    [HumanMessage(content=formatted_prompt)]
                )
                summary_text = summary_response.content

                # Generate embedding for summary
                summary_embedding = self.generate_embedding(summary_text)

                # Store summary in database
                summary_id = str(uuid.uuid4())
                time_range = (
                    f"[{messages[0]['created_at']}, {messages[-1]['created_at']}]"
                )

                await conn.execute(
                    """
                    INSERT INTO conversation_summaries (
                        id, agent_id, session_id, summary_text, summary_embedding,
                        message_count, token_count, time_range, summary_type, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    summary_id,
                    agent_id,
                    session_id,
                    summary_text,
                    summary_embedding,
                    len(messages),
                    self.count_tokens(summary_text),
                    time_range,
                    "auto",
                    datetime.now(),
                )

                logger.info(
                    f"Created conversation summary {summary_id} for session {session_id}"
                )

            except Exception as e:
                logger.error(f"Error creating conversation summary: {e}")

    async def search_conversation_history(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        session_id: Optional[str] = None,
        include_summaries: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search conversation history using semantic similarity"""

        query_embedding = self.generate_embedding(query)

        async with self.pool.acquire() as conn:
            # Search conversation messages
            where_clause = "WHERE agent_id = $2"
            params = [query_embedding, agent_id]

            if session_id:
                where_clause += " AND session_id = $3"
                params.append(session_id)
                param_offset = 4
            else:
                param_offset = 3

            messages = await conn.fetch(
                f"""
                SELECT 
                    id, session_id, message_type, content, metadata, created_at,
                    1 - (embedding <=> $1) as similarity
                FROM agent_conversations 
                {where_clause}
                AND 1 - (embedding <=> $1) > ${param_offset}
                ORDER BY similarity DESC
                LIMIT ${param_offset + 1}
            """,
                *params,
                similarity_threshold,
                limit,
            )

            results = []
            for msg in messages:
                results.append(
                    {
                        "type": "message",
                        "id": str(msg["id"]),
                        "session_id": str(msg["session_id"]),
                        "message_type": msg["message_type"],
                        "content": msg["content"],
                        "metadata": msg["metadata"],
                        "created_at": msg["created_at"],
                        "similarity": float(msg["similarity"]),
                    }
                )

            # Search conversation summaries if requested
            if include_summaries:
                summaries = await conn.fetch(
                    f"""
                    SELECT 
                        id, session_id, summary_text, message_count, time_range, created_at,
                        1 - (summary_embedding <=> $1) as similarity
                    FROM conversation_summaries 
                    {where_clause}
                    AND 1 - (summary_embedding <=> $1) > ${param_offset}
                    ORDER BY similarity DESC
                    LIMIT ${param_offset + 1}
                """,
                    *params,
                    similarity_threshold,
                    limit // 2,
                )

                for summary in summaries:
                    results.append(
                        {
                            "type": "summary",
                            "id": str(summary["id"]),
                            "session_id": str(summary["session_id"]),
                            "content": summary["summary_text"],
                            "message_count": summary["message_count"],
                            "time_range": summary["time_range"],
                            "created_at": summary["created_at"],
                            "similarity": float(summary["similarity"]),
                        }
                    )

            # Sort by similarity and return top results
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]

    async def add_to_knowledge_base(
        self,
        agent_id: str,
        content: str,
        content_type: str = "text",
        source_type: str = "manual",
        source_reference: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Add content to agent's knowledge base"""

        knowledge_id = str(uuid.uuid4())
        embedding = self.generate_embedding(content)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO agent_knowledge_base (
                    id, agent_id, content, content_type, source_type, 
                    source_reference, embedding, metadata, tags, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                knowledge_id,
                agent_id,
                content,
                content_type,
                source_type,
                source_reference,
                embedding,
                json.dumps(metadata or {}),
                tags or [],
                datetime.now(),
            )

        logger.info(f"Added knowledge item {knowledge_id} to agent {agent_id}")
        return knowledge_id

    async def search_knowledge_base(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        content_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search agent's knowledge base using semantic similarity"""

        query_embedding = self.generate_embedding(query)

        async with self.pool.acquire() as conn:
            where_conditions = ["agent_id = $2", "1 - (embedding <=> $1) > $3"]
            params = [query_embedding, agent_id, similarity_threshold]
            param_count = 4

            if content_types:
                where_conditions.append(f"content_type = ANY(${param_count})")
                params.append(content_types)
                param_count += 1

            if tags:
                where_conditions.append(f"tags && ${param_count}")
                params.append(tags)
                param_count += 1

            where_clause = "WHERE " + " AND ".join(where_conditions)

            results = await conn.fetch(
                f"""
                SELECT 
                    id, content, content_type, source_type, metadata, tags, 
                    access_count, created_at,
                    1 - (embedding <=> $1) as similarity
                FROM agent_knowledge_base 
                {where_clause}
                ORDER BY similarity DESC
                LIMIT ${param_count}
            """,
                *params,
                limit,
            )

            # Update access count for retrieved items
            if results:
                result_ids = [str(r["id"]) for r in results]
                await conn.execute(
                    """
                    UPDATE agent_knowledge_base 
                    SET access_count = access_count + 1, last_accessed = $1
                    WHERE id = ANY($2)
                """,
                    datetime.now(),
                    result_ids,
                )

            return [
                {
                    "id": str(r["id"]),
                    "content": r["content"],
                    "content_type": r["content_type"],
                    "source_type": r["source_type"],
                    "metadata": r["metadata"],
                    "tags": r["tags"],
                    "access_count": r["access_count"],
                    "created_at": r["created_at"],
                    "similarity": float(r["similarity"]),
                }
                for r in results
            ]

    async def get_conversation_context(
        self, agent_id: str, session_id: str, context_window: int = 20
    ) -> Dict[str, Any]:
        """Get recent conversation context for an agent session"""

        async with self.pool.acquire() as conn:
            # Get session info
            session_info = await conn.fetchrow(
                """
                SELECT session_name, session_type, participants, context, 
                       message_count, total_tokens, started_at, last_activity
                FROM chat_sessions 
                WHERE id = $1 AND agent_id = $2
            """,
                session_id,
                agent_id,
            )

            if not session_info:
                return {"error": "Session not found"}

            # Get recent messages
            recent_messages = await conn.fetch(
                """
                SELECT message_type, content, metadata, created_at
                FROM agent_conversations 
                WHERE session_id = $1 AND agent_id = $2
                ORDER BY created_at DESC
                LIMIT $3
            """,
                session_id,
                agent_id,
                context_window,
            )

            # Get latest summary if available
            latest_summary = await conn.fetchrow(
                """
                SELECT summary_text, message_count, time_range, created_at
                FROM conversation_summaries 
                WHERE session_id = $1 AND agent_id = $2
                ORDER BY created_at DESC
                LIMIT 1
            """,
                session_id,
                agent_id,
            )

            return {
                "session_info": dict(session_info),
                "recent_messages": [dict(msg) for msg in reversed(recent_messages)],
                "latest_summary": dict(latest_summary) if latest_summary else None,
                "context_window_size": len(recent_messages),
            }

    async def cleanup_old_data(self, retention_days: int = 90):
        """Clean up old conversation data based on retention policy"""

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        async with self.pool.acquire() as conn:
            # Archive old sessions
            archived_sessions = await conn.fetch(
                """
                UPDATE chat_sessions 
                SET status = 'archived'
                WHERE last_activity < $1 AND status != 'archived'
                RETURNING id
            """,
                cutoff_date,
            )

            # Delete very old conversations (keep summaries)
            deleted_conversations = await conn.fetchval(
                """
                DELETE FROM agent_conversations 
                WHERE created_at < $1
                RETURNING COUNT(*)
            """,
                cutoff_date,
            )

            logger.info(
                f"Archived {len(archived_sessions)} sessions and deleted {deleted_conversations} old conversations"
            )

            return {
                "archived_sessions": len(archived_sessions),
                "deleted_conversations": deleted_conversations,
            }
