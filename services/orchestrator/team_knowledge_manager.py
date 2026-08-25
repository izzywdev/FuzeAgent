"""
Team Knowledge Manager for FuzeAgent

This module manages team-level knowledge aggregation, filtering organization knowledge
for team relevance, and facilitating knowledge sharing between agents within teams.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
from sentence_transformers import SentenceTransformer

from .organization_rag_manager import (
    ContentType,
    KnowledgeCategory,
    KnowledgeSearchResult,
    OrganizationRAGManager,
    SourceType,
    VisibilityLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class TeamKnowledge:
    """Represents team-level knowledge"""

    id: str
    team_id: str
    organization_id: str
    title: str
    content: str
    content_type: ContentType
    knowledge_category: KnowledgeCategory
    embedding: Optional[List[float]]
    source_type: SourceType
    contributing_agents: List[str]
    source_knowledge_ids: List[str]
    aggregation_method: str
    team_relevance_score: float
    agent_adoption_rate: float
    effectiveness_score: float
    visibility_level: VisibilityLevel
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime]


@dataclass
class TeamKnowledgeSearchResult:
    """Result of team knowledge search"""

    team_knowledge: TeamKnowledge
    similarity_score: float
    relevance_score: float
    team_fit_score: float
    combined_score: float


class TeamKnowledgeManager:
    """
    Manages team-specific knowledge base with intelligent aggregation
    from organization knowledge and agent contributions.
    """

    def __init__(
        self, database_url: str, organization_rag_manager: OrganizationRAGManager
    ):
        self.database_url = database_url
        self.org_rag_manager = organization_rag_manager
        self.pool: Optional[asyncpg.Pool] = None

        # Initialize embedding model
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embedding_dim = 384

        # Configuration
        self.min_team_relevance = 0.4
        self.adoption_threshold = 0.6  # 60% of team agents should find it useful
        self.effectiveness_decay_days = 30

        # Statistics
        self.team_queries_processed = 0
        self.team_knowledge_created = 0
        self.aggregations_performed = 0

    async def initialize(self):
        """Initialize the team knowledge manager"""
        logger.info("Initializing TeamKnowledgeManager")

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=2, max_size=10, command_timeout=60
            )

            logger.info("TeamKnowledgeManager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize TeamKnowledgeManager: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        logger.info("TeamKnowledgeManager closed")

    async def create_team_knowledge(
        self,
        team_id: str,
        title: str,
        content: str,
        content_type: ContentType = ContentType.TEXT,
        knowledge_category: KnowledgeCategory = KnowledgeCategory.DEVELOPMENT,
        source_type: SourceType = SourceType.TEAM_AGGREGATION,
        contributing_agents: Optional[List[str]] = None,
        source_knowledge_ids: Optional[List[str]] = None,
        aggregation_method: str = "synthesis",
        team_relevance_score: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create team-specific knowledge"""

        team_knowledge_id = str(uuid.uuid4())
        embedding = self._generate_embedding(content)

        async with self.pool.acquire() as conn:
            # Get organization_id for this team
            org_id = await conn.fetchval(
                """
                SELECT organization_id FROM teams WHERE id = $1
            """,
                team_id,
            )

            if not org_id:
                raise ValueError(f"Team {team_id} not found")

            await conn.execute(
                """
                INSERT INTO team_knowledge_base (
                    id, team_id, organization_id, title, content, content_type,
                    knowledge_category, embedding, source_type, contributing_agents,
                    source_knowledge_ids, aggregation_method, team_relevance_score,
                    metadata, tags
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """,
                team_knowledge_id,
                team_id,
                org_id,
                title,
                content,
                content_type.value,
                knowledge_category.value,
                embedding,
                source_type.value,
                contributing_agents or [],
                source_knowledge_ids or [],
                aggregation_method,
                team_relevance_score,
                json.dumps(metadata or {}),
                tags or [],
            )

        self.team_knowledge_created += 1

        logger.info(f"Created team knowledge {team_knowledge_id} for team {team_id}")
        return team_knowledge_id

    async def search_team_knowledge(
        self,
        team_id: str,
        query: str,
        categories: Optional[List[KnowledgeCategory]] = None,
        content_types: Optional[List[ContentType]] = None,
        include_org_knowledge: bool = True,
        limit: int = 10,
        min_similarity: float = 0.3,
    ) -> List[TeamKnowledgeSearchResult]:
        """Search team knowledge with optional organization knowledge inclusion"""

        self.team_queries_processed += 1
        query_embedding = self._generate_embedding(query)
        results = []

        async with self.pool.acquire() as conn:
            # Search team-specific knowledge
            team_results = await self._search_team_specific_knowledge(
                conn,
                team_id,
                query_embedding,
                categories,
                content_types,
                limit,
                min_similarity,
            )
            results.extend(team_results)

            # Search organization knowledge filtered for team relevance
            if include_org_knowledge and len(results) < limit:
                org_results = await self._search_org_knowledge_for_team(
                    conn,
                    team_id,
                    query,
                    categories,
                    content_types,
                    limit - len(results),
                    min_similarity,
                )
                results.extend(org_results)

        # Sort by combined score
        results.sort(key=lambda x: x.combined_score, reverse=True)
        return results[:limit]

    async def aggregate_agent_knowledge_to_team(
        self,
        team_id: str,
        agent_id: str,
        agent_memory_ids: List[str],
        aggregation_method: str = "synthesis",
    ) -> Optional[str]:
        """Aggregate multiple agent memories into team knowledge"""

        async with self.pool.acquire() as conn:
            # Get agent memories
            agent_memories = await conn.fetch(
                """
                SELECT * FROM agent_memory 
                WHERE id = ANY($1) AND agent_id = $2
                ORDER BY confidence_score DESC, created_at DESC
            """,
                agent_memory_ids,
                agent_id,
            )

            if not agent_memories:
                return None

            # Analyze memories for commonalities
            analysis_result = await self._analyze_memories_for_aggregation(
                agent_memories
            )

            if analysis_result["aggregation_value"] < self.min_team_relevance:
                logger.debug(
                    f"Agent memories don't meet team relevance threshold: {analysis_result['aggregation_value']}"
                )
                return None

            # Create aggregated knowledge
            team_knowledge_id = await self.create_team_knowledge(
                team_id=team_id,
                title=analysis_result["title"],
                content=analysis_result["content"],
                content_type=analysis_result["content_type"],
                knowledge_category=analysis_result["category"],
                source_type=SourceType.AGENT_CONTRIBUTION,
                contributing_agents=[agent_id],
                aggregation_method=aggregation_method,
                team_relevance_score=analysis_result["aggregation_value"],
                metadata=analysis_result["metadata"],
                tags=analysis_result["tags"],
            )

            # Mark original memories as aggregated
            await conn.execute(
                """
                UPDATE agent_memory 
                SET propagated_to_team = TRUE, team_context_id = $2
                WHERE id = ANY($1)
            """,
                agent_memory_ids,
                team_knowledge_id,
            )

            self.aggregations_performed += 1

            logger.info(
                f"Aggregated {len(agent_memory_ids)} agent memories into team knowledge {team_knowledge_id}"
            )
            return team_knowledge_id

    async def get_team_knowledge_context(
        self,
        team_id: str,
        task_context: Dict[str, Any],
        agent_id: Optional[str] = None,
        max_context_items: int = 5,
    ) -> Dict[str, Any]:
        """Get relevant team knowledge for task execution context"""

        # Build context query from task information
        context_query = self._build_context_query(task_context)

        # Search for relevant knowledge
        search_results = await self.search_team_knowledge(
            team_id=team_id,
            query=context_query,
            limit=max_context_items,
            min_similarity=0.4,
        )

        # Get team statistics
        team_stats = await self.get_team_knowledge_stats(team_id)

        # Build context
        context = {
            "team_id": team_id,
            "relevant_knowledge": [
                {
                    "id": result.team_knowledge.id,
                    "title": result.team_knowledge.title,
                    "content": (
                        result.team_knowledge.content[:500] + "..."
                        if len(result.team_knowledge.content) > 500
                        else result.team_knowledge.content
                    ),
                    "category": result.team_knowledge.knowledge_category.value,
                    "relevance_score": result.combined_score,
                    "usage_stats": {
                        "adoption_rate": result.team_knowledge.agent_adoption_rate,
                        "effectiveness": result.team_knowledge.effectiveness_score,
                    },
                }
                for result in search_results
            ],
            "team_knowledge_stats": team_stats,
            "context_query": context_query,
            "generated_at": datetime.now().isoformat(),
        }

        return context

    async def update_knowledge_effectiveness(
        self,
        team_knowledge_id: str,
        agent_id: str,
        task_success: bool,
        feedback_score: Optional[float] = None,
        usage_context: Optional[Dict[str, Any]] = None,
    ):
        """Update knowledge effectiveness based on agent usage"""

        async with self.pool.acquire() as conn:
            # Get current knowledge
            knowledge = await conn.fetchrow(
                """
                SELECT * FROM team_knowledge_base WHERE id = $1
            """,
                team_knowledge_id,
            )

            if not knowledge:
                return

            # Calculate new effectiveness score
            success_weight = 1.0 if task_success else -0.3
            feedback_weight = (feedback_score or 0.5) - 0.5

            # Update effectiveness with exponential moving average
            current_effectiveness = knowledge["effectiveness_score"]
            new_effectiveness = (
                current_effectiveness * 0.8 + (success_weight + feedback_weight) * 0.2
            )
            new_effectiveness = max(0.0, min(1.0, new_effectiveness))

            # Update agent adoption tracking
            contributing_agents = knowledge["contributing_agents"] or []
            if agent_id not in contributing_agents:
                contributing_agents.append(agent_id)

            # Calculate adoption rate (agents who used it / total team agents)
            team_agent_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM agents WHERE team_id = $1
            """,
                knowledge["team_id"],
            )

            adoption_rate = len(contributing_agents) / max(1, team_agent_count)

            # Update knowledge
            await conn.execute(
                """
                UPDATE team_knowledge_base 
                SET effectiveness_score = $2,
                    agent_adoption_rate = $3,
                    contributing_agents = $4,
                    last_accessed = NOW(),
                    updated_at = NOW()
                WHERE id = $1
            """,
                team_knowledge_id,
                new_effectiveness,
                adoption_rate,
                contributing_agents,
            )

            logger.debug(
                f"Updated knowledge {team_knowledge_id} effectiveness: {new_effectiveness:.2f}, adoption: {adoption_rate:.2f}"
            )

    async def get_team_knowledge_stats(self, team_id: str) -> Dict[str, Any]:
        """Get comprehensive team knowledge statistics"""

        async with self.pool.acquire() as conn:
            # Basic statistics
            basic_stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_knowledge,
                    COUNT(DISTINCT knowledge_category) as categories,
                    COUNT(DISTINCT unnest(contributing_agents)) as contributing_agents,
                    AVG(team_relevance_score) as avg_relevance,
                    AVG(effectiveness_score) as avg_effectiveness,
                    AVG(agent_adoption_rate) as avg_adoption_rate
                FROM team_knowledge_base 
                WHERE team_id = $1
            """,
                team_id,
            )

            # Category breakdown
            category_stats = await conn.fetch(
                """
                SELECT 
                    knowledge_category,
                    COUNT(*) as count,
                    AVG(effectiveness_score) as avg_effectiveness,
                    AVG(agent_adoption_rate) as avg_adoption
                FROM team_knowledge_base 
                WHERE team_id = $1
                GROUP BY knowledge_category
                ORDER BY count DESC
            """,
                team_id,
            )

            # Most effective knowledge
            top_knowledge = await conn.fetch(
                """
                SELECT 
                    title,
                    knowledge_category,
                    effectiveness_score,
                    agent_adoption_rate
                FROM team_knowledge_base 
                WHERE team_id = $1
                ORDER BY effectiveness_score DESC
                LIMIT 5
            """,
                team_id,
            )

            return {
                "team_id": team_id,
                "basic_stats": dict(basic_stats) if basic_stats else {},
                "category_breakdown": [dict(cat) for cat in category_stats],
                "top_knowledge": [dict(know) for know in top_knowledge],
                "generated_at": datetime.now().isoformat(),
            }

    async def _search_team_specific_knowledge(
        self,
        conn,
        team_id: str,
        query_embedding: List[float],
        categories: Optional[List[KnowledgeCategory]],
        content_types: Optional[List[ContentType]],
        limit: int,
        min_similarity: float,
    ) -> List[TeamKnowledgeSearchResult]:
        """Search team-specific knowledge base"""

        # Build query conditions
        where_conditions = ["team_id = $2"]
        params = [query_embedding, team_id]
        param_idx = 3

        if categories:
            where_conditions.append(f"knowledge_category = ANY(${param_idx})")
            params.append([cat.value for cat in categories])
            param_idx += 1

        if content_types:
            where_conditions.append(f"content_type = ANY(${param_idx})")
            params.append([ct.value for ct in content_types])
            param_idx += 1

        where_conditions.append(f"(1 - (embedding <=> $1)) >= ${param_idx}")
        params.append(min_similarity)
        param_idx += 1

        where_clause = "WHERE " + " AND ".join(where_conditions)

        results = await conn.fetch(
            f"""
            SELECT 
                *,
                (1 - (embedding <=> $1)) as similarity_score
            FROM team_knowledge_base 
            {where_clause}
            ORDER BY similarity_score DESC, effectiveness_score DESC
            LIMIT ${param_idx}
        """,  # nosec B608 -- where clause is fixed fragments with $N placeholders; all values bound as query params
            *params,
            limit,
        )

        search_results = []
        for row in results:
            team_knowledge = self._row_to_team_knowledge(row)

            # Calculate team fit score based on adoption and effectiveness
            team_fit_score = (
                team_knowledge.agent_adoption_rate * 0.4
                + team_knowledge.effectiveness_score * 0.6
            )

            combined_score = (
                float(row["similarity_score"]) * 0.4
                + team_knowledge.team_relevance_score * 0.3
                + team_fit_score * 0.3
            )

            search_results.append(
                TeamKnowledgeSearchResult(
                    team_knowledge=team_knowledge,
                    similarity_score=float(row["similarity_score"]),
                    relevance_score=team_knowledge.team_relevance_score,
                    team_fit_score=team_fit_score,
                    combined_score=combined_score,
                )
            )

        return search_results

    async def _search_org_knowledge_for_team(
        self,
        conn,
        team_id: str,
        query: str,
        categories: Optional[List[KnowledgeCategory]],
        content_types: Optional[List[ContentType]],
        limit: int,
        min_similarity: float,
    ) -> List[TeamKnowledgeSearchResult]:
        """Search organization knowledge filtered for team relevance"""

        # Get organization ID for the team
        org_id = await conn.fetchval(
            """
            SELECT organization_id FROM teams WHERE id = $1
        """,
            team_id,
        )

        if not org_id:
            return []

        # Search organization knowledge
        org_results = await self.org_rag_manager.search_knowledge(
            organization_id=str(org_id),
            query=query,
            categories=categories,
            content_types=content_types,
            limit=limit * 2,  # Get more to filter for team relevance
            min_similarity=min_similarity,
            requester_team_id=team_id,
        )

        # Convert to team knowledge search results with team relevance scoring
        team_results = []
        for org_result in org_results:
            # Calculate team relevance based on source and usage
            team_relevance = await self._calculate_team_relevance(
                conn, team_id, org_result.knowledge
            )

            if team_relevance >= self.min_team_relevance:
                # Create pseudo team knowledge for consistent interface
                pseudo_team_knowledge = TeamKnowledge(
                    id=org_result.knowledge.id,
                    team_id=team_id,
                    organization_id=org_result.knowledge.organization_id,
                    title=org_result.knowledge.title,
                    content=org_result.knowledge.content,
                    content_type=org_result.knowledge.content_type,
                    knowledge_category=org_result.knowledge.knowledge_category,
                    embedding=org_result.knowledge.embedding,
                    source_type=org_result.knowledge.source_type,
                    contributing_agents=[],
                    source_knowledge_ids=[org_result.knowledge.id],
                    aggregation_method="organization_filter",
                    team_relevance_score=team_relevance,
                    agent_adoption_rate=0.0,
                    effectiveness_score=org_result.knowledge.success_correlation,
                    visibility_level=org_result.knowledge.visibility_level,
                    metadata=org_result.knowledge.metadata,
                    tags=org_result.knowledge.tags,
                    created_at=org_result.knowledge.created_at,
                    updated_at=org_result.knowledge.updated_at,
                    last_accessed=org_result.knowledge.last_accessed,
                )

                combined_score = (
                    org_result.similarity_score * 0.5 + team_relevance * 0.5
                )

                team_results.append(
                    TeamKnowledgeSearchResult(
                        team_knowledge=pseudo_team_knowledge,
                        similarity_score=org_result.similarity_score,
                        relevance_score=org_result.relevance_score,
                        team_fit_score=team_relevance,
                        combined_score=combined_score,
                    )
                )

        return team_results[:limit]

    async def _calculate_team_relevance(
        self, conn, team_id: str, org_knowledge
    ) -> float:
        """Calculate how relevant organization knowledge is for a specific team"""

        relevance_factors = []

        # Factor 1: Source team match
        if org_knowledge.source_team_id == team_id:
            relevance_factors.append(1.0)
        elif org_knowledge.source_team_id:
            # Check if source team is similar to current team
            team_similarity = await self._calculate_team_similarity(
                conn, team_id, org_knowledge.source_team_id
            )
            relevance_factors.append(team_similarity)
        else:
            relevance_factors.append(0.3)  # No team context

        # Factor 2: Category relevance to team's work
        team_categories = await self._get_team_primary_categories(conn, team_id)
        if org_knowledge.knowledge_category.value in team_categories:
            relevance_factors.append(0.9)
        else:
            relevance_factors.append(0.4)

        # Factor 3: Usage by team agents
        team_usage = (
            await conn.fetchval(
                """
            SELECT COUNT(DISTINCT source_agent_id)::float / NULLIF(
                (SELECT COUNT(*) FROM agents WHERE team_id = $1), 0
            )
            FROM organization_knowledge_base 
            WHERE id = $2 AND source_agent_id IN (
                SELECT id FROM agents WHERE team_id = $1
            )
        """,
                team_id,
                org_knowledge.id,
            )
            or 0.0
        )
        relevance_factors.append(team_usage)

        # Factor 4: Base quality and relevance
        relevance_factors.append(org_knowledge.quality_score)
        relevance_factors.append(org_knowledge.relevance_score)

        # Calculate weighted average
        weights = [0.3, 0.25, 0.25, 0.1, 0.1]
        team_relevance = sum(f * w for f, w in zip(relevance_factors, weights))

        return min(1.0, max(0.0, team_relevance))

    async def _calculate_team_similarity(
        self, conn, team_id1: str, team_id2: str
    ) -> float:
        """Calculate similarity between two teams based on their work patterns"""

        # Simple implementation based on team type and settings
        team_info = await conn.fetch(
            """
            SELECT id, team_type, settings FROM teams 
            WHERE id IN ($1, $2)
        """,
            team_id1,
            team_id2,
        )

        if len(team_info) != 2:
            return 0.0

        team1, team2 = team_info

        # Type similarity
        type_similarity = 1.0 if team1["team_type"] == team2["team_type"] else 0.5

        # Settings similarity (simplified)
        settings1 = team1["settings"] or {}
        settings2 = team2["settings"] or {}

        common_keys = set(settings1.keys()) & set(settings2.keys())
        if common_keys:
            settings_similarity = sum(
                1.0 if settings1.get(key) == settings2.get(key) else 0.0
                for key in common_keys
            ) / len(common_keys)
        else:
            settings_similarity = 0.5

        return type_similarity * 0.7 + settings_similarity * 0.3

    async def _get_team_primary_categories(self, conn, team_id: str) -> List[str]:
        """Get primary knowledge categories this team works with"""

        categories = await conn.fetch(
            """
            SELECT knowledge_category, COUNT(*) as usage_count
            FROM team_knowledge_base 
            WHERE team_id = $1
            GROUP BY knowledge_category
            ORDER BY usage_count DESC
            LIMIT 3
        """,
            team_id,
        )

        return [cat["knowledge_category"] for cat in categories]

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using sentence transformers"""
        try:
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * self.embedding_dim

    def _row_to_team_knowledge(self, row) -> TeamKnowledge:
        """Convert database row to TeamKnowledge object"""
        return TeamKnowledge(
            id=str(row["id"]),
            team_id=str(row["team_id"]),
            organization_id=str(row["organization_id"]),
            title=row["title"],
            content=row["content"],
            content_type=ContentType(row["content_type"]),
            knowledge_category=KnowledgeCategory(row["knowledge_category"]),
            embedding=row["embedding"] if row["embedding"] else None,
            source_type=SourceType(row["source_type"]),
            contributing_agents=row["contributing_agents"] or [],
            source_knowledge_ids=row["source_knowledge_ids"] or [],
            aggregation_method=row["aggregation_method"],
            team_relevance_score=row["team_relevance_score"],
            agent_adoption_rate=row["agent_adoption_rate"],
            effectiveness_score=row["effectiveness_score"],
            visibility_level=VisibilityLevel(row["visibility_level"]),
            metadata=(
                json.loads(row["metadata"])
                if isinstance(row["metadata"], str)
                else row["metadata"]
            ),
            tags=row["tags"] or [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_accessed=row["last_accessed"],
        )

    def _build_context_query(self, task_context: Dict[str, Any]) -> str:
        """Build a search query from task context"""
        query_parts = []

        if task_context.get("task_type"):
            query_parts.append(task_context["task_type"])

        if task_context.get("description"):
            query_parts.append(task_context["description"])

        if task_context.get("technologies"):
            query_parts.extend(task_context["technologies"])

        if task_context.get("domain"):
            query_parts.append(task_context["domain"])

        return " ".join(query_parts)

    async def _analyze_memories_for_aggregation(
        self, agent_memories: List
    ) -> Dict[str, Any]:
        """Analyze agent memories to determine if they should be aggregated"""

        if not agent_memories:
            return {"aggregation_value": 0.0}

        # Simple aggregation analysis
        # In practice, this could use more sophisticated NLP

        # Calculate average confidence and success correlation
        avg_confidence = sum(mem["confidence_score"] for mem in agent_memories) / len(
            agent_memories
        )
        avg_success = sum(
            mem.get("success_correlation", 0.0) for mem in agent_memories
        ) / len(agent_memories)

        # Find common themes
        all_content = " ".join(mem["content"] for mem in agent_memories)

        # Determine primary category
        categories = [mem.get("memory_type", "general") for mem in agent_memories]
        primary_category = (
            max(set(categories), key=categories.count) if categories else "general"
        )

        # Create aggregated content (simplified)
        title = f"Team Knowledge: {primary_category.replace('_', ' ').title()}"
        content = (
            f"Aggregated knowledge from {len(agent_memories)} agent experiences:\n\n"
            + all_content[:1000]
        )

        # Map memory type to knowledge category
        category_mapping = {
            "code_pattern": KnowledgeCategory.DEVELOPMENT,
            "task_outcome": KnowledgeCategory.PROCESS,
            "debugging": KnowledgeCategory.TROUBLESHOOTING,
            "optimization": KnowledgeCategory.DEVELOPMENT,
            "testing": KnowledgeCategory.TESTING,
        }

        knowledge_category = category_mapping.get(
            primary_category, KnowledgeCategory.DEVELOPMENT
        )

        # Determine content type
        content_type = (
            ContentType.CODE if "code" in primary_category else ContentType.TEXT
        )

        # Calculate aggregation value
        aggregation_value = min(1.0, (avg_confidence + avg_success) / 2.0)

        return {
            "aggregation_value": aggregation_value,
            "title": title,
            "content": content,
            "content_type": content_type,
            "category": knowledge_category,
            "metadata": {
                "source_memory_count": len(agent_memories),
                "avg_confidence": avg_confidence,
                "avg_success_correlation": avg_success,
                "primary_type": primary_category,
            },
            "tags": [primary_category, "aggregated", "agent_contribution"],
        }
