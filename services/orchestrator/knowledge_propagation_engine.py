"""
Knowledge Propagation Engine for FuzeAgent

This module handles automated knowledge flow between agents, teams, and organizations.
It determines when knowledge should be propagated, executes the propagation,
and manages the lifecycle of knowledge across hierarchical levels.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum

import asyncpg
from sentence_transformers import SentenceTransformer

from organization_rag_manager import (
    OrganizationRAGManager,
    KnowledgeCategory,
    ContentType,
    SourceType,
    VisibilityLevel,
)
from team_knowledge_manager import TeamKnowledgeManager

logger = logging.getLogger(__name__)


class PropagationTrigger(str, Enum):
    TASK_COMPLETION = "task_completion"
    KNOWLEDGE_THRESHOLD = "knowledge_threshold"
    MANUAL_REQUEST = "manual_request"
    SCHEDULED_SYNC = "scheduled_sync"
    CROSS_TEAM_REQUEST = "cross_team_request"
    QUALITY_IMPROVEMENT = "quality_improvement"


class PropagationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class AcceptanceStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class PropagationRule:
    """Defines rules for knowledge propagation"""

    source_type: str  # 'agent', 'team', 'organization'
    target_type: str  # 'agent', 'team', 'organization'
    min_confidence: float
    min_success_correlation: float
    min_usage_count: int
    knowledge_categories: List[KnowledgeCategory]
    auto_approve: bool
    propagation_weight: float


@dataclass
class PropagationTask:
    """Represents a knowledge propagation task"""

    id: str
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    knowledge_type: str
    knowledge_content_id: str
    propagation_method: str
    propagation_trigger: PropagationTrigger
    confidence_score: float
    propagation_status: PropagationStatus
    acceptance_status: AcceptanceStatus
    metadata: Dict[str, Any]
    created_at: datetime
    processed_at: Optional[datetime]
    completed_at: Optional[datetime]


class KnowledgePropagationEngine:
    """
    Manages the automated flow of knowledge across the organization hierarchy.
    Handles agent → team → organization propagation and cross-team sharing.
    """

    def __init__(
        self,
        database_url: str,
        org_rag_manager: OrganizationRAGManager,
        team_knowledge_manager: TeamKnowledgeManager,
    ):
        self.database_url = database_url
        self.org_rag_manager = org_rag_manager
        self.team_knowledge_manager = team_knowledge_manager
        self.pool: Optional[asyncpg.Pool] = None

        # Initialize embedding model for similarity analysis
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

        # Default propagation rules
        self.default_rules = self._create_default_propagation_rules()

        # Configuration
        self.propagation_batch_size = 50
        self.max_concurrent_propagations = 5
        self.similarity_threshold = 0.8
        self.propagation_cooldown_hours = 24

        # Statistics
        self.propagations_processed = 0
        self.propagations_completed = 0
        self.propagations_rejected = 0

        # Background task management
        self._propagation_task: Optional[asyncio.Task] = None
        self._running = False

    async def initialize(self):
        """Initialize the knowledge propagation engine"""
        logger.info("Initializing KnowledgePropagationEngine")

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=2, max_size=10, command_timeout=60
            )

            # Start background propagation processing
            self._running = True
            self._propagation_task = asyncio.create_task(
                self._background_propagation_processor()
            )

            logger.info("KnowledgePropagationEngine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize KnowledgePropagationEngine: {e}")
            raise

    async def close(self):
        """Close the propagation engine and cleanup resources"""
        self._running = False

        if self._propagation_task:
            self._propagation_task.cancel()
            try:
                await self._propagation_task
            except asyncio.CancelledError:
                pass

        if self.pool:
            await self.pool.close()

        logger.info("KnowledgePropagationEngine closed")

    async def trigger_agent_to_team_propagation(
        self, agent_id: str, task_id: str, task_outcome: Dict[str, Any]
    ) -> List[str]:
        """Trigger knowledge propagation from agent to team level after task completion"""

        propagation_ids = []

        async with self.pool.acquire() as conn:
            # Get agent's team
            team_id = await conn.fetchval(
                """
                SELECT team_id FROM agents WHERE id = $1
            """,
                agent_id,
            )

            if not team_id:
                logger.warning(f"No team found for agent {agent_id}")
                return propagation_ids

            # Get recent agent memories from this task
            recent_memories = await conn.fetch(
                """
                SELECT * FROM agent_memory 
                WHERE agent_id = $1 
                  AND task_id = $2
                  AND confidence_score >= 0.6
                  AND propagated_to_team = FALSE
                ORDER BY confidence_score DESC, created_at DESC
            """,
                agent_id,
                task_id,
            )

            # Group memories by type and analyze for propagation
            memory_groups = self._group_memories_for_propagation(recent_memories)

            for group_type, memories in memory_groups.items():
                if len(memories) >= 1 and self._meets_propagation_criteria(
                    memories, task_outcome
                ):
                    # Create propagation task
                    propagation_id = await self._create_propagation_task(
                        source_type="agent",
                        source_id=agent_id,
                        target_type="team",
                        target_id=str(team_id),
                        knowledge_type=group_type,
                        knowledge_content_ids=[str(mem["id"]) for mem in memories],
                        propagation_trigger=PropagationTrigger.TASK_COMPLETION,
                        confidence_score=self._calculate_group_confidence(memories),
                        metadata={
                            "task_id": task_id,
                            "task_outcome": task_outcome,
                            "memory_count": len(memories),
                        },
                    )

                    propagation_ids.append(propagation_id)

        logger.info(
            f"Created {len(propagation_ids)} propagation tasks for agent {agent_id} → team {team_id}"
        )
        return propagation_ids

    async def trigger_team_to_org_propagation(
        self, team_id: str, knowledge_threshold_check: bool = True
    ) -> List[str]:
        """Trigger knowledge propagation from team to organization level"""

        propagation_ids = []

        async with self.pool.acquire() as conn:
            # Get organization ID
            org_id = await conn.fetchval(
                """
                SELECT organization_id FROM teams WHERE id = $1
            """,
                team_id,
            )

            if not org_id:
                logger.warning(f"No organization found for team {team_id}")
                return propagation_ids

            # Find high-value team knowledge for propagation
            if knowledge_threshold_check:
                team_knowledge = await conn.fetch(
                    """
                    SELECT * FROM team_knowledge_base 
                    WHERE team_id = $1
                      AND effectiveness_score >= 0.7
                      AND agent_adoption_rate >= 0.5
                      AND created_at <= NOW() - INTERVAL '7 days'  -- Allow time for validation
                    ORDER BY effectiveness_score DESC, agent_adoption_rate DESC
                """,
                    team_id,
                )
            else:
                team_knowledge = await conn.fetch(
                    """
                    SELECT * FROM team_knowledge_base 
                    WHERE team_id = $1
                    ORDER BY effectiveness_score DESC
                    LIMIT 10
                """,
                    team_id,
                )

            for knowledge in team_knowledge:
                # Check if similar knowledge already exists at org level
                if not await self._check_for_similar_org_knowledge(
                    knowledge, str(org_id)
                ):
                    # Create propagation task
                    propagation_id = await self._create_propagation_task(
                        source_type="team",
                        source_id=team_id,
                        target_type="organization",
                        target_id=str(org_id),
                        knowledge_type=knowledge["knowledge_category"],
                        knowledge_content_ids=[str(knowledge["id"])],
                        propagation_trigger=PropagationTrigger.KNOWLEDGE_THRESHOLD,
                        confidence_score=knowledge["effectiveness_score"],
                        metadata={
                            "team_knowledge_id": str(knowledge["id"]),
                            "adoption_rate": knowledge["agent_adoption_rate"],
                            "contributing_agents": knowledge["contributing_agents"],
                        },
                    )

                    propagation_ids.append(propagation_id)

        logger.info(
            f"Created {len(propagation_ids)} propagation tasks for team {team_id} → organization {org_id}"
        )
        return propagation_ids

    async def trigger_cross_team_sharing(
        self,
        source_team_id: str,
        knowledge_categories: List[KnowledgeCategory],
        target_teams: Optional[List[str]] = None,
    ) -> List[str]:
        """Trigger knowledge sharing between teams"""

        propagation_ids = []

        async with self.pool.acquire() as conn:
            # Get organization and determine target teams
            org_id = await conn.fetchval(
                """
                SELECT organization_id FROM teams WHERE id = $1
            """,
                source_team_id,
            )

            if not org_id:
                return propagation_ids

            if not target_teams:
                # Get all teams in the organization except source team
                target_teams_rows = await conn.fetch(
                    """
                    SELECT id FROM teams 
                    WHERE organization_id = $1 AND id != $2
                """,
                    org_id,
                    source_team_id,
                )
                target_teams = [str(row["id"]) for row in target_teams_rows]

            # Get relevant knowledge from source team
            category_list = [cat.value for cat in knowledge_categories]
            source_knowledge = await conn.fetch(
                """
                SELECT * FROM team_knowledge_base 
                WHERE team_id = $1 
                  AND knowledge_category = ANY($2)
                  AND effectiveness_score >= 0.6
                ORDER BY effectiveness_score DESC
                LIMIT 20
            """,
                source_team_id,
                category_list,
            )

            # Create propagation tasks for each target team
            for target_team_id in target_teams:
                for knowledge in source_knowledge:
                    # Check if target team would benefit from this knowledge
                    relevance = await self._calculate_cross_team_relevance(
                        knowledge, source_team_id, target_team_id
                    )

                    if relevance >= 0.5:
                        propagation_id = await self._create_propagation_task(
                            source_type="team",
                            source_id=source_team_id,
                            target_type="team",
                            target_id=target_team_id,
                            knowledge_type=knowledge["knowledge_category"],
                            knowledge_content_ids=[str(knowledge["id"])],
                            propagation_trigger=PropagationTrigger.CROSS_TEAM_REQUEST,
                            confidence_score=relevance,
                            metadata={
                                "cross_team_relevance": relevance,
                                "source_effectiveness": knowledge[
                                    "effectiveness_score"
                                ],
                            },
                        )

                        propagation_ids.append(propagation_id)

        logger.info(f"Created {len(propagation_ids)} cross-team propagation tasks")
        return propagation_ids

    async def process_pending_propagations(self, limit: int = 10) -> Dict[str, int]:
        """Process pending propagation tasks"""

        results = {"processed": 0, "completed": 0, "failed": 0}

        async with self.pool.acquire() as conn:
            # Get pending propagation tasks
            pending_tasks = await conn.fetch(
                """
                SELECT * FROM knowledge_propagation_log 
                WHERE propagation_status = 'pending'
                ORDER BY propagated_at ASC
                LIMIT $1
            """,
                limit,
            )

            for task_row in pending_tasks:
                task = self._row_to_propagation_task(task_row)

                try:
                    # Update status to processing
                    await conn.execute(
                        """
                        UPDATE knowledge_propagation_log 
                        SET propagation_status = 'processing', processed_at = NOW()
                        WHERE id = $1
                    """,
                        task.id,
                    )

                    # Process the propagation
                    success = await self._execute_propagation(task)

                    if success:
                        # Mark as completed
                        await conn.execute(
                            """
                            UPDATE knowledge_propagation_log 
                            SET propagation_status = 'completed', 
                                acceptance_status = 'accepted',
                                completed_at = NOW()
                            WHERE id = $1
                        """,
                            task.id,
                        )
                        results["completed"] += 1
                        self.propagations_completed += 1
                    else:
                        # Mark as failed
                        await conn.execute(
                            """
                            UPDATE knowledge_propagation_log 
                            SET propagation_status = 'failed'
                            WHERE id = $1
                        """,
                            task.id,
                        )
                        results["failed"] += 1

                    results["processed"] += 1
                    self.propagations_processed += 1

                except Exception as e:
                    logger.error(f"Error processing propagation task {task.id}: {e}")
                    await conn.execute(
                        """
                        UPDATE knowledge_propagation_log 
                        SET propagation_status = 'failed',
                            metadata = metadata || $2
                        WHERE id = $1
                    """,
                        task.id,
                        json.dumps({"error": str(e)}),
                    )
                    results["failed"] += 1

        return results

    async def get_propagation_statistics(
        self,
        organization_id: Optional[str] = None,
        team_id: Optional[str] = None,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """Get comprehensive propagation statistics"""

        async with self.pool.acquire() as conn:
            where_conditions = [
                "propagated_at >= NOW() - INTERVAL '%s days'" % days_back
            ]
            params = []

            if organization_id:
                where_conditions.append(
                    "target_id = $1 AND target_type = 'organization'"
                )
                params.append(organization_id)
            elif team_id:
                where_conditions.append(
                    "(target_id = $1 OR source_id = $1) AND ('team' = ANY(ARRAY[target_type, source_type]))"
                )
                params.append(team_id)

            where_clause = "WHERE " + " AND ".join(where_conditions)

            # Basic statistics
            stats = await conn.fetchrow(
                f"""
                SELECT 
                    COUNT(*) as total_propagations,
                    COUNT(CASE WHEN propagation_status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN propagation_status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN propagation_status = 'pending' THEN 1 END) as pending,
                    COUNT(CASE WHEN acceptance_status = 'accepted' THEN 1 END) as accepted,
                    COUNT(CASE WHEN acceptance_status = 'rejected' THEN 1 END) as rejected,
                    AVG(confidence_score) as avg_confidence
                FROM knowledge_propagation_log
                {where_clause}
            """,
                *params,
            )

            # Propagation flow statistics
            flow_stats = await conn.fetch(
                f"""
                SELECT 
                    source_type || ' → ' || target_type as flow_type,
                    COUNT(*) as count,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(CASE WHEN propagation_status = 'completed' THEN 1 END)::float / COUNT(*) as success_rate
                FROM knowledge_propagation_log
                {where_clause}
                GROUP BY source_type, target_type
                ORDER BY count DESC
            """,
                *params,
            )

            # Trigger analysis
            trigger_stats = await conn.fetch(
                f"""
                SELECT 
                    propagation_trigger,
                    COUNT(*) as count,
                    AVG(confidence_score) as avg_confidence
                FROM knowledge_propagation_log
                {where_clause}
                GROUP BY propagation_trigger
                ORDER BY count DESC
            """,
                *params,
            )

            return {
                "time_period_days": days_back,
                "basic_stats": dict(stats) if stats else {},
                "flow_patterns": [dict(flow) for flow in flow_stats],
                "trigger_analysis": [dict(trigger) for trigger in trigger_stats],
                "generated_at": datetime.now().isoformat(),
            }

    async def _background_propagation_processor(self):
        """Background task to continuously process propagation queue"""

        while self._running:
            try:
                # Process a batch of propagations
                results = await self.process_pending_propagations(
                    self.propagation_batch_size
                )

                if results["processed"] > 0:
                    logger.info(
                        f"Processed {results['processed']} propagations: "
                        f"{results['completed']} completed, {results['failed']} failed"
                    )

                # Sleep between processing cycles
                await asyncio.sleep(30)  # Process every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background propagation processor: {e}")
                await asyncio.sleep(60)  # Wait longer after errors

    async def _create_propagation_task(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        knowledge_type: str,
        knowledge_content_ids: List[str],
        propagation_trigger: PropagationTrigger,
        confidence_score: float,
        metadata: Dict[str, Any],
    ) -> str:
        """Create a new propagation task"""

        propagation_id = str(uuid.uuid4())

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO knowledge_propagation_log (
                    id, source_type, source_id, target_type, target_id,
                    knowledge_type, propagation_method, propagation_trigger,
                    confidence_score, propagation_status, acceptance_status, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, 'automatic', $7, $8, 'pending', 'pending', $9)
            """,
                propagation_id,
                source_type,
                source_id,
                target_type,
                target_id,
                knowledge_type,
                propagation_trigger.value,
                confidence_score,
                json.dumps({**metadata, "content_ids": knowledge_content_ids}),
            )

        return propagation_id

    async def _execute_propagation(self, task: PropagationTask) -> bool:
        """Execute a specific propagation task"""

        try:
            if task.source_type == "agent" and task.target_type == "team":
                return await self._execute_agent_to_team_propagation(task)
            elif task.source_type == "team" and task.target_type == "organization":
                return await self._execute_team_to_org_propagation(task)
            elif task.source_type == "team" and task.target_type == "team":
                return await self._execute_team_to_team_propagation(task)
            else:
                logger.warning(
                    f"Unsupported propagation type: {task.source_type} → {task.target_type}"
                )
                return False

        except Exception as e:
            logger.error(f"Error executing propagation {task.id}: {e}")
            return False

    async def _execute_agent_to_team_propagation(self, task: PropagationTask) -> bool:
        """Execute agent → team propagation"""

        content_ids = task.metadata.get("content_ids", [])
        if not content_ids:
            return False

        # Aggregate agent memories to team knowledge
        result = await self.team_knowledge_manager.aggregate_agent_knowledge_to_team(
            team_id=task.target_id,
            agent_id=task.source_id,
            agent_memory_ids=content_ids,
            aggregation_method="propagation",
        )

        return result is not None

    async def _execute_team_to_org_propagation(self, task: PropagationTask) -> bool:
        """Execute team → organization propagation"""

        team_knowledge_id = task.metadata.get("team_knowledge_id")
        if not team_knowledge_id:
            return False

        async with self.pool.acquire() as conn:
            # Get team knowledge
            team_knowledge = await conn.fetchrow(
                """
                SELECT * FROM team_knowledge_base WHERE id = $1
            """,
                team_knowledge_id,
            )

            if not team_knowledge:
                return False

            # Create organization knowledge
            org_knowledge_id = await self.org_rag_manager.add_knowledge(
                organization_id=task.target_id,
                title=f"[Team Contribution] {team_knowledge['title']}",
                content=team_knowledge["content"],
                content_type=ContentType(team_knowledge["content_type"]),
                knowledge_category=KnowledgeCategory(
                    team_knowledge["knowledge_category"]
                ),
                source_type=SourceType.TEAM_AGGREGATION,
                source_team_id=task.source_id,
                relevance_score=team_knowledge["effectiveness_score"],
                quality_score=team_knowledge["effectiveness_score"],
                visibility_level=VisibilityLevel.ORGANIZATION,
                metadata={
                    "team_adoption_rate": team_knowledge["agent_adoption_rate"],
                    "team_effectiveness": team_knowledge["effectiveness_score"],
                    "contributing_agents": team_knowledge["contributing_agents"],
                    "propagation_task_id": task.id,
                },
                tags=team_knowledge["tags"] + ["team_contribution"],
            )

            return org_knowledge_id is not None

    async def _execute_team_to_team_propagation(self, task: PropagationTask) -> bool:
        """Execute team → team propagation"""

        team_knowledge_id = task.metadata.get("content_ids", [None])[0]
        if not team_knowledge_id:
            return False

        async with self.pool.acquire() as conn:
            # Get source team knowledge
            source_knowledge = await conn.fetchrow(
                """
                SELECT * FROM team_knowledge_base WHERE id = $1
            """,
                team_knowledge_id,
            )

            if not source_knowledge:
                return False

            # Create adapted knowledge for target team
            adapted_knowledge_id = (
                await self.team_knowledge_manager.create_team_knowledge(
                    team_id=task.target_id,
                    title=f"[Shared] {source_knowledge['title']}",
                    content=source_knowledge["content"],
                    content_type=ContentType(source_knowledge["content_type"]),
                    knowledge_category=KnowledgeCategory(
                        source_knowledge["knowledge_category"]
                    ),
                    source_type=SourceType.TEAM_AGGREGATION,
                    contributing_agents=[],
                    source_knowledge_ids=[team_knowledge_id],
                    aggregation_method="cross_team_sharing",
                    team_relevance_score=task.confidence_score,
                    metadata={
                        "source_team_id": task.source_id,
                        "cross_team_propagation": True,
                        "original_effectiveness": source_knowledge[
                            "effectiveness_score"
                        ],
                        "propagation_task_id": task.id,
                    },
                    tags=source_knowledge["tags"] + ["cross_team_shared"],
                )
            )

            return adapted_knowledge_id is not None

    def _group_memories_for_propagation(self, memories: List) -> Dict[str, List]:
        """Group memories by type for propagation analysis"""
        groups = {}

        for memory in memories:
            memory_type = memory.get("memory_type", "general")
            if memory_type not in groups:
                groups[memory_type] = []
            groups[memory_type].append(memory)

        return groups

    def _meets_propagation_criteria(
        self, memories: List, task_outcome: Dict[str, Any]
    ) -> bool:
        """Determine if memories meet criteria for propagation"""

        # Check success rate
        success = task_outcome.get("success", False)
        if not success:
            return False

        # Check confidence scores
        avg_confidence = sum(mem["confidence_score"] for mem in memories) / len(
            memories
        )
        if avg_confidence < 0.6:
            return False

        # Check memory age (don't propagate very old memories)
        recent_memories = [
            mem for mem in memories if (datetime.now() - mem["created_at"]).days <= 7
        ]

        return (
            len(recent_memories) >= len(memories) * 0.5
        )  # At least 50% should be recent

    def _calculate_group_confidence(self, memories: List) -> float:
        """Calculate confidence score for a group of memories"""
        if not memories:
            return 0.0

        scores = [mem["confidence_score"] for mem in memories]
        success_correlations = [mem.get("success_correlation", 0.0) for mem in memories]

        # Weighted average with recency bias
        weights = [1.0 / (1 + i * 0.1) for i in range(len(memories))]

        weighted_confidence = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        avg_success = (
            sum(success_correlations) / len(success_correlations)
            if success_correlations
            else 0.0
        )

        return min(1.0, weighted_confidence * 0.7 + avg_success * 0.3)

    async def _check_for_similar_org_knowledge(
        self, team_knowledge: Dict, org_id: str
    ) -> bool:
        """Check if similar knowledge already exists at organization level"""

        if not team_knowledge.get("embedding"):
            return False

        # Search for similar content
        search_results = await self.org_rag_manager.search_knowledge(
            organization_id=org_id,
            query=team_knowledge["content"][:200],  # Use beginning of content as query
            limit=5,
            min_similarity=self.similarity_threshold,
        )

        # Check if any results are highly similar
        for result in search_results:
            if result.similarity_score >= self.similarity_threshold:
                return True

        return False

    async def _calculate_cross_team_relevance(
        self, knowledge: Dict, source_team_id: str, target_team_id: str
    ) -> float:
        """Calculate how relevant knowledge from one team is for another team"""

        async with self.pool.acquire() as conn:
            # Get team information
            teams = await conn.fetch(
                """
                SELECT id, team_type, settings FROM teams 
                WHERE id IN ($1, $2)
            """,
                source_team_id,
                target_team_id,
            )

            if len(teams) != 2:
                return 0.0

            source_team = next(t for t in teams if str(t["id"]) == source_team_id)
            target_team = next(t for t in teams if str(t["id"]) == target_team_id)

            relevance_factors = []

            # Factor 1: Team type similarity
            type_similarity = (
                1.0 if source_team["team_type"] == target_team["team_type"] else 0.3
            )
            relevance_factors.append(type_similarity)

            # Factor 2: Knowledge category relevance to target team
            target_team_categories = await conn.fetch(
                """
                SELECT knowledge_category, COUNT(*) as usage_count
                FROM team_knowledge_base 
                WHERE team_id = $1
                GROUP BY knowledge_category
                ORDER BY usage_count DESC
                LIMIT 5
            """,
                target_team_id,
            )

            target_categories = [
                cat["knowledge_category"] for cat in target_team_categories
            ]
            category_relevance = (
                1.0 if knowledge["knowledge_category"] in target_categories else 0.4
            )
            relevance_factors.append(category_relevance)

            # Factor 3: Effectiveness score of source knowledge
            effectiveness_factor = knowledge["effectiveness_score"]
            relevance_factors.append(effectiveness_factor)

            # Factor 4: Adoption rate in source team (indicates broad utility)
            adoption_factor = knowledge["agent_adoption_rate"]
            relevance_factors.append(adoption_factor)

            # Calculate weighted relevance
            weights = [0.2, 0.3, 0.3, 0.2]
            relevance = sum(f * w for f, w in zip(relevance_factors, weights))

            return min(1.0, max(0.0, relevance))

    def _create_default_propagation_rules(self) -> List[PropagationRule]:
        """Create default propagation rules"""
        return [
            # Agent to Team rules
            PropagationRule(
                source_type="agent",
                target_type="team",
                min_confidence=0.6,
                min_success_correlation=0.0,
                min_usage_count=1,
                knowledge_categories=list(KnowledgeCategory),
                auto_approve=True,
                propagation_weight=1.0,
            ),
            # Team to Organization rules
            PropagationRule(
                source_type="team",
                target_type="organization",
                min_confidence=0.7,
                min_success_correlation=0.5,
                min_usage_count=3,
                knowledge_categories=list(KnowledgeCategory),
                auto_approve=False,
                propagation_weight=0.8,
            ),
            # Cross-team rules
            PropagationRule(
                source_type="team",
                target_type="team",
                min_confidence=0.65,
                min_success_correlation=0.4,
                min_usage_count=2,
                knowledge_categories=[
                    KnowledgeCategory.DEVELOPMENT,
                    KnowledgeCategory.TESTING,
                    KnowledgeCategory.TROUBLESHOOTING,
                ],
                auto_approve=False,
                propagation_weight=0.6,
            ),
        ]

    def _row_to_propagation_task(self, row) -> PropagationTask:
        """Convert database row to PropagationTask object"""
        return PropagationTask(
            id=str(row["id"]),
            source_type=row["source_type"],
            source_id=str(row["source_id"]),
            target_type=row["target_type"],
            target_id=str(row["target_id"]),
            knowledge_type=row["knowledge_type"],
            knowledge_content_id=(
                str(row["knowledge_content_id"]) if row["knowledge_content_id"] else ""
            ),
            propagation_method=row["propagation_method"],
            propagation_trigger=PropagationTrigger(row["propagation_trigger"]),
            confidence_score=row["confidence_score"],
            propagation_status=PropagationStatus(row["propagation_status"]),
            acceptance_status=AcceptanceStatus(row["acceptance_status"]),
            metadata=(
                json.loads(row["metadata"])
                if isinstance(row["metadata"], str)
                else row["metadata"]
            ),
            created_at=row["propagated_at"],
            processed_at=row["processed_at"],
            completed_at=row["completed_at"],
        )
