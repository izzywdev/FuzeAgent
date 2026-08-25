import asyncio
import json
from typing import Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from .database import get_db_connection


class ContextService:
    def __init__(self):
        # Load sentence transformer for embeddings
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()

    async def store_interaction(
        self, agent_id: str, content: str, metadata: Dict = None
    ) -> str:
        """Store agent interaction with embedding"""
        embedding = self.generate_embedding(content)

        async with get_db_connection() as conn:
            interaction_id = await conn.fetchval(
                """
                INSERT INTO interactions (agent_id, content, embedding, metadata)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                agent_id,
                content,
                embedding,
                metadata or {},
            )
            return str(interaction_id)

    async def get_similar_interactions(
        self,
        query: str,
        agent_id: str = None,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Dict]:
        """Find similar interactions using vector similarity"""
        query_embedding = self.generate_embedding(query)

        async with get_db_connection() as conn:
            if agent_id:
                rows = await conn.fetch(
                    """
                    SELECT id, agent_id, content, metadata, created_at,
                           1 - (embedding <=> $1) as similarity
                    FROM interactions 
                    WHERE agent_id = $2 AND 1 - (embedding <=> $1) > $3
                    ORDER BY similarity DESC
                    LIMIT $4
                    """,
                    query_embedding,
                    agent_id,
                    similarity_threshold,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, agent_id, content, metadata, created_at,
                           1 - (embedding <=> $1) as similarity
                    FROM interactions 
                    WHERE 1 - (embedding <=> $1) > $2
                    ORDER BY similarity DESC
                    LIMIT $3
                    """,
                    query_embedding,
                    similarity_threshold,
                    limit,
                )

        return [dict(row) for row in rows]

    async def get_context(self, query: str, agent_id: str = None) -> Dict:
        """Get relevant context for a query"""
        similar_interactions = await self.get_similar_interactions(query, agent_id)

        # Get recent interactions from same agent
        recent_interactions = []
        if agent_id:
            async with get_db_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT content, metadata, created_at
                    FROM interactions 
                    WHERE agent_id = $1
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    agent_id,
                )
                recent_interactions = [dict(row) for row in rows]

        return {
            "similar_interactions": similar_interactions,
            "recent_interactions": recent_interactions,
            "relevant_code": self._extract_code_snippets(similar_interactions),
            "similar_features": self._extract_similar_features(similar_interactions),
        }

    def _extract_code_snippets(self, interactions: List[Dict]) -> str:
        """Extract code snippets from interactions"""
        code_snippets = []
        for interaction in interactions:
            content = interaction.get("content", "")
            # Simple extraction - look for code blocks
            if "```" in content:
                parts = content.split("```")
                for i in range(1, len(parts), 2):
                    code_snippets.append(parts[i].strip())

        return "\n\n".join(code_snippets[:3])  # Return top 3 snippets

    def _extract_similar_features(self, interactions: List[Dict]) -> str:
        """Extract similar feature descriptions"""
        features = []
        for interaction in interactions:
            metadata = interaction.get("metadata", {})
            if "task_type" in metadata and metadata["task_type"] == "implement_feature":
                features.append(interaction.get("content", ""))

        return "\n\n".join(features[:2])  # Return top 2 similar features

    async def get_agent_memory(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """Get agent's memory/interaction history"""
        async with get_db_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT content, metadata, created_at
                FROM interactions 
                WHERE agent_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                agent_id,
                limit,
            )
            return [dict(row) for row in rows]

    async def search_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """Search across all agent knowledge"""
        return await self.get_similar_interactions(query, limit=limit)
