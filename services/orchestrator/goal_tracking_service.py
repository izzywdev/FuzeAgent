"""
Goal Tracking and Progress Monitoring Service for FuzeAgent

This service provides comprehensive tracking, monitoring, and deadline management
for organizational goals with automated progress calculations, risk assessment,
and intelligent notifications for stakeholders.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

import asyncpg

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GoalAlert:
    """Represents an alert for a goal"""

    id: str
    goal_id: str
    alert_type: str
    severity: AlertSeverity
    title: str
    description: str
    recommended_actions: List[Dict[str, Any]]
    affected_stakeholders: List[str]
    auto_generated: bool
    acknowledged: bool
    resolved: bool
    created_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]


@dataclass
class ProgressSnapshot:
    """Represents a point-in-time progress snapshot"""

    id: str
    goal_id: str
    milestone_id: Optional[str]
    recorded_at: datetime
    progress_percentage: Decimal
    current_value: Optional[Decimal]
    velocity: Optional[Decimal]  # Rate of progress
    confidence_score: Decimal
    risk_assessment: Dict[str, Any]
    performance_indicators: Dict[str, Any]
    notes: Optional[str]
    recorded_by: Optional[str]


@dataclass
class DeadlineRisk:
    """Represents deadline risk assessment"""

    goal_id: str
    risk_level: RiskLevel
    probability_of_delay: Decimal
    estimated_completion_date: date
    days_at_risk: int
    critical_path_items: List[Dict[str, Any]]
    mitigation_strategies: List[Dict[str, Any]]
    updated_at: datetime


class GoalTrackingService:
    """
    Comprehensive goal tracking and monitoring system with automated progress
    calculation, risk assessment, deadline management, and stakeholder alerts.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

        # Configuration
        self.progress_update_threshold = Decimal(
            "1.0"
        )  # Minimum change to trigger update
        self.risk_calculation_interval_hours = 6
        self.deadline_warning_days = [30, 14, 7, 3, 1]
        self.velocity_calculation_window_days = 14

        # Performance thresholds
        self.low_velocity_threshold = Decimal("0.5")  # % per day
        self.critical_confidence_threshold = Decimal("0.3")
        self.overdue_escalation_days = 7

        # Statistics
        self.progress_updates_processed = 0
        self.alerts_generated = 0
        self.risk_assessments_performed = 0
        self.deadline_warnings_sent = 0

    async def initialize(self):
        """Initialize the goal tracking service"""
        logger.info("Initializing GoalTrackingService")

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=2, max_size=8, command_timeout=60
            )

            # Schedule periodic tasks
            asyncio.create_task(self._periodic_risk_assessment())
            asyncio.create_task(self._periodic_deadline_monitoring())

            logger.info("GoalTrackingService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize GoalTrackingService: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        logger.info("GoalTrackingService closed")

    async def record_progress_update(
        self,
        goal_id: str,
        progress_percentage: Optional[Decimal] = None,
        current_value: Optional[Decimal] = None,
        milestone_id: Optional[str] = None,
        notes: Optional[str] = None,
        recorded_by: Optional[str] = None,
        confidence_score: Optional[Decimal] = None,
        trigger_alerts: bool = True,
    ) -> str:
        """Record a progress update for a goal"""

        snapshot_id = str(uuid.uuid4())

        try:
            async with self.pool.acquire() as conn:
                # Get current goal state
                current_goal = await conn.fetchrow(
                    """
                    SELECT progress_percentage, current_value, completion_confidence,
                           target_value, target_deadline, status, title
                    FROM organization_goals WHERE id = $1
                """,
                    goal_id,
                )

                if not current_goal:
                    raise ValueError(f"Goal {goal_id} not found")

                # Calculate velocity if progress_percentage provided
                velocity = None
                if progress_percentage is not None:
                    velocity = await self._calculate_velocity(
                        goal_id, progress_percentage
                    )

                # Calculate risk assessment
                risk_assessment = await self._assess_progress_risks(
                    goal_id, progress_percentage, current_value, velocity
                )

                # Generate performance indicators
                performance_indicators = await self._calculate_performance_indicators(
                    goal_id, progress_percentage, current_value
                )

                # Record progress snapshot
                await conn.execute(
                    """
                    INSERT INTO goal_progress_tracking (
                        id, goal_id, milestone_id, progress_type, progress_percentage,
                        current_value, progress_notes, recorded_by, data_source,
                        context_data
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    snapshot_id,
                    goal_id,
                    milestone_id,
                    "manual_update",
                    progress_percentage,
                    current_value,
                    notes,
                    recorded_by,
                    "tracking_service",
                    json.dumps(
                        {
                            "velocity": float(velocity) if velocity else None,
                            "risk_assessment": risk_assessment,
                            "performance_indicators": performance_indicators,
                            "confidence_score": (
                                float(confidence_score) if confidence_score else None
                            ),
                        }
                    ),
                )

                # Update goal if significant change
                if (
                    progress_percentage is not None
                    and abs(progress_percentage - current_goal["progress_percentage"])
                    >= self.progress_update_threshold
                ):
                    await conn.execute(
                        """
                        UPDATE organization_goals 
                        SET progress_percentage = $2,
                            current_value = COALESCE($3, current_value),
                            completion_confidence = COALESCE($4, completion_confidence),
                            updated_at = NOW()
                        WHERE id = $1
                    """,
                        goal_id,
                        progress_percentage,
                        current_value,
                        confidence_score,
                    )

                # Generate alerts if enabled
                if trigger_alerts:
                    await self._generate_progress_alerts(
                        goal_id, progress_percentage, risk_assessment, velocity
                    )

            self.progress_updates_processed += 1
            logger.info(
                f"Recorded progress update for goal {goal_id}: {progress_percentage}%"
            )

            return snapshot_id

        except Exception as e:
            logger.error(f"Error recording progress update for goal {goal_id}: {e}")
            raise

    async def assess_goal_deadline_risk(self, goal_id: str) -> DeadlineRisk:
        """Assess deadline risk for a specific goal"""

        try:
            async with self.pool.acquire() as conn:
                # Get goal details with progress data
                goal_data = await conn.fetchrow(
                    """
                    SELECT g.*, 
                           COUNT(m.id) as total_milestones,
                           COUNT(CASE WHEN m.status = 'completed' THEN 1 END) as completed_milestones,
                           COUNT(t.id) as total_tasks,
                           COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
                           COUNT(CASE WHEN t.due_date < CURRENT_DATE AND t.status NOT IN ('completed', 'cancelled') THEN 1 END) as overdue_tasks
                    FROM organization_goals g
                    LEFT JOIN goal_milestones m ON g.id = m.goal_id AND m.status != 'cancelled'
                    LEFT JOIN goal_tasks t ON g.id = t.goal_id AND t.status != 'cancelled'
                    WHERE g.id = $1
                    GROUP BY g.id
                """,
                    goal_id,
                )

                if not goal_data:
                    raise ValueError(f"Goal {goal_id} not found")

                # Calculate velocity and trend
                velocity = await self._calculate_velocity(
                    goal_id, goal_data["progress_percentage"]
                )

                # Calculate probability of delay
                days_remaining = (goal_data["target_deadline"] - date.today()).days
                progress_remaining = Decimal("100.0") - goal_data["progress_percentage"]

                if velocity and velocity > 0:
                    estimated_days_needed = int(progress_remaining / velocity)
                    probability_of_delay = max(
                        0,
                        min(
                            1,
                            (estimated_days_needed - days_remaining)
                            / max(days_remaining, 1),
                        ),
                    )
                else:
                    estimated_days_needed = days_remaining * 2  # Conservative estimate
                    probability_of_delay = (
                        Decimal("0.8") if days_remaining < 30 else Decimal("0.5")
                    )

                # Determine risk level
                if probability_of_delay >= Decimal("0.8") or days_remaining < 0:
                    risk_level = RiskLevel.CRITICAL
                elif probability_of_delay >= Decimal("0.6") or days_remaining < 7:
                    risk_level = RiskLevel.HIGH
                elif (
                    probability_of_delay >= Decimal("0.3")
                    or goal_data["overdue_tasks"] > 0
                ):
                    risk_level = RiskLevel.MEDIUM
                else:
                    risk_level = RiskLevel.LOW

                # Identify critical path items
                critical_path_items = await self._identify_critical_path(
                    goal_id, goal_data
                )

                # Generate mitigation strategies
                mitigation_strategies = self._generate_mitigation_strategies(
                    goal_data, risk_level, probability_of_delay, critical_path_items
                )

                # Estimated completion date
                if velocity and velocity > 0:
                    estimated_completion_date = date.today() + timedelta(
                        days=estimated_days_needed
                    )
                else:
                    estimated_completion_date = goal_data[
                        "target_deadline"
                    ] + timedelta(days=30)

                deadline_risk = DeadlineRisk(
                    goal_id=goal_id,
                    risk_level=risk_level,
                    probability_of_delay=Decimal(str(probability_of_delay)),
                    estimated_completion_date=estimated_completion_date,
                    days_at_risk=max(0, estimated_days_needed - days_remaining),
                    critical_path_items=critical_path_items,
                    mitigation_strategies=mitigation_strategies,
                    updated_at=datetime.now(),
                )

                self.risk_assessments_performed += 1

                return deadline_risk

        except Exception as e:
            logger.error(f"Error assessing deadline risk for goal {goal_id}: {e}")
            raise

    async def generate_progress_report(
        self, goal_id: str, report_period_days: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive progress report for a goal"""

        try:
            async with self.pool.acquire() as conn:
                # Get goal overview
                goal = await conn.fetchrow(
                    """
                    SELECT * FROM goal_overview WHERE id = $1
                """,
                    goal_id,
                )

                if not goal:
                    raise ValueError(f"Goal {goal_id} not found")

                # Get progress history
                progress_history = await conn.fetch(
                    """
                    SELECT * FROM goal_progress_tracking
                    WHERE goal_id = $1 
                      AND recorded_at >= NOW() - INTERVAL '%s days'
                    ORDER BY recorded_at ASC
                """,
                    goal_id,
                    report_period_days,
                )

                # Calculate metrics
                velocity = await self._calculate_velocity(
                    goal_id, goal["progress_percentage"]
                )
                deadline_risk = await self.assess_goal_deadline_risk(goal_id)

                # Performance analysis
                performance_metrics = {
                    "average_daily_progress": self._calculate_average_daily_progress(
                        progress_history
                    ),
                    "progress_consistency": self._calculate_progress_consistency(
                        progress_history
                    ),
                    "velocity_trend": self._analyze_velocity_trend(progress_history),
                    "milestone_completion_rate": goal["completed_milestones"]
                    / max(goal["total_milestones"], 1)
                    * 100,
                    "task_completion_rate": goal["completed_tasks"]
                    / max(goal["total_tasks"], 1)
                    * 100,
                }

                # Recommendations
                recommendations = self._generate_progress_recommendations(
                    goal, performance_metrics, deadline_risk
                )

                # Key insights
                insights = self._extract_progress_insights(
                    goal, progress_history, performance_metrics
                )

                return {
                    "goal_id": goal_id,
                    "goal_title": goal["title"],
                    "report_period_days": report_period_days,
                    "generated_at": datetime.now().isoformat(),
                    "current_status": {
                        "progress_percentage": float(goal["progress_percentage"]),
                        "current_value": (
                            float(goal["current_value"])
                            if goal["current_value"]
                            else None
                        ),
                        "target_value": (
                            float(goal["target_value"])
                            if goal["target_value"]
                            else None
                        ),
                        "days_remaining": goal["days_remaining"],
                        "status": goal["calculated_status"],
                    },
                    "performance_metrics": performance_metrics,
                    "deadline_risk": {
                        "risk_level": deadline_risk.risk_level.value,
                        "probability_of_delay": float(
                            deadline_risk.probability_of_delay
                        ),
                        "estimated_completion_date": deadline_risk.estimated_completion_date.isoformat(),
                        "days_at_risk": deadline_risk.days_at_risk,
                    },
                    "progress_history": [
                        {
                            "recorded_at": p["recorded_at"].isoformat(),
                            "progress_percentage": float(p["progress_percentage"]),
                            "current_value": (
                                float(p["current_value"])
                                if p["current_value"]
                                else None
                            ),
                            "notes": p["progress_notes"],
                        }
                        for p in progress_history
                    ],
                    "insights": insights,
                    "recommendations": recommendations,
                    "critical_path_items": deadline_risk.critical_path_items,
                    "mitigation_strategies": deadline_risk.mitigation_strategies,
                }

        except Exception as e:
            logger.error(f"Error generating progress report for goal {goal_id}: {e}")
            return {"error": str(e)}

    async def get_organization_tracking_dashboard(
        self, organization_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive tracking dashboard for organization goals"""

        try:
            async with self.pool.acquire() as conn:
                # Get all active goals with risk assessment
                goals_with_risk = []

                active_goals = await conn.fetch(
                    """
                    SELECT id FROM organization_goals 
                    WHERE organization_id = $1 AND status IN ('active', 'overdue')
                """,
                    organization_id,
                )

                for goal_row in active_goals:
                    goal_id = str(goal_row["id"])
                    deadline_risk = await self.assess_goal_deadline_risk(goal_id)

                    goal_data = await conn.fetchrow(
                        """
                        SELECT * FROM goal_overview WHERE id = $1
                    """,
                        goal_id,
                    )

                    goals_with_risk.append(
                        {
                            "goal": dict(goal_data),
                            "deadline_risk": {
                                "risk_level": deadline_risk.risk_level.value,
                                "probability_of_delay": float(
                                    deadline_risk.probability_of_delay
                                ),
                                "days_at_risk": deadline_risk.days_at_risk,
                            },
                        }
                    )

                # Calculate organization-level metrics
                org_metrics = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_goals,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_goals,
                        COUNT(CASE WHEN target_deadline < CURRENT_DATE AND status = 'active' THEN 1 END) as overdue_goals,
                        AVG(progress_percentage) as avg_progress,
                        AVG(completion_confidence) as avg_confidence
                    FROM organization_goals
                    WHERE organization_id = $1
                """,
                    organization_id,
                )

                # Risk distribution
                risk_distribution = {
                    "low": len(
                        [
                            g
                            for g in goals_with_risk
                            if g["deadline_risk"]["risk_level"] == "low"
                        ]
                    ),
                    "medium": len(
                        [
                            g
                            for g in goals_with_risk
                            if g["deadline_risk"]["risk_level"] == "medium"
                        ]
                    ),
                    "high": len(
                        [
                            g
                            for g in goals_with_risk
                            if g["deadline_risk"]["risk_level"] == "high"
                        ]
                    ),
                    "critical": len(
                        [
                            g
                            for g in goals_with_risk
                            if g["deadline_risk"]["risk_level"] == "critical"
                        ]
                    ),
                }

                # Upcoming deadlines
                upcoming_deadlines = await conn.fetch(
                    """
                    SELECT id, title, target_deadline, progress_percentage
                    FROM organization_goals
                    WHERE organization_id = $1 
                      AND status = 'active'
                      AND target_deadline <= CURRENT_DATE + INTERVAL '30 days'
                    ORDER BY target_deadline ASC
                    LIMIT 10
                """,
                    organization_id,
                )

                return {
                    "organization_id": organization_id,
                    "dashboard_generated_at": datetime.now().isoformat(),
                    "summary_metrics": dict(org_metrics),
                    "risk_distribution": risk_distribution,
                    "goals_with_risk_assessment": goals_with_risk,
                    "upcoming_deadlines": [dict(ud) for ud in upcoming_deadlines],
                    "high_priority_alerts": len(
                        [
                            g
                            for g in goals_with_risk
                            if g["deadline_risk"]["risk_level"] in ["high", "critical"]
                        ]
                    ),
                }

        except Exception as e:
            logger.error(
                f"Error generating tracking dashboard for organization {organization_id}: {e}"
            )
            return {"error": str(e)}

    # Helper methods for calculations and analysis

    async def _calculate_velocity(
        self, goal_id: str, current_progress: Decimal
    ) -> Optional[Decimal]:
        """Calculate progress velocity (progress per day)"""

        try:
            async with self.pool.acquire() as conn:
                # Get progress data from the last window period
                progress_data = await conn.fetch(
                    """
                    SELECT progress_percentage, recorded_at
                    FROM goal_progress_tracking
                    WHERE goal_id = $1 
                      AND recorded_at >= NOW() - INTERVAL '%s days'
                    ORDER BY recorded_at ASC
                """,
                    goal_id,
                    self.velocity_calculation_window_days,
                )

                if len(progress_data) < 2:
                    return None

                # Calculate velocity using linear regression or simple difference
                first_point = progress_data[0]
                last_point = progress_data[-1]

                time_diff = (
                    last_point["recorded_at"] - first_point["recorded_at"]
                ).days
                if time_diff <= 0:
                    return None

                progress_diff = (
                    last_point["progress_percentage"]
                    - first_point["progress_percentage"]
                )
                velocity = progress_diff / time_diff

                return max(Decimal("0"), velocity)

        except Exception as e:
            logger.error(f"Error calculating velocity for goal {goal_id}: {e}")
            return None

    async def _assess_progress_risks(
        self,
        goal_id: str,
        progress_percentage: Optional[Decimal],
        current_value: Optional[Decimal],
        velocity: Optional[Decimal],
    ) -> Dict[str, Any]:
        """Assess various risks based on current progress"""

        risks = {
            "velocity_risk": "low",
            "deadline_risk": "low",
            "confidence_risk": "low",
            "overall_risk_score": 0.2,
        }

        try:
            # Velocity risk assessment
            if velocity is not None:
                if velocity < self.low_velocity_threshold:
                    risks["velocity_risk"] = "high"
                    risks["overall_risk_score"] += 0.3
                elif velocity < self.low_velocity_threshold * 2:
                    risks["velocity_risk"] = "medium"
                    risks["overall_risk_score"] += 0.15

            # Add more risk assessments here...

        except Exception as e:
            logger.error(f"Error assessing progress risks for goal {goal_id}: {e}")

        return risks

    async def _calculate_performance_indicators(
        self,
        goal_id: str,
        progress_percentage: Optional[Decimal],
        current_value: Optional[Decimal],
    ) -> Dict[str, Any]:
        """Calculate performance indicators"""

        return {
            "progress_health": (
                "good"
                if progress_percentage and progress_percentage > 50
                else "needs_attention"
            ),
            "completion_likelihood": (
                "high"
                if progress_percentage and progress_percentage > 75
                else "moderate"
            ),
            "resource_efficiency": "optimal",  # Would be calculated based on actual metrics
        }

    async def _generate_progress_alerts(
        self,
        goal_id: str,
        progress_percentage: Optional[Decimal],
        risk_assessment: Dict[str, Any],
        velocity: Optional[Decimal],
    ):
        """Generate appropriate alerts based on progress and risk"""

        alerts_to_create = []

        # Low velocity alert
        if velocity and velocity < self.low_velocity_threshold:
            alerts_to_create.append(
                {
                    "alert_type": "low_velocity",
                    "severity": AlertSeverity.WARNING,
                    "title": "Low Progress Velocity Detected",
                    "description": f"Goal progress velocity ({velocity:.2f}% per day) is below the recommended threshold",
                }
            )

        # High risk alert
        if risk_assessment.get("overall_risk_score", 0) > 0.7:
            alerts_to_create.append(
                {
                    "alert_type": "high_risk",
                    "severity": AlertSeverity.CRITICAL,
                    "title": "High Risk Goal Requires Attention",
                    "description": "Multiple risk factors detected that may impact goal completion",
                }
            )

        # Create alerts in database (implementation would go here)
        for alert_data in alerts_to_create:
            self.alerts_generated += 1
            # Would create actual database records

    async def _identify_critical_path(
        self, goal_id: str, goal_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify critical path items that could impact goal completion"""

        try:
            async with self.pool.acquire() as conn:
                # Get overdue tasks
                overdue_tasks = await conn.fetch(
                    """
                    SELECT id, title, due_date, assigned_agent_id, estimated_hours
                    FROM goal_tasks
                    WHERE goal_id = $1 
                      AND due_date < CURRENT_DATE 
                      AND status NOT IN ('completed', 'cancelled')
                    ORDER BY due_date ASC
                    LIMIT 5
                """,
                    goal_id,
                )

                # Get pending milestones with upcoming deadlines
                critical_milestones = await conn.fetch(
                    """
                    SELECT id, title, target_date, responsible_agent_id
                    FROM goal_milestones
                    WHERE goal_id = $1 
                      AND target_date <= CURRENT_DATE + INTERVAL '14 days'
                      AND status IN ('planned', 'in_progress')
                    ORDER BY target_date ASC
                    LIMIT 5
                """,
                    goal_id,
                )

                critical_items = []

                for task in overdue_tasks:
                    critical_items.append(
                        {
                            "type": "overdue_task",
                            "id": str(task["id"]),
                            "title": task["title"],
                            "due_date": task["due_date"].isoformat(),
                            "impact": "high",
                        }
                    )

                for milestone in critical_milestones:
                    critical_items.append(
                        {
                            "type": "critical_milestone",
                            "id": str(milestone["id"]),
                            "title": milestone["title"],
                            "target_date": milestone["target_date"].isoformat(),
                            "impact": "high",
                        }
                    )

                return critical_items

        except Exception as e:
            logger.error(f"Error identifying critical path for goal {goal_id}: {e}")
            return []

    def _generate_mitigation_strategies(
        self,
        goal_data: Dict[str, Any],
        risk_level: RiskLevel,
        probability_of_delay: Decimal,
        critical_path_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate mitigation strategies based on risk assessment"""

        strategies = []

        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            strategies.append(
                {
                    "strategy": "resource_reallocation",
                    "description": "Consider reallocating resources from lower priority initiatives",
                    "priority": "high",
                    "estimated_impact": "medium",
                }
            )

            strategies.append(
                {
                    "strategy": "scope_adjustment",
                    "description": "Review goal scope and consider focusing on highest value deliverables",
                    "priority": "high",
                    "estimated_impact": "high",
                }
            )

        if len(critical_path_items) > 0:
            strategies.append(
                {
                    "strategy": "critical_path_focus",
                    "description": f"Prioritize {len(critical_path_items)} critical path items requiring immediate attention",
                    "priority": "urgent",
                    "estimated_impact": "high",
                }
            )

        if probability_of_delay > Decimal("0.6"):
            strategies.append(
                {
                    "strategy": "timeline_negotiation",
                    "description": "Consider negotiating deadline extension with stakeholders",
                    "priority": "medium",
                    "estimated_impact": "medium",
                }
            )

        return strategies

    # Periodic monitoring tasks

    async def _periodic_risk_assessment(self):
        """Periodic risk assessment for all active goals"""
        while True:
            try:
                await asyncio.sleep(self.risk_calculation_interval_hours * 3600)

                async with self.pool.acquire() as conn:
                    active_goals = await conn.fetch("""
                        SELECT id FROM organization_goals 
                        WHERE status IN ('active', 'overdue')
                    """)

                    for goal in active_goals:
                        try:
                            await self.assess_goal_deadline_risk(str(goal["id"]))
                        except Exception as e:
                            logger.error(
                                f"Error in periodic risk assessment for goal {goal['id']}: {e}"
                            )

                logger.info(
                    f"Completed periodic risk assessment for {len(active_goals)} goals"
                )

            except Exception as e:
                logger.error(f"Error in periodic risk assessment: {e}")

    async def _periodic_deadline_monitoring(self):
        """Periodic deadline monitoring and alerts"""
        while True:
            try:
                await asyncio.sleep(24 * 3600)  # Run daily

                async with self.pool.acquire() as conn:
                    # Check for goals approaching deadlines
                    for warning_days in self.deadline_warning_days:
                        approaching_goals = await conn.fetch(
                            """
                            SELECT id, title, target_deadline, progress_percentage
                            FROM organization_goals
                            WHERE status = 'active'
                              AND target_deadline = CURRENT_DATE + INTERVAL '%s days'
                              AND progress_percentage < 90
                        """,
                            warning_days,
                        )

                        for goal in approaching_goals:
                            # Generate deadline warning alert
                            self.deadline_warnings_sent += 1
                            logger.warning(
                                f"Deadline warning: Goal {goal['title']} due in {warning_days} days, "
                                f"progress: {goal['progress_percentage']}%"
                            )

            except Exception as e:
                logger.error(f"Error in periodic deadline monitoring: {e}")

    # Additional helper methods for report generation

    def _calculate_average_daily_progress(
        self, progress_history: List[Dict[str, Any]]
    ) -> float:
        """Calculate average daily progress from history"""
        if len(progress_history) < 2:
            return 0.0

        total_days = (
            progress_history[-1]["recorded_at"] - progress_history[0]["recorded_at"]
        ).days
        if total_days <= 0:
            return 0.0

        progress_change = (
            progress_history[-1]["progress_percentage"]
            - progress_history[0]["progress_percentage"]
        )
        return float(progress_change / total_days)

    def _calculate_progress_consistency(
        self, progress_history: List[Dict[str, Any]]
    ) -> str:
        """Calculate progress consistency rating"""
        if len(progress_history) < 3:
            return "insufficient_data"

        # Calculate variance in daily progress
        daily_changes = []
        for i in range(1, len(progress_history)):
            prev = progress_history[i - 1]
            curr = progress_history[i]
            days_diff = (curr["recorded_at"] - prev["recorded_at"]).days or 1
            daily_change = (
                curr["progress_percentage"] - prev["progress_percentage"]
            ) / days_diff
            daily_changes.append(daily_change)

        if not daily_changes:
            return "insufficient_data"

        avg_change = sum(daily_changes) / len(daily_changes)
        variance = sum((x - avg_change) ** 2 for x in daily_changes) / len(
            daily_changes
        )

        if variance < 1.0:
            return "very_consistent"
        elif variance < 4.0:
            return "consistent"
        elif variance < 9.0:
            return "somewhat_consistent"
        else:
            return "inconsistent"

    def _analyze_velocity_trend(self, progress_history: List[Dict[str, Any]]) -> str:
        """Analyze velocity trend direction"""
        if len(progress_history) < 4:
            return "insufficient_data"

        # Split history into two halves and compare average velocity
        mid_point = len(progress_history) // 2
        first_half = progress_history[: mid_point + 1]
        second_half = progress_history[mid_point:]

        def calc_velocity(segment):
            if len(segment) < 2:
                return 0
            days = (segment[-1]["recorded_at"] - segment[0]["recorded_at"]).days or 1
            progress = (
                segment[-1]["progress_percentage"] - segment[0]["progress_percentage"]
            )
            return progress / days

        first_velocity = calc_velocity(first_half)
        second_velocity = calc_velocity(second_half)

        if second_velocity > first_velocity * 1.2:
            return "accelerating"
        elif second_velocity < first_velocity * 0.8:
            return "decelerating"
        else:
            return "stable"

    def _generate_progress_recommendations(
        self,
        goal: Dict[str, Any],
        performance_metrics: Dict[str, Any],
        deadline_risk: DeadlineRisk,
    ) -> List[str]:
        """Generate actionable recommendations based on progress analysis"""

        recommendations = []

        if deadline_risk.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.append(
                "URGENT: Goal is at high risk of missing deadline. Consider immediate intervention."
            )

        if performance_metrics["progress_consistency"] == "inconsistent":
            recommendations.append(
                "Improve progress consistency by establishing regular check-ins and milestone reviews."
            )

        if performance_metrics["velocity_trend"] == "decelerating":
            recommendations.append(
                "Progress velocity is declining. Investigate blockers and resource constraints."
            )

        if goal["completed_tasks"] / max(goal["total_tasks"], 1) < 0.5:
            recommendations.append(
                "Focus on task completion rate. Many tasks remain incomplete."
            )

        return recommendations

    def _extract_progress_insights(
        self,
        goal: Dict[str, Any],
        progress_history: List[Dict[str, Any]],
        performance_metrics: Dict[str, Any],
    ) -> List[str]:
        """Extract key insights from progress data"""

        insights = []

        if len(progress_history) > 0:
            latest_progress = progress_history[-1]
            insights.append(
                f"Latest progress update: {latest_progress['progress_percentage']}% on {latest_progress['recorded_at'].strftime('%Y-%m-%d')}"
            )

        if performance_metrics["average_daily_progress"] > 0:
            days_to_completion = (
                100 - float(goal["progress_percentage"])
            ) / performance_metrics["average_daily_progress"]
            insights.append(
                f"At current pace, goal completion estimated in {int(days_to_completion)} days"
            )

        if goal["days_remaining"] is not None:
            if goal["days_remaining"] < 0:
                insights.append(f"Goal is {abs(goal['days_remaining'])} days overdue")
            elif goal["days_remaining"] < 30:
                insights.append(
                    f"Goal deadline approaching in {goal['days_remaining']} days"
                )

        return insights
