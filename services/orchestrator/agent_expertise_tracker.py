"""
Agent Expertise Tracker

Provides analytics and insights into agent performance, learning patterns,
and expertise development across the FuzeAgent system.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .database import get_db_connection

logger = logging.getLogger(__name__)


@dataclass
class ExpertiseInsight:
    """Insight about agent expertise development"""

    agent_id: str
    skill_area: str
    insight_type: str  # 'improving', 'declining', 'plateau', 'breakthrough'
    description: str
    confidence: float
    evidence: Dict[str, Any]
    timestamp: datetime


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for an agent"""

    agent_id: str
    total_tasks: int
    success_rate: float
    avg_expertise_level: float
    improving_skills_count: int
    declining_skills_count: int
    memory_usage_stats: Dict[str, Any]
    recent_performance_trend: str
    top_skill_areas: List[Dict[str, Any]]


class AgentExpertiseTracker:
    """
    Tracks and analyzes agent expertise development, providing insights
    into learning patterns, performance trends, and optimization opportunities.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.insights_cache: Dict[str, List[ExpertiseInsight]] = {}
        self.metrics_cache: Dict[str, AgentPerformanceMetrics] = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_cache_update = {}

    async def get_agent_performance_metrics(
        self, agent_id: str
    ) -> Optional[AgentPerformanceMetrics]:
        """Get comprehensive performance metrics for an agent"""

        # Check cache first
        if (
            agent_id in self.metrics_cache
            and agent_id in self.last_cache_update
            and (datetime.now() - self.last_cache_update[agent_id]).total_seconds()
            < self.cache_ttl
        ):
            return self.metrics_cache[agent_id]

        try:
            async with get_db_connection() as conn:
                # Get basic performance stats
                basic_stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(DISTINCT am.task_id) as total_tasks,
                        AVG(CASE WHEN am.memory_type = 'success' THEN 1.0 ELSE 0.0 END) as success_rate,
                        COUNT(DISTINCT am.id) as total_memories
                    FROM agent_memory am
                    WHERE am.agent_id = $1
                """,
                    agent_id,
                )

                # Get expertise summary
                expertise_stats = await conn.fetchrow(
                    """
                    SELECT 
                        AVG(expertise_level) as avg_expertise_level,
                        COUNT(CASE WHEN performance_trend = 'improving' THEN 1 END) as improving_skills,
                        COUNT(CASE WHEN performance_trend = 'declining' THEN 1 END) as declining_skills
                    FROM agent_expertise
                    WHERE agent_id = $1
                """,
                    agent_id,
                )

                # Get memory usage statistics
                memory_stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_memories,
                        AVG(confidence_score) as avg_confidence,
                        SUM(usage_count) as total_usage,
                        COUNT(DISTINCT memory_type) as memory_types_used
                    FROM agent_memory
                    WHERE agent_id = $1
                """,
                    agent_id,
                )

                # Get top skill areas
                top_skills = await conn.fetch(
                    """
                    SELECT skill_area, expertise_level, success_rate, task_count, performance_trend
                    FROM agent_expertise
                    WHERE agent_id = $1
                    ORDER BY expertise_level DESC, success_rate DESC
                    LIMIT 5
                """,
                    agent_id,
                )

                # Determine recent performance trend
                recent_trend = await self._calculate_recent_trend(agent_id, conn)

                # Build metrics object
                metrics = AgentPerformanceMetrics(
                    agent_id=agent_id,
                    total_tasks=basic_stats["total_tasks"] or 0,
                    success_rate=basic_stats["success_rate"] or 0.0,
                    avg_expertise_level=expertise_stats["avg_expertise_level"] or 0.0,
                    improving_skills_count=expertise_stats["improving_skills"] or 0,
                    declining_skills_count=expertise_stats["declining_skills"] or 0,
                    memory_usage_stats={
                        "total_memories": memory_stats["total_memories"] or 0,
                        "avg_confidence": float(memory_stats["avg_confidence"])
                        if memory_stats["avg_confidence"]
                        else 0.0,
                        "total_usage": memory_stats["total_usage"] or 0,
                        "memory_types_used": memory_stats["memory_types_used"] or 0,
                    },
                    recent_performance_trend=recent_trend,
                    top_skill_areas=[dict(skill) for skill in top_skills],
                )

                # Cache the result
                self.metrics_cache[agent_id] = metrics
                self.last_cache_update[agent_id] = datetime.now()

                return metrics

        except Exception as e:
            logger.error(f"Error getting performance metrics for agent {agent_id}: {e}")
            return None

    async def generate_expertise_insights(
        self, agent_id: str
    ) -> List[ExpertiseInsight]:
        """Generate insights about agent expertise development"""

        # Check cache first
        if (
            agent_id in self.insights_cache
            and agent_id in self.last_cache_update
            and (datetime.now() - self.last_cache_update[agent_id]).total_seconds()
            < self.cache_ttl
        ):
            return self.insights_cache[agent_id]

        insights = []

        try:
            async with get_db_connection() as conn:
                # Analyze learning velocity patterns
                learning_insights = await self._analyze_learning_velocity(
                    agent_id, conn
                )
                insights.extend(learning_insights)

                # Analyze skill development patterns
                skill_insights = await self._analyze_skill_development(agent_id, conn)
                insights.extend(skill_insights)

                # Analyze memory usage patterns
                memory_insights = await self._analyze_memory_patterns(agent_id, conn)
                insights.extend(memory_insights)

                # Cache the results
                self.insights_cache[agent_id] = insights
                self.last_cache_update[agent_id] = datetime.now()

        except Exception as e:
            logger.error(f"Error generating insights for agent {agent_id}: {e}")

        return insights

    async def get_system_wide_expertise_summary(self) -> Dict[str, Any]:
        """Get system-wide expertise and performance summary"""

        try:
            async with get_db_connection() as conn:
                # Overall system stats
                system_stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(DISTINCT a.id) as total_agents,
                        COUNT(DISTINCT ae.skill_area) as total_skill_areas,
                        AVG(ae.expertise_level) as avg_system_expertise,
                        COUNT(CASE WHEN ae.performance_trend = 'improving' THEN 1 END) as improving_agents,
                        COUNT(CASE WHEN ae.performance_trend = 'declining' THEN 1 END) as declining_agents
                    FROM agents a
                    LEFT JOIN agent_expertise ae ON a.id = ae.agent_id
                """
                )

                # Memory system stats
                memory_stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_memories,
                        AVG(confidence_score) as avg_confidence,
                        SUM(usage_count) as total_usage,
                        COUNT(DISTINCT agent_id) as agents_with_memory
                    FROM agent_memory
                """
                )

                # Top performing skill areas
                top_skill_areas = await conn.fetch(
                    """
                    SELECT 
                        skill_area,
                        COUNT(*) as agent_count,
                        AVG(expertise_level) as avg_expertise,
                        AVG(success_rate) as avg_success_rate
                    FROM agent_expertise
                    GROUP BY skill_area
                    ORDER BY avg_expertise DESC, avg_success_rate DESC
                    LIMIT 10
                """
                )

                # Recent activity
                recent_activity = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN 1 END) as memories_24h,
                        COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as memories_7d,
                        COUNT(DISTINCT CASE WHEN created_at > NOW() - INTERVAL '24 hours' THEN agent_id END) as active_agents_24h
                    FROM agent_memory
                """
                )

                return {
                    "system_stats": dict(system_stats) if system_stats else {},
                    "memory_stats": dict(memory_stats) if memory_stats else {},
                    "top_skill_areas": [dict(skill) for skill in top_skill_areas],
                    "recent_activity": dict(recent_activity) if recent_activity else {},
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error getting system-wide expertise summary: {e}")
            return {"error": str(e)}

    async def _calculate_recent_trend(self, agent_id: str, conn) -> str:
        """Calculate recent performance trend for an agent"""

        try:
            # Get recent task outcomes
            recent_outcomes = await conn.fetch(
                """
                SELECT 
                    DATE_TRUNC('day', created_at) as date,
                    AVG(CASE WHEN memory_type = 'success' THEN 1.0 ELSE 0.0 END) as daily_success_rate
                FROM agent_memory
                WHERE agent_id = $1 
                    AND created_at > NOW() - INTERVAL '14 days'
                    AND memory_type IN ('success', 'task_outcome')
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY date DESC
                LIMIT 7
            """,
                agent_id,
            )

            if len(recent_outcomes) < 3:
                return "insufficient_data"

            # Calculate trend
            success_rates = [
                float(row["daily_success_rate"]) for row in recent_outcomes
            ]

            # Simple linear trend calculation
            if len(success_rates) >= 3:
                early_avg = sum(success_rates[-3:]) / 3
                recent_avg = sum(success_rates[:3]) / 3

                if recent_avg > early_avg + 0.1:
                    return "improving"
                elif recent_avg < early_avg - 0.1:
                    return "declining"
                else:
                    return "stable"

            return "stable"

        except Exception as e:
            logger.error(f"Error calculating recent trend: {e}")
            return "unknown"

    async def _analyze_learning_velocity(
        self, agent_id: str, conn
    ) -> List[ExpertiseInsight]:
        """Analyze learning velocity patterns"""

        insights = []

        try:
            # Get skills with high learning velocity
            fast_learners = await conn.fetch(
                """
                SELECT skill_area, learning_velocity, expertise_level, task_count
                FROM agent_expertise
                WHERE agent_id = $1 AND learning_velocity > 0.1
                ORDER BY learning_velocity DESC
            """,
                agent_id,
            )

            for skill in fast_learners:
                insights.append(
                    ExpertiseInsight(
                        agent_id=agent_id,
                        skill_area=skill["skill_area"],
                        insight_type="improving",
                        description=f"Rapid improvement in {skill['skill_area']} with velocity {skill['learning_velocity']:.2f}",
                        confidence=0.8,
                        evidence={
                            "learning_velocity": float(skill["learning_velocity"]),
                            "expertise_level": float(skill["expertise_level"]),
                            "task_count": skill["task_count"],
                        },
                        timestamp=datetime.now(),
                    )
                )

            # Get skills with declining performance
            declining_skills = await conn.fetch(
                """
                SELECT skill_area, learning_velocity, expertise_level, task_count
                FROM agent_expertise
                WHERE agent_id = $1 AND learning_velocity < -0.05
                ORDER BY learning_velocity ASC
            """,
                agent_id,
            )

            for skill in declining_skills:
                insights.append(
                    ExpertiseInsight(
                        agent_id=agent_id,
                        skill_area=skill["skill_area"],
                        insight_type="declining",
                        description=f"Performance decline in {skill['skill_area']} - may need attention",
                        confidence=0.7,
                        evidence={
                            "learning_velocity": float(skill["learning_velocity"]),
                            "expertise_level": float(skill["expertise_level"]),
                            "task_count": skill["task_count"],
                        },
                        timestamp=datetime.now(),
                    )
                )

        except Exception as e:
            logger.error(f"Error analyzing learning velocity: {e}")

        return insights

    async def _analyze_skill_development(
        self, agent_id: str, conn
    ) -> List[ExpertiseInsight]:
        """Analyze skill development patterns"""

        insights = []

        try:
            # Find breakthrough moments (significant expertise jumps)
            breakthroughs = await conn.fetch(
                """
                SELECT skill_area, expertise_level, success_rate, task_count
                FROM agent_expertise
                WHERE agent_id = $1 
                    AND expertise_level > 0.7 
                    AND success_rate > 0.8
                    AND task_count >= 5
            """,
                agent_id,
            )

            for breakthrough in breakthroughs:
                insights.append(
                    ExpertiseInsight(
                        agent_id=agent_id,
                        skill_area=breakthrough["skill_area"],
                        insight_type="breakthrough",
                        description=f"Expert level achieved in {breakthrough['skill_area']} with {breakthrough['success_rate']:.1%} success rate",
                        confidence=0.9,
                        evidence={
                            "expertise_level": float(breakthrough["expertise_level"]),
                            "success_rate": float(breakthrough["success_rate"]),
                            "task_count": breakthrough["task_count"],
                        },
                        timestamp=datetime.now(),
                    )
                )

            # Find plateau situations (high task count but low expertise)
            plateaus = await conn.fetch(
                """
                SELECT skill_area, expertise_level, success_rate, task_count
                FROM agent_expertise
                WHERE agent_id = $1 
                    AND task_count > 10 
                    AND expertise_level < 0.4
                    AND learning_velocity BETWEEN -0.02 AND 0.02
            """,
                agent_id,
            )

            for plateau in plateaus:
                insights.append(
                    ExpertiseInsight(
                        agent_id=agent_id,
                        skill_area=plateau["skill_area"],
                        insight_type="plateau",
                        description=f"Learning plateau in {plateau['skill_area']} - consider new approaches",
                        confidence=0.6,
                        evidence={
                            "expertise_level": float(plateau["expertise_level"]),
                            "success_rate": float(plateau["success_rate"]),
                            "task_count": plateau["task_count"],
                        },
                        timestamp=datetime.now(),
                    )
                )

        except Exception as e:
            logger.error(f"Error analyzing skill development: {e}")

        return insights

    async def _analyze_memory_patterns(
        self, agent_id: str, conn
    ) -> List[ExpertiseInsight]:
        """Analyze memory usage and effectiveness patterns"""

        insights = []

        try:
            # Analyze memory types and their effectiveness
            memory_effectiveness = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_memories,
                    AVG(usage_count) as avg_usage,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(CASE WHEN usage_count > 5 THEN 1 END) as high_usage_memories
                FROM agent_memory
                WHERE agent_id = $1
            """,
                agent_id,
            )

            if memory_effectiveness and memory_effectiveness["total_memories"] > 50:
                high_usage_ratio = (
                    memory_effectiveness["high_usage_memories"]
                    / memory_effectiveness["total_memories"]
                )

                if (
                    high_usage_ratio > 0.2
                ):  # More than 20% of memories are highly reused
                    insights.append(
                        ExpertiseInsight(
                            agent_id=agent_id,
                            skill_area="memory_management",
                            insight_type="improving",
                            description=f"Excellent memory reuse patterns - {high_usage_ratio:.1%} of memories are frequently accessed",
                            confidence=0.8,
                            evidence={
                                "total_memories": memory_effectiveness[
                                    "total_memories"
                                ],
                                "high_usage_ratio": high_usage_ratio,
                                "avg_confidence": float(
                                    memory_effectiveness["avg_confidence"]
                                ),
                            },
                            timestamp=datetime.now(),
                        )
                    )

        except Exception as e:
            logger.error(f"Error analyzing memory patterns: {e}")

        return insights

    async def clear_cache(self, agent_id: Optional[str] = None):
        """Clear analytics cache"""
        if agent_id:
            self.insights_cache.pop(agent_id, None)
            self.metrics_cache.pop(agent_id, None)
            self.last_cache_update.pop(agent_id, None)
        else:
            self.insights_cache.clear()
            self.metrics_cache.clear()
            self.last_cache_update.clear()
