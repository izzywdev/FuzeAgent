"""
Context Enhancement Service for FuzeAgent

This service enhances agent context with relevant organizational and team knowledge
before task execution. It provides intelligent knowledge injection based on
task type, agent capabilities, and historical success patterns.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import asyncpg

from .organization_rag_manager import (
    ContentType,
    KnowledgeCategory,
    KnowledgeSearchResult,
    OrganizationRAGManager,
)
from .team_knowledge_manager import TeamKnowledgeManager, TeamKnowledgeSearchResult

logger = logging.getLogger(__name__)


@dataclass
class ContextEnhancement:
    """Represents an enhancement to agent context"""

    knowledge_id: str
    title: str
    content: str
    source_type: str  # 'organization', 'team', 'agent'
    category: str
    relevance_score: float
    confidence_score: float
    usage_stats: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class EnhancedContext:
    """Enhanced context for agent task execution"""

    task_id: str
    agent_id: str
    team_id: str
    organization_id: str
    base_context: Dict[str, Any]
    organizational_knowledge: List[ContextEnhancement]
    team_knowledge: List[ContextEnhancement]
    similar_task_insights: List[ContextEnhancement]
    success_patterns: List[str]
    common_pitfalls: List[str]
    recommended_approaches: List[str]
    context_summary: str
    enhancement_metadata: Dict[str, Any]


class ContextEnhancementService:
    """
    Enhances agent context with relevant organizational knowledge
    to improve task execution success rates.
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

        # Configuration
        self.max_org_knowledge_items = 5
        self.max_team_knowledge_items = 8
        self.max_similar_tasks = 3
        self.min_relevance_threshold = 0.4
        self.context_freshness_days = 90

        # Statistics
        self.enhancements_created = 0
        self.average_enhancement_score = 0.0
        self.knowledge_usage_tracking = {}

    async def initialize(self):
        """Initialize the context enhancement service"""
        logger.info("Initializing ContextEnhancementService")

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=5, command_timeout=60
            )

            logger.info("ContextEnhancementService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ContextEnhancementService: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        logger.info("ContextEnhancementService closed")

    async def enhance_agent_context(
        self,
        agent_id: str,
        task_data: Dict[str, Any],
        base_context: Optional[Dict[str, Any]] = None,
    ) -> EnhancedContext:
        """Enhance agent context with relevant organizational knowledge"""

        try:
            # Get agent and team information
            agent_info = await self._get_agent_info(agent_id)
            if not agent_info:
                raise ValueError(f"Agent {agent_id} not found")

            # Build search queries based on task data
            search_queries = self._build_search_queries(task_data, agent_info)

            # Gather knowledge from different sources
            org_knowledge = await self._gather_organizational_knowledge(
                agent_info["organization_id"],
                search_queries,
                agent_id,
                agent_info["team_id"],
            )

            team_knowledge = await self._gather_team_knowledge(
                agent_info["team_id"], search_queries
            )

            similar_tasks = await self._find_similar_task_insights(
                agent_info["organization_id"], task_data, agent_id
            )

            # Extract patterns and recommendations
            success_patterns = await self._extract_success_patterns(
                org_knowledge + team_knowledge + similar_tasks
            )

            pitfalls = await self._extract_common_pitfalls(
                agent_info["organization_id"], task_data
            )

            recommendations = await self._generate_recommendations(
                task_data, org_knowledge, team_knowledge, similar_tasks
            )

            # Create context summary
            context_summary = self._create_context_summary(
                task_data, org_knowledge, team_knowledge, success_patterns
            )

            # Build enhanced context
            enhanced_context = EnhancedContext(
                task_id=task_data.get("task_id", ""),
                agent_id=agent_id,
                team_id=agent_info["team_id"],
                organization_id=agent_info["organization_id"],
                base_context=base_context or {},
                organizational_knowledge=org_knowledge,
                team_knowledge=team_knowledge,
                similar_task_insights=similar_tasks,
                success_patterns=success_patterns,
                common_pitfalls=pitfalls,
                recommended_approaches=recommendations,
                context_summary=context_summary,
                enhancement_metadata={
                    "enhancement_timestamp": datetime.now().isoformat(),
                    "search_queries_used": search_queries,
                    "knowledge_sources_count": {
                        "organizational": len(org_knowledge),
                        "team": len(team_knowledge),
                        "similar_tasks": len(similar_tasks),
                    },
                    "total_relevance_score": sum(
                        item.relevance_score
                        for item in org_knowledge + team_knowledge + similar_tasks
                    ),
                    "enhancement_version": "1.0",
                },
            )

            # Track enhancement usage
            await self._track_enhancement_usage(enhanced_context)

            self.enhancements_created += 1

            logger.info(
                f"Enhanced context for agent {agent_id}: "
                f"{len(org_knowledge)} org + {len(team_knowledge)} team + "
                f"{len(similar_tasks)} similar task insights"
            )

            return enhanced_context

        except Exception as e:
            logger.error(f"Error enhancing context for agent {agent_id}: {e}")
            # Return minimal enhanced context on error
            return EnhancedContext(
                task_id=task_data.get("task_id", ""),
                agent_id=agent_id,
                team_id="",
                organization_id="",
                base_context=base_context or {},
                organizational_knowledge=[],
                team_knowledge=[],
                similar_task_insights=[],
                success_patterns=[],
                common_pitfalls=[],
                recommended_approaches=[],
                context_summary="Context enhancement failed - using minimal context",
                enhancement_metadata={"error": str(e)},
            )

    async def get_contextual_guidance(
        self,
        agent_id: str,
        current_task_context: Dict[str, Any],
        current_iteration: int = 1,
    ) -> Dict[str, Any]:
        """Get contextual guidance during task execution"""

        try:
            agent_info = await self._get_agent_info(agent_id)
            if not agent_info:
                return {"guidance": [], "suggestions": []}

            # Build guidance based on current context
            guidance_items = []

            # Get iteration-specific guidance
            if current_iteration > 3:
                guidance_items.extend(
                    await self._get_iteration_guidance(
                        agent_info["organization_id"], current_iteration
                    )
                )

            # Get context-specific suggestions
            suggestions = await self._get_contextual_suggestions(
                agent_info["organization_id"],
                agent_info["team_id"],
                current_task_context,
            )

            return {
                "guidance": guidance_items,
                "suggestions": suggestions,
                "iteration": current_iteration,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting contextual guidance: {e}")
            return {"guidance": [], "suggestions": []}

    async def update_knowledge_effectiveness(
        self,
        knowledge_id: str,
        knowledge_source: str,
        task_success: bool,
        agent_feedback: Optional[Dict[str, Any]] = None,
    ):
        """Update knowledge effectiveness based on usage outcomes"""

        try:
            if knowledge_source == "organization":
                await self.org_rag_manager.update_knowledge_quality(
                    knowledge_id=knowledge_id,
                    success_correlation=1.0 if task_success else -0.2,
                    feedback_metadata=agent_feedback,
                )
            elif knowledge_source == "team":
                # Update team knowledge effectiveness
                async with self.pool.acquire() as conn:
                    agent_id = (
                        agent_feedback.get("agent_id") if agent_feedback else None
                    )
                    if agent_id:
                        await self.team_knowledge_manager.update_knowledge_effectiveness(
                            team_knowledge_id=knowledge_id,
                            agent_id=agent_id,
                            task_success=task_success,
                            feedback_score=agent_feedback.get("usefulness_score"),
                            usage_context=agent_feedback,
                        )

            # Track in local usage statistics
            if knowledge_id not in self.knowledge_usage_tracking:
                self.knowledge_usage_tracking[knowledge_id] = {
                    "usage_count": 0,
                    "success_count": 0,
                    "effectiveness_score": 0.0,
                }

            stats = self.knowledge_usage_tracking[knowledge_id]
            stats["usage_count"] += 1
            if task_success:
                stats["success_count"] += 1
            stats["effectiveness_score"] = stats["success_count"] / stats["usage_count"]

        except Exception as e:
            logger.error(f"Error updating knowledge effectiveness: {e}")

    async def get_enhancement_statistics(
        self,
        organization_id: Optional[str] = None,
        team_id: Optional[str] = None,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """Get context enhancement statistics"""

        try:
            async with self.pool.acquire() as conn:
                # Basic enhancement statistics
                where_conditions = [
                    "created_at >= NOW() - INTERVAL '%s days'" % days_back
                ]
                params = []

                if organization_id:
                    where_conditions.append("organization_id = $1")
                    params.append(organization_id)

                if team_id:
                    where_conditions.append(
                        "team_id = $2" if organization_id else "team_id = $1"
                    )
                    params.append(team_id)

                # This is a placeholder - in practice you'd have a table to track enhancements
                stats = {
                    "total_enhancements": self.enhancements_created,
                    "average_knowledge_items_per_enhancement": {
                        "organizational": 3.2,
                        "team": 4.1,
                        "similar_tasks": 1.8,
                    },
                    "knowledge_effectiveness": dict(self.knowledge_usage_tracking),
                    "generated_at": datetime.now().isoformat(),
                }

                return stats

        except Exception as e:
            logger.error(f"Error getting enhancement statistics: {e}")
            return {}

    async def _get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent information including team and organization"""

        async with self.pool.acquire() as conn:
            agent_info = await conn.fetchrow(
                """
                SELECT a.id, a.name, a.type, a.config, a.team_id,
                       t.organization_id, t.name as team_name,
                       o.name as organization_name
                FROM agents a
                JOIN teams t ON a.team_id = t.id
                JOIN organizations o ON t.organization_id = o.id
                WHERE a.id = $1
            """,
                agent_id,
            )

            return dict(agent_info) if agent_info else None

    def _build_search_queries(
        self, task_data: Dict[str, Any], agent_info: Dict[str, Any]
    ) -> List[str]:
        """Build search queries based on task data and agent information"""

        queries = []

        # Primary query from task description
        if task_data.get("description"):
            queries.append(task_data["description"][:200])

        # Query from task title
        if task_data.get("title"):
            queries.append(task_data["title"])

        # Technology-specific queries
        if task_data.get("technologies"):
            for tech in task_data["technologies"]:
                queries.append(f"{tech} development best practices")

        # Task type specific query
        if task_data.get("task_type"):
            queries.append(f"{task_data['task_type']} implementation guide")

        # Agent type specific query
        agent_type = agent_info.get("type", "")
        if agent_type:
            queries.append(f"{agent_type} workflow best practices")

        return queries[:5]  # Limit to top 5 queries

    async def _gather_organizational_knowledge(
        self,
        organization_id: str,
        search_queries: List[str],
        agent_id: str,
        team_id: str,
    ) -> List[ContextEnhancement]:
        """Gather relevant organizational knowledge"""

        org_knowledge = []

        for query in search_queries:
            search_results = await self.org_rag_manager.search_knowledge(
                organization_id=organization_id,
                query=query,
                limit=self.max_org_knowledge_items // len(search_queries) + 1,
                min_similarity=self.min_relevance_threshold,
                requester_agent_id=agent_id,
                requester_team_id=team_id,
            )

            for result in search_results:
                if result.combined_score >= self.min_relevance_threshold:
                    enhancement = ContextEnhancement(
                        knowledge_id=result.knowledge.id,
                        title=result.knowledge.title,
                        content=result.knowledge.content[:1000] + "..."
                        if len(result.knowledge.content) > 1000
                        else result.knowledge.content,
                        source_type="organization",
                        category=result.knowledge.knowledge_category.value,
                        relevance_score=result.combined_score,
                        confidence_score=result.knowledge.quality_score,
                        usage_stats={
                            "usage_count": result.knowledge.usage_count,
                            "success_correlation": result.knowledge.success_correlation,
                        },
                        metadata=result.knowledge.metadata,
                    )
                    org_knowledge.append(enhancement)

        # Sort by relevance and remove duplicates
        seen_ids = set()
        unique_knowledge = []
        for item in sorted(
            org_knowledge, key=lambda x: x.relevance_score, reverse=True
        ):
            if item.knowledge_id not in seen_ids:
                unique_knowledge.append(item)
                seen_ids.add(item.knowledge_id)

        return unique_knowledge[: self.max_org_knowledge_items]

    async def _gather_team_knowledge(
        self, team_id: str, search_queries: List[str]
    ) -> List[ContextEnhancement]:
        """Gather relevant team knowledge"""

        team_knowledge = []

        for query in search_queries:
            search_results = await self.team_knowledge_manager.search_team_knowledge(
                team_id=team_id,
                query=query,
                limit=self.max_team_knowledge_items // len(search_queries) + 1,
                min_similarity=self.min_relevance_threshold,
            )

            for result in search_results:
                if result.combined_score >= self.min_relevance_threshold:
                    enhancement = ContextEnhancement(
                        knowledge_id=result.team_knowledge.id,
                        title=result.team_knowledge.title,
                        content=result.team_knowledge.content[:1000] + "..."
                        if len(result.team_knowledge.content) > 1000
                        else result.team_knowledge.content,
                        source_type="team",
                        category=result.team_knowledge.knowledge_category.value,
                        relevance_score=result.combined_score,
                        confidence_score=result.team_knowledge.effectiveness_score,
                        usage_stats={
                            "adoption_rate": result.team_knowledge.agent_adoption_rate,
                            "effectiveness": result.team_knowledge.effectiveness_score,
                        },
                        metadata=result.team_knowledge.metadata,
                    )
                    team_knowledge.append(enhancement)

        # Sort and deduplicate
        seen_ids = set()
        unique_knowledge = []
        for item in sorted(
            team_knowledge, key=lambda x: x.relevance_score, reverse=True
        ):
            if item.knowledge_id not in seen_ids:
                unique_knowledge.append(item)
                seen_ids.add(item.knowledge_id)

        return unique_knowledge[: self.max_team_knowledge_items]

    async def _find_similar_task_insights(
        self, organization_id: str, task_data: Dict[str, Any], agent_id: str
    ) -> List[ContextEnhancement]:
        """Find insights from similar completed tasks"""

        similar_tasks = []

        try:
            async with self.pool.acquire() as conn:
                # Find similar tasks based on description similarity and success
                similar_task_data = await conn.fetch(
                    """
                    SELECT t.id, t.title, t.description, t.result, t.completed_at,
                           a.name as agent_name, a.type as agent_type,
                           similarity(t.description, $2) as similarity_score
                    FROM tasks t
                    JOIN agents a ON t.agent_id = a.id
                    JOIN teams te ON a.team_id = te.id
                    WHERE te.organization_id = $1
                      AND t.status = 'completed'
                      AND t.result->>'status' = 'completed'
                      AND t.completed_at >= NOW() - INTERVAL '90 days'
                      AND similarity(t.description, $2) > 0.3
                    ORDER BY similarity_score DESC, t.completed_at DESC
                    LIMIT $3
                """,
                    organization_id,
                    task_data.get("description", ""),
                    self.max_similar_tasks,
                )

                for task in similar_task_data:
                    # Extract insights from the task result
                    task_result = (
                        task["result"] if isinstance(task["result"], dict) else {}
                    )

                    insights_content = self._extract_task_insights(
                        dict(task), task_result
                    )

                    if insights_content:
                        enhancement = ContextEnhancement(
                            knowledge_id=str(task["id"]),
                            title=f"Similar Task: {task['title'][:50]}...",
                            content=insights_content,
                            source_type="similar_task",
                            category="process",
                            relevance_score=float(task["similarity_score"]),
                            confidence_score=0.8,  # High confidence for successful completed tasks
                            usage_stats={
                                "agent_type": task["agent_type"],
                                "completion_date": task["completed_at"].isoformat(),
                            },
                            metadata={
                                "source_task_id": str(task["id"]),
                                "source_agent": task["agent_name"],
                                "similarity_score": float(task["similarity_score"]),
                            },
                        )
                        similar_tasks.append(enhancement)

        except Exception as e:
            logger.error(f"Error finding similar task insights: {e}")

        return similar_tasks

    async def _extract_success_patterns(
        self, all_knowledge: List[ContextEnhancement]
    ) -> List[str]:
        """Extract success patterns from knowledge items"""

        patterns = []

        for item in all_knowledge:
            # Look for success indicators in metadata
            if "success_indicators" in item.metadata:
                patterns.extend(item.metadata["success_indicators"])

            # Extract patterns from high-confidence, high-usage items
            if item.confidence_score > 0.7 and item.relevance_score > 0.6:
                if "optimization" in item.title.lower():
                    patterns.append("Focus on optimization early")
                if "test" in item.title.lower():
                    patterns.append("Comprehensive testing leads to success")
                if "pattern" in item.title.lower():
                    patterns.append("Follow established patterns")

        return list(set(patterns))  # Remove duplicates

    async def _extract_common_pitfalls(
        self, organization_id: str, task_data: Dict[str, Any]
    ) -> List[str]:
        """Extract common pitfalls for this type of task"""

        pitfalls = []

        try:
            # Search for error patterns and failure knowledge
            error_knowledge = await self.org_rag_manager.search_knowledge(
                organization_id=organization_id,
                query=f"error pattern {task_data.get('task_type', '')}",
                categories=[KnowledgeCategory.TROUBLESHOOTING],
                limit=5,
                min_similarity=0.3,
            )

            for result in error_knowledge:
                if "failure_patterns" in result.knowledge.metadata:
                    pitfalls.extend(result.knowledge.metadata["failure_patterns"])

                # Extract pitfalls from error pattern content
                content_lower = result.knowledge.content.lower()
                if (
                    "avoid" in content_lower
                    or "pitfall" in content_lower
                    or "common mistake" in content_lower
                ):
                    pitfalls.append(result.knowledge.title)

        except Exception as e:
            logger.error(f"Error extracting pitfalls: {e}")

        return list(set(pitfalls))[:5]  # Top 5 pitfalls

    async def _generate_recommendations(
        self,
        task_data: Dict[str, Any],
        org_knowledge: List[ContextEnhancement],
        team_knowledge: List[ContextEnhancement],
        similar_tasks: List[ContextEnhancement],
    ) -> List[str]:
        """Generate actionable recommendations based on knowledge"""

        recommendations = []

        # Recommendations from high-value organizational knowledge
        high_value_org = [item for item in org_knowledge if item.confidence_score > 0.7]
        for item in high_value_org[:3]:
            if item.category == "best_practice":
                recommendations.append(f"Apply best practice: {item.title}")
            elif item.category == "development":
                recommendations.append(f"Consider development approach: {item.title}")

        # Recommendations from effective team knowledge
        effective_team = [
            item
            for item in team_knowledge
            if item.usage_stats.get("adoption_rate", 0) > 0.5
        ]
        for item in effective_team[:2]:
            recommendations.append(f"Team recommendation: {item.title}")

        # Recommendations from similar successful tasks
        for task in similar_tasks:
            if task.relevance_score > 0.6:
                recommendations.append(
                    f"Based on similar task: Consider approach used in '{task.title}'"
                )

        return recommendations[:8]  # Limit recommendations

    def _create_context_summary(
        self,
        task_data: Dict[str, Any],
        org_knowledge: List[ContextEnhancement],
        team_knowledge: List[ContextEnhancement],
        success_patterns: List[str],
    ) -> str:
        """Create a summary of the enhanced context"""

        summary_parts = []

        summary_parts.append(f"Enhanced context for: {task_data.get('title', 'Task')}")

        if org_knowledge:
            summary_parts.append(
                f"• {len(org_knowledge)} organizational knowledge items available"
            )

        if team_knowledge:
            summary_parts.append(
                f"• {len(team_knowledge)} team-specific insights included"
            )

        if success_patterns:
            summary_parts.append(
                f"• {len(success_patterns)} success patterns identified"
            )
            summary_parts.append(f"Key patterns: {', '.join(success_patterns[:3])}")

        return "\n".join(summary_parts)

    def _extract_task_insights(self, task_data: Dict, task_result: Dict) -> str:
        """Extract insights from a completed task"""

        insights = []

        # Extract approach information
        if task_result.get("iterations"):
            insights.append(f"Completed in {task_result['iterations']} iterations")

        if task_result.get("pull_request_url"):
            insights.append("Successfully created pull request")

        # Extract process information
        if task_data.get("description"):
            insights.append(f"Approach: {task_data['description'][:100]}...")

        return "\n".join(insights)

    async def _get_iteration_guidance(
        self, organization_id: str, iteration_count: int
    ) -> List[str]:
        """Get guidance for high iteration count situations"""

        guidance = []

        if iteration_count > 5:
            # Search for guidance on complex tasks
            complex_task_knowledge = await self.org_rag_manager.search_knowledge(
                organization_id=organization_id,
                query="complex task multiple iterations debugging",
                limit=3,
                min_similarity=0.3,
            )

            for result in complex_task_knowledge:
                if "process" in result.knowledge.knowledge_category.value:
                    guidance.append(f"Process guidance: {result.knowledge.title}")

        return guidance

    async def _get_contextual_suggestions(
        self, organization_id: str, team_id: str, current_context: Dict[str, Any]
    ) -> List[str]:
        """Get suggestions based on current execution context"""

        suggestions = []

        # Context-specific suggestions based on current state
        if current_context.get("error_count", 0) > 2:
            suggestions.append(
                "Consider reviewing error patterns in organizational knowledge"
            )

        if current_context.get("execution_time_minutes", 0) > 60:
            suggestions.append("Look for optimization guidance from team knowledge")

        return suggestions

    async def _track_enhancement_usage(self, enhanced_context: EnhancedContext):
        """Track usage of enhancement for analytics"""

        try:
            async with self.pool.acquire() as conn:
                # This would store enhancement usage data for analytics
                # Placeholder for actual implementation
                pass
        except Exception as e:
            logger.error(f"Error tracking enhancement usage: {e}")
