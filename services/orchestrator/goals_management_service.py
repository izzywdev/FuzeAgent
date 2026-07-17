# fmt: off
"""
Goals Management Service for FuzeAgent

This service manages organizational goals, milestones, tasks, and conversations.
Provides a complete goal lifecycle from creation through completion with 
AI-powered planning and milestone generation.
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


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class GoalType(str, Enum):
    BUSINESS = "business"
    TECHNICAL = "technical"
    GROWTH = "growth"
    OPERATIONAL = "operational"


class MilestoneStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class OrganizationGoal:
    """Represents an organizational goal"""

    id: str
    organization_id: str
    title: str
    description: str
    goal_type: GoalType
    priority_level: int
    target_value: Optional[Decimal]
    target_unit: Optional[str]
    current_value: Optional[Decimal]
    success_criteria: Dict[str, Any]
    start_date: date
    target_deadline: date
    actual_completion_date: Optional[date]
    status: GoalStatus
    progress_percentage: Decimal
    completion_confidence: Decimal
    assigned_teams: List[str]
    goal_owner_agent_id: Optional[str]
    stakeholder_agents: List[str]
    tags: List[str]
    metadata: Dict[str, Any]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class GoalMilestone:
    """Represents a milestone within a goal"""

    id: str
    goal_id: str
    parent_milestone_id: Optional[str]
    title: str
    description: str
    milestone_type: str
    target_date: date
    actual_completion_date: Optional[date]
    success_criteria: Dict[str, Any]
    deliverables: List[Dict[str, Any]]
    dependencies: List[Dict[str, Any]]
    status: MilestoneStatus
    progress_percentage: Decimal
    completion_confidence: Decimal
    assigned_teams: List[str]
    responsible_agent_id: Optional[str]
    supporting_agents: List[str]
    priority_level: int
    weight_in_goal: Decimal
    tags: List[str]
    metadata: Dict[str, Any]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class GoalTask:
    """Represents a specific task derived from a milestone"""

    id: str
    goal_id: str
    milestone_id: Optional[str]
    parent_task_id: Optional[str]
    title: str
    description: str
    task_type: str
    complexity_level: str
    assigned_team_id: Optional[str]
    assigned_agent_id: Optional[str]
    created_by_agent_id: Optional[str]
    estimated_hours: Optional[Decimal]
    due_date: Optional[date]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    status: TaskStatus
    priority: int
    dependencies: List[Dict[str, Any]]
    blockers: List[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    quality_score: Optional[Decimal]
    effort_actual_hours: Optional[Decimal]
    requirements: Dict[str, Any]
    acceptance_criteria: List[Dict[str, Any]]
    technical_specifications: Dict[str, Any]
    tags: List[str]
    labels: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class GoalConversation:
    """Represents an AI-powered conversation about a goal"""

    id: str
    goal_id: str
    conversation_type: str
    conversation_title: str
    conversation_summary: Optional[str]
    conversation_context: Dict[str, Any]
    participants: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    insights_generated: List[Dict[str, Any]]
    action_items: List[Dict[str, Any]]
    status: str
    last_activity_at: datetime
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime


class GoalsManagementService:
    """
    Comprehensive goals management system with AI-powered planning,
    milestone generation, and task derivation capabilities.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

        # Configuration
        self.default_milestone_weight = Decimal("10.0")
        self.default_task_priority = 5
        self.progress_calculation_precision = 2

        # Statistics
        self.goals_created = 0
        self.milestones_generated = 0
        self.tasks_created = 0
        self.conversations_initiated = 0

    async def initialize(self):
        """Initialize the goals management service"""
        logger.info("Initializing GoalsManagementService")

        try:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=2, max_size=10, command_timeout=60
            )

            logger.info("GoalsManagementService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize GoalsManagementService: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        logger.info("GoalsManagementService closed")

    async def create_goal(
        self,
        organization_id: str,
        title: str,
        description: str,
        goal_type: GoalType,
        target_value: Optional[Decimal] = None,
        target_unit: Optional[str] = None,
        target_deadline: Optional[date] = None,
        priority_level: int = 5,
        success_criteria: Optional[Dict[str, Any]] = None,
        assigned_teams: Optional[List[str]] = None,
        goal_owner_agent_id: Optional[str] = None,
        stakeholder_agents: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> str:
        """Create a new organizational goal"""

        goal_id = str(uuid.uuid4())

        # Set defaults
        if target_deadline is None:
            target_deadline = date.today() + timedelta(days=90)  # 3 months default
        if success_criteria is None:
            success_criteria = {}
        if assigned_teams is None:
            assigned_teams = []
        if stakeholder_agents is None:
            stakeholder_agents = []
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO organization_goals (
                        id, organization_id, title, description, goal_type,
                        priority_level, target_value, target_unit, success_criteria,
                        target_deadline, status, assigned_teams, goal_owner_agent_id,
                        stakeholder_agents, tags, metadata, created_by
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
                    )
                """,
                    goal_id,
                    organization_id,
                    title,
                    description,
                    goal_type.value,
                    priority_level,
                    target_value,
                    target_unit,
                    json.dumps(success_criteria),
                    target_deadline,
                    GoalStatus.ACTIVE.value,
                    assigned_teams,
                    goal_owner_agent_id,
                    stakeholder_agents,
                    tags,
                    json.dumps(metadata),
                    created_by,
                )

                # Create initial metrics if target_value is provided
                if target_value is not None and target_unit is not None:
                    await conn.execute(
                        """
                        INSERT INTO goal_metrics (
                            goal_id, metric_name, metric_type, metric_unit,
                            current_value, target_value, baseline_value
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        goal_id,
                        f"Primary {target_unit} Target",
                        self._determine_metric_type(target_unit),
                        target_unit,
                        Decimal("0"),
                        target_value,
                        Decimal("0"),
                    )

                # Create initial progress tracking entry
                await conn.execute(
                    """
                    INSERT INTO goal_progress_tracking (
                        goal_id, progress_type, progress_percentage, 
                        progress_notes, recorded_by, data_source
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    goal_id,
                    "goal_created",
                    Decimal("0"),
                    f"Goal created: {title}",
                    created_by,
                    "system",
                )

            self.goals_created += 1
            logger.info(f"Created goal {goal_id}: {title}")

            return goal_id

        except Exception as e:
            logger.error(f"Error creating goal: {e}")
            raise

    async def get_goal(self, goal_id: str) -> Optional[OrganizationGoal]:
        """Get a goal by ID"""

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT * FROM organization_goals WHERE id = $1
                """,
                    goal_id,
                )

                if not row:
                    return None

                return self._row_to_goal(row)

        except Exception as e:
            logger.error(f"Error getting goal {goal_id}: {e}")
            return None

    async def list_organization_goals(
        self,
        organization_id: str,
        status_filter: Optional[List[GoalStatus]] = None,
        goal_type_filter: Optional[List[GoalType]] = None,
        limit: int = 50,
    ) -> List[OrganizationGoal]:
        """List goals for an organization with optional filtering"""

        try:
            async with self.pool.acquire() as conn:
                where_conditions = ["organization_id = $1"]
                params = [organization_id]
                param_idx = 2

                if status_filter:
                    where_conditions.append(f"status = ANY(${param_idx})")
                    params.append([s.value for s in status_filter])
                    param_idx += 1

                if goal_type_filter:
                    where_conditions.append(f"goal_type = ANY(${param_idx})")
                    params.append([gt.value for gt in goal_type_filter])
                    param_idx += 1

                where_clause = " AND ".join(where_conditions)

                rows = await conn.fetch(
                    f"""
                    SELECT * FROM organization_goals 
                    WHERE {where_clause}
                    ORDER BY priority_level DESC, created_at DESC
                    LIMIT ${param_idx}
                """,
                    *params,
                    limit,
                )

                return [self._row_to_goal(row) for row in rows]

        except Exception as e:
            logger.error(f"Error listing goals for organization {organization_id}: {e}")
            return []

    async def update_goal_progress(
        self,
        goal_id: str,
        progress_percentage: Optional[Decimal] = None,
        current_value: Optional[Decimal] = None,
        completion_confidence: Optional[Decimal] = None,
        progress_notes: Optional[str] = None,
        recorded_by: Optional[str] = None,
    ) -> bool:
        """Update goal progress and record tracking entry"""

        try:
            async with self.pool.acquire() as conn:
                # Build update query dynamically
                update_fields = []
                params = [goal_id]
                param_idx = 2

                if progress_percentage is not None:
                    update_fields.append(f"progress_percentage = ${param_idx}")
                    params.append(progress_percentage)
                    param_idx += 1

                if current_value is not None:
                    update_fields.append(f"current_value = ${param_idx}")
                    params.append(current_value)
                    param_idx += 1

                if completion_confidence is not None:
                    update_fields.append(f"completion_confidence = ${param_idx}")
                    params.append(completion_confidence)
                    param_idx += 1

                if update_fields:
                    update_fields.append("updated_at = NOW()")
                    await conn.execute(
                        f"""
                        UPDATE organization_goals 
                        SET {', '.join(update_fields)}
                        WHERE id = $1
                    """,
                        *params,
                    )

                    # Record progress tracking entry
                    await conn.execute(
                        """
                        INSERT INTO goal_progress_tracking (
                            goal_id, progress_type, progress_percentage, current_value,
                            progress_notes, recorded_by, data_source
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        goal_id,
                        "manual_update",
                        progress_percentage,
                        current_value,
                        progress_notes or "Progress updated manually",
                        recorded_by,
                        "manual",
                    )

                    return True

                return False

        except Exception as e:
            logger.error(f"Error updating goal progress for {goal_id}: {e}")
            return False

    async def create_milestone(
        self,
        goal_id: str,
        title: str,
        description: str,
        target_date: date,
        milestone_type: str = "deliverable",
        success_criteria: Optional[Dict[str, Any]] = None,
        deliverables: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        assigned_teams: Optional[List[str]] = None,
        responsible_agent_id: Optional[str] = None,
        priority_level: int = 5,
        weight_in_goal: Optional[Decimal] = None,
        parent_milestone_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> str:
        """Create a milestone for a goal"""

        milestone_id = str(uuid.uuid4())

        # Set defaults
        if success_criteria is None:
            success_criteria = {}
        if deliverables is None:
            deliverables = []
        if dependencies is None:
            dependencies = []
        if assigned_teams is None:
            assigned_teams = []
        if weight_in_goal is None:
            weight_in_goal = self.default_milestone_weight

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO goal_milestones (
                        id, goal_id, parent_milestone_id, title, description, milestone_type,
                        target_date, success_criteria, deliverables, dependencies,
                        assigned_teams, responsible_agent_id, priority_level,
                        weight_in_goal, created_by
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                    )
                """,
                    milestone_id,
                    goal_id,
                    parent_milestone_id,
                    title,
                    description,
                    milestone_type,
                    target_date,
                    json.dumps(success_criteria),
                    json.dumps(deliverables),
                    json.dumps(dependencies),
                    assigned_teams,
                    responsible_agent_id,
                    priority_level,
                    weight_in_goal,
                    created_by,
                )

            self.milestones_generated += 1
            logger.info(f"Created milestone {milestone_id}: {title} for goal {goal_id}")

            return milestone_id

        except Exception as e:
            logger.error(f"Error creating milestone: {e}")
            raise

    async def create_task_from_milestone(
        self,
        milestone_id: str,
        title: str,
        description: str,
        task_type: str = "development",
        complexity_level: str = "medium",
        estimated_hours: Optional[Decimal] = None,
        due_date: Optional[date] = None,
        assigned_team_id: Optional[str] = None,
        assigned_agent_id: Optional[str] = None,
        priority: int = 5,
        requirements: Optional[Dict[str, Any]] = None,
        acceptance_criteria: Optional[List[Dict[str, Any]]] = None,
        dependencies: Optional[List[Dict[str, Any]]] = None,
        created_by_agent_id: Optional[str] = None,
    ) -> str:
        """Create a task derived from a milestone"""

        task_id = str(uuid.uuid4())

        # Set defaults
        if requirements is None:
            requirements = {}
        if acceptance_criteria is None:
            acceptance_criteria = []
        if dependencies is None:
            dependencies = []

        try:
            async with self.pool.acquire() as conn:
                # Get goal_id from milestone
                goal_id = await conn.fetchval(
                    """
                    SELECT goal_id FROM goal_milestones WHERE id = $1
                """,
                    milestone_id,
                )

                if not goal_id:
                    raise ValueError(f"Milestone {milestone_id} not found")

                await conn.execute(
                    """
                    INSERT INTO goal_tasks (
                        id, goal_id, milestone_id, title, description, task_type,
                        complexity_level, estimated_hours, due_date, assigned_team_id,
                        assigned_agent_id, priority, dependencies, requirements,
                        acceptance_criteria, created_by_agent_id
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                    )
                """,
                    task_id,
                    str(goal_id),
                    milestone_id,
                    title,
                    description,
                    task_type,
                    complexity_level,
                    estimated_hours,
                    due_date,
                    assigned_team_id,
                    assigned_agent_id,
                    priority,
                    json.dumps(dependencies),
                    json.dumps(requirements),
                    json.dumps(acceptance_criteria),
                    created_by_agent_id,
                )

            self.tasks_created += 1
            logger.info(
                f"Created task {task_id}: {title} from milestone {milestone_id}"
            )

            return task_id

        except Exception as e:
            logger.error(f"Error creating task from milestone: {e}")
            raise

    async def get_goal_overview(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive goal overview with milestones and tasks"""

        try:
            async with self.pool.acquire() as conn:
                # Get goal details
                goal_row = await conn.fetchrow(
                    """
                    SELECT * FROM goal_overview WHERE id = $1
                """,
                    goal_id,
                )

                if not goal_row:
                    return None

                # Get milestones
                milestones = await conn.fetch(
                    """
                    SELECT * FROM goal_milestones 
                    WHERE goal_id = $1
                    ORDER BY target_date ASC, priority_level DESC
                """,
                    goal_id,
                )

                # Get tasks
                tasks = await conn.fetch(
                    """
                    SELECT * FROM goal_tasks 
                    WHERE goal_id = $1
                    ORDER BY due_date ASC, priority DESC
                """,
                    goal_id,
                )

                # Get recent progress
                progress_history = await conn.fetch(
                    """
                    SELECT * FROM goal_progress_tracking
                    WHERE goal_id = $1
                    ORDER BY recorded_at DESC
                    LIMIT 10
                """,
                    goal_id,
                )

                # Get metrics
                metrics = await conn.fetch(
                    """
                    SELECT * FROM goal_metrics
                    WHERE goal_id = $1 AND status = 'active'
                """,
                    goal_id,
                )

                return {
                    "goal": dict(goal_row),
                    "milestones": [dict(m) for m in milestones],
                    "tasks": [dict(t) for t in tasks],
                    "progress_history": [dict(p) for p in progress_history],
                    "metrics": [dict(m) for m in metrics],
                    "summary": {
                        "total_milestones": len(milestones),
                        "completed_milestones": len(
                            [m for m in milestones if m["status"] == "completed"]
                        ),
                        "total_tasks": len(tasks),
                        "completed_tasks": len(
                            [t for t in tasks if t["status"] == "completed"]
                        ),
                        "overdue_tasks": len(
                            [
                                t
                                for t in tasks
                                if t["due_date"]
                                and t["due_date"] < date.today()
                                and t["status"] not in ["completed", "cancelled"]
                            ]
                        ),
                    },
                }

        except Exception as e:
            logger.error(f"Error getting goal overview for {goal_id}: {e}")
            return None

    async def get_organization_goals_dashboard(
        self, organization_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard for organization goals"""

        try:
            async with self.pool.acquire() as conn:
                # Get dashboard view
                dashboard_goals = await conn.fetch(
                    """
                    SELECT * FROM active_goals_dashboard 
                    WHERE organization_name = (
                        SELECT name FROM organizations WHERE id = $1
                    )
                    ORDER BY priority_level DESC, days_remaining ASC
                """,
                    organization_id,
                )

                # Get summary statistics
                stats = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total_goals,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_goals,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_goals,
                        COUNT(CASE WHEN target_deadline < CURRENT_DATE AND status = 'active' THEN 1 END) as overdue_goals,
                        AVG(progress_percentage) as avg_progress,
                        AVG(completion_confidence) as avg_confidence
                    FROM organization_goals
                    WHERE organization_id = $1
                """,
                    organization_id,
                )

                # Get goals by type
                goals_by_type = await conn.fetch(
                    """
                    SELECT 
                        goal_type,
                        COUNT(*) as count,
                        AVG(progress_percentage) as avg_progress
                    FROM organization_goals
                    WHERE organization_id = $1 AND status = 'active'
                    GROUP BY goal_type
                    ORDER BY count DESC
                """,
                    organization_id,
                )

                # Get upcoming deadlines
                upcoming_deadlines = await conn.fetch(
                    """
                    SELECT id, title, target_deadline, progress_percentage, priority_level
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
                    "goals": [dict(g) for g in dashboard_goals],
                    "statistics": dict(stats) if stats else {},
                    "goals_by_type": [dict(gbt) for gbt in goals_by_type],
                    "upcoming_deadlines": [dict(ud) for ud in upcoming_deadlines],
                    "generated_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(
                f"Error getting organization dashboard for {organization_id}: {e}"
            )
            return {"error": str(e)}

    # Helper methods

    def _row_to_goal(self, row) -> OrganizationGoal:
        """Convert database row to OrganizationGoal object"""
        return OrganizationGoal(
            id=str(row["id"]),
            organization_id=str(row["organization_id"]),
            title=row["title"],
            description=row["description"],
            goal_type=GoalType(row["goal_type"]),
            priority_level=row["priority_level"],
            target_value=row["target_value"],
            target_unit=row["target_unit"],
            current_value=row["current_value"],
            success_criteria=json.loads(row["success_criteria"])
            if isinstance(row["success_criteria"], str)
            else row["success_criteria"],
            start_date=row["start_date"],
            target_deadline=row["target_deadline"],
            actual_completion_date=row["actual_completion_date"],
            status=GoalStatus(row["status"]),
            progress_percentage=row["progress_percentage"],
            completion_confidence=row["completion_confidence"],
            assigned_teams=row["assigned_teams"] or [],
            goal_owner_agent_id=str(row["goal_owner_agent_id"])
            if row["goal_owner_agent_id"]
            else None,
            stakeholder_agents=row["stakeholder_agents"] or [],
            tags=row["tags"] or [],
            metadata=json.loads(row["metadata"])
            if isinstance(row["metadata"], str)
            else row["metadata"],
            created_by=str(row["created_by"]) if row["created_by"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _determine_metric_type(self, unit: str) -> str:
        """Determine metric type based on unit"""
        financial_units = ["USD", "EUR", "GBP", "revenue", "cost", "profit"]
        if any(fu in unit.lower() for fu in financial_units):
            return "financial"
        elif unit.lower() in ["users", "customers", "subscribers"]:
            return "operational"
        elif "%" in unit or "percent" in unit.lower():
            return "engagement"
        else:
            return "technical"
