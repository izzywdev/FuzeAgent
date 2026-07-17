"""
Milestone and Task Generation Engine for FuzeAgent

This engine automatically generates milestones and tasks for organizational goals
using AI-powered analysis and planning. It breaks down complex goals into
actionable milestones and specific tasks across different time horizons.
"""

import asyncio
import json
import logging
import uuid
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class MilestoneTemplate:
    """Template for generating milestones"""

    title: str
    description: str
    milestone_type: str
    target_date_offset_days: int
    weight_in_goal: Decimal
    priority_level: int
    success_criteria: Dict[str, Any]
    deliverables: List[Dict[str, Any]]
    task_templates: List[Dict[str, Any]]


@dataclass
class TaskTemplate:
    """Template for generating tasks"""

    title: str
    description: str
    task_type: str
    complexity_level: str
    estimated_hours: Decimal
    requirements: Dict[str, Any]
    acceptance_criteria: List[Dict[str, Any]]
    suggested_teams: List[str]
    dependencies: List[str]


class MilestoneTaskEngine:
    """
    Intelligent engine for generating milestones and tasks from organizational goals.
    Uses AI-powered analysis and predefined templates for different goal types.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

        # Milestone and task templates by goal type
        self.milestone_templates = self._initialize_milestone_templates()
        self.task_templates = self._initialize_task_templates()

        # Configuration
        self.default_milestone_duration_weeks = 2
        self.max_milestones_per_goal = 20
        self.max_tasks_per_milestone = 15

        # Statistics
        self.milestones_generated = 0
        self.tasks_generated = 0
        self.plans_created = 0

    async def initialize(self):
        """Initialize the milestone task engine"""
        logger.info("Initializing MilestoneTaskEngine")

        try:
            self.pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5, command_timeout=60)

            logger.info("MilestoneTaskEngine initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MilestoneTaskEngine: {e}")
            raise

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
        logger.info("MilestoneTaskEngine closed")

    async def generate_goal_execution_plan(self, goal_id: str, planning_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive execution plan with milestones and tasks for a goal"""

        try:
            async with self.pool.acquire() as conn:
                # Get goal details
                goal = await conn.fetchrow(
                    """
                    SELECT * FROM organization_goals WHERE id = $1
                """,
                    goal_id,
                )

                if not goal:
                    raise ValueError(f"Goal {goal_id} not found")

                # Generate time-based milestone structure
                milestone_plan = await self._generate_milestone_structure(goal, planning_context)

                # Create milestones in database
                milestone_ids = []
                for milestone_data in milestone_plan["milestones"]:
                    milestone_id = await self._create_milestone_from_plan(goal_id, milestone_data)
                    milestone_ids.append(milestone_id)

                    # Generate tasks for each milestone
                    task_ids = []
                    for task_data in milestone_data.get("tasks", []):
                        task_id = await self._create_task_from_plan(goal_id, milestone_id, task_data)
                        task_ids.append(task_id)

                    milestone_data["generated_task_ids"] = task_ids

                # Update goal with generated plan metadata
                await conn.execute(
                    """
                    UPDATE organization_goals
                    SET metadata = metadata || $2, updated_at = NOW()
                    WHERE id = $1
                """,
                    goal_id,
                    json.dumps(
                        {
                            "execution_plan_generated": True,
                            "plan_generation_date": datetime.now().isoformat(),
                            "milestone_count": len(milestone_ids),
                            "estimated_task_count": sum(len(m.get("tasks", [])) for m in milestone_plan["milestones"]),
                        }
                    ),
                )

                self.plans_created += 1
                self.milestones_generated += len(milestone_ids)

                execution_plan = {
                    "goal_id": goal_id,
                    "plan_type": milestone_plan["plan_type"],
                    "planning_horizon": milestone_plan["planning_horizon"],
                    "milestones": milestone_plan["milestones"],
                    "generated_milestone_ids": milestone_ids,
                    "summary": {
                        "total_milestones": len(milestone_ids),
                        "estimated_duration_weeks": milestone_plan["estimated_duration_weeks"],
                        "complexity_assessment": milestone_plan["complexity_assessment"],
                        "recommended_team_size": milestone_plan["recommended_team_size"],
                    },
                    "generated_at": datetime.now().isoformat(),
                }

                logger.info(f"Generated execution plan for goal {goal_id}: {len(milestone_ids)} milestones")

                return execution_plan

        except Exception as e:
            logger.error(f"Error generating execution plan for goal {goal_id}: {e}")
            raise

    async def generate_monthly_milestones(
        self,
        goal_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[str]:
        """Generate monthly milestone breakdown for a goal"""

        try:
            async with self.pool.acquire() as conn:
                goal = await conn.fetchrow(
                    """
                    SELECT * FROM organization_goals WHERE id = $1
                """,
                    goal_id,
                )

                if not goal:
                    raise ValueError(f"Goal {goal_id} not found")

                # Set date range
                if start_date is None:
                    start_date = goal["start_date"]
                if end_date is None:
                    end_date = goal["target_deadline"]

                # Calculate monthly milestones
                monthly_milestones = []
                current_date = start_date
                month_counter = 1
                target_value = goal["target_value"] or Decimal("100")

                while current_date <= end_date:
                    # Calculate monthly target (progressive increase)
                    months_total = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

                    # Use progressive growth curve for revenue goals
                    if goal["goal_type"] == "business" and "revenue" in goal["title"].lower():
                        monthly_target = self._calculate_progressive_revenue_target(target_value, month_counter, months_total)
                    else:
                        # Linear progression for other goals
                        monthly_target = (target_value * month_counter) / months_total

                    # Create milestone
                    milestone_title = f"Month {month_counter}: {goal['title']} Milestone"
                    milestone_description = f"Achieve {monthly_target} {goal['target_unit']} by end of month {month_counter}"

                    # Get last day of month
                    last_day = monthrange(current_date.year, current_date.month)[1]
                    milestone_date = date(current_date.year, current_date.month, last_day)

                    milestone_id = await conn.execute(
                        """
                        INSERT INTO goal_milestones (
                            id, goal_id, title, description, milestone_type, target_date,
                            success_criteria, weight_in_goal, priority_level, created_by,
                            metadata
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
                        ) RETURNING id
                    """,
                        str(uuid.uuid4()),
                        goal_id,
                        milestone_title,
                        milestone_description,
                        "metric",
                        milestone_date,
                        json.dumps(
                            {
                                "target_value": float(monthly_target),
                                "measurement_unit": goal["target_unit"],
                                "measurement_method": "monthly_cumulative",
                            }
                        ),
                        Decimal("100") / months_total,  # Equal weight distribution
                        5,  # Medium priority
                        goal["created_by"],
                        json.dumps(
                            {
                                "month_number": month_counter,
                                "generated_type": "monthly_milestone",
                                "progressive_target": float(monthly_target),
                            }
                        ),
                    )

                    monthly_milestones.append(str(milestone_id))

                    # Move to next month
                    if current_date.month == 12:
                        current_date = date(current_date.year + 1, 1, 1)
                    else:
                        current_date = date(current_date.year, current_date.month + 1, 1)

                    month_counter += 1

                logger.info(f"Generated {len(monthly_milestones)} monthly milestones for goal {goal_id}")

                return monthly_milestones

        except Exception as e:
            logger.error(f"Error generating monthly milestones for goal {goal_id}: {e}")
            raise

    async def generate_weekly_tasks_for_milestone(self, milestone_id: str, focus_areas: Optional[List[str]] = None) -> List[str]:
        """Generate weekly task breakdown for a milestone"""

        try:
            async with self.pool.acquire() as conn:
                milestone = await conn.fetchrow(
                    """
                    SELECT m.*, g.goal_type, g.target_value, g.target_unit
                    FROM goal_milestones m
                    JOIN organization_goals g ON m.goal_id = g.id
                    WHERE m.id = $1
                """,
                    milestone_id,
                )

                if not milestone:
                    raise ValueError(f"Milestone {milestone_id} not found")

                # Calculate weeks available
                weeks_to_deadline = max(1, (milestone["target_date"] - date.today()).days // 7)

                # Generate task templates based on goal type and milestone
                task_templates = self._get_task_templates_for_milestone(milestone["goal_type"], milestone["milestone_type"], focus_areas)

                # Create weekly tasks
                weekly_tasks = []
                for week_num in range(1, min(weeks_to_deadline + 1, 8)):  # Max 8 weeks
                    for template in task_templates:
                        if self._should_create_task_for_week(template, week_num, weeks_to_deadline):
                            task_id = await self._create_weekly_task(milestone["goal_id"], milestone_id, template, week_num)
                            weekly_tasks.append(task_id)

                logger.info(f"Generated {len(weekly_tasks)} weekly tasks for milestone {milestone_id}")

                return weekly_tasks

        except Exception as e:
            logger.error(f"Error generating weekly tasks for milestone {milestone_id}: {e}")
            raise

    async def generate_cross_functional_tasks(self, goal_id: str, target_functions: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Generate tasks across different business functions for a goal"""

        if target_functions is None:
            target_functions = [
                "development",
                "marketing",
                "sales",
                "operations",
                "finance",
            ]

        try:
            async with self.pool.acquire() as conn:
                goal = await conn.fetchrow(
                    """
                    SELECT * FROM organization_goals WHERE id = $1
                """,
                    goal_id,
                )

                if not goal:
                    raise ValueError(f"Goal {goal_id} not found")

                functional_tasks = {}

                for function in target_functions:
                    # Get function-specific task templates
                    function_templates = self._get_functional_task_templates(goal["goal_type"], function)

                    function_task_ids = []
                    for template in function_templates:
                        task_id = await self._create_functional_task(goal_id, function, template)
                        function_task_ids.append(task_id)

                    functional_tasks[function] = function_task_ids
                    self.tasks_generated += len(function_task_ids)

                logger.info(f"Generated cross-functional tasks for goal {goal_id}: {functional_tasks}")

                return functional_tasks

        except Exception as e:
            logger.error(f"Error generating cross-functional tasks for goal {goal_id}: {e}")
            raise

    # Helper methods for milestone and task generation

    async def _generate_milestone_structure(self, goal: Dict[str, Any], planning_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate the overall milestone structure for a goal"""

        goal_type = goal["goal_type"]
        target_deadline = goal["target_deadline"]
        start_date = goal["start_date"] or date.today()

        # Calculate total duration
        total_days = (target_deadline - start_date).days
        total_weeks = max(1, total_days // 7)

        # Determine planning approach based on goal type and duration
        if total_days <= 30:  # Short-term goal (1 month)
            plan_type = "weekly_focused"
            milestone_interval_weeks = 1
        elif total_days <= 90:  # Medium-term goal (3 months)
            plan_type = "bi_weekly"
            milestone_interval_weeks = 2
        else:  # Long-term goal (6+ months)
            plan_type = "monthly_focused"
            milestone_interval_weeks = 4

        # Generate milestone sequence
        milestones = []
        current_date = start_date
        milestone_counter = 1

        while current_date < target_deadline:
            next_date = min(
                current_date + timedelta(weeks=milestone_interval_weeks),
                target_deadline,
            )

            milestone_data = self._create_milestone_data(goal, milestone_counter, current_date, next_date, plan_type)
            milestones.append(milestone_data)

            current_date = next_date + timedelta(days=1)
            milestone_counter += 1

            # Safety limit
            if len(milestones) >= self.max_milestones_per_goal:
                break

        # Assess complexity and recommend team size
        complexity = self._assess_goal_complexity(goal, len(milestones))
        team_size = self._recommend_team_size(goal, complexity)

        return {
            "plan_type": plan_type,
            "planning_horizon": f"{total_weeks} weeks",
            "milestones": milestones,
            "estimated_duration_weeks": total_weeks,
            "complexity_assessment": complexity,
            "recommended_team_size": team_size,
        }

    def _create_milestone_data(
        self,
        goal: Dict[str, Any],
        milestone_number: int,
        start_date: date,
        target_date: date,
        plan_type: str,
    ) -> Dict[str, Any]:
        """Create milestone data structure"""

        goal_type = goal["goal_type"]

        # Get appropriate milestone template
        template = self._get_milestone_template(goal_type, milestone_number, plan_type)

        milestone_data = {
            "title": template["title"].format(number=milestone_number, goal_title=goal["title"]),
            "description": template["description"].format(number=milestone_number, target_date=target_date.strftime("%B %d, %Y")),
            "milestone_type": template["milestone_type"],
            "target_date": target_date.isoformat(),
            "weight_in_goal": template["weight_in_goal"],
            "priority_level": template["priority_level"],
            "success_criteria": template["success_criteria"],
            "deliverables": template["deliverables"],
            "tasks": self._generate_tasks_for_milestone(goal, template, start_date, target_date),
        }

        return milestone_data

    def _generate_tasks_for_milestone(
        self,
        goal: Dict[str, Any],
        milestone_template: Dict[str, Any],
        start_date: date,
        target_date: date,
    ) -> List[Dict[str, Any]]:
        """Generate tasks for a specific milestone"""

        tasks = []

        for task_template in milestone_template.get("task_templates", []):
            task_data = {
                "title": task_template["title"],
                "description": task_template["description"],
                "task_type": task_template["task_type"],
                "complexity_level": task_template["complexity_level"],
                "estimated_hours": task_template["estimated_hours"],
                "due_date": target_date.isoformat(),
                "priority": task_template.get("priority", 5),
                "requirements": task_template["requirements"],
                "acceptance_criteria": task_template["acceptance_criteria"],
                "suggested_teams": task_template.get("suggested_teams", []),
                "dependencies": task_template.get("dependencies", []),
            }
            tasks.append(task_data)

        return tasks[: self.max_tasks_per_milestone]

    def _calculate_progressive_revenue_target(self, final_target: Decimal, current_month: int, total_months: int) -> Decimal:
        """Calculate progressive revenue target using growth curve"""

        # Use exponential growth curve for revenue goals
        # This simulates realistic business growth patterns
        growth_factor = 1.2  # 20% month-over-month growth assumption

        if current_month == 1:
            base_monthly_target = final_target / (total_months * 2)  # Start lower
        else:
            # Progressive increase with diminishing growth rate
            base_monthly_target = (final_target * current_month * growth_factor) / (total_months * total_months)

        return min(base_monthly_target, final_target)

    def _get_milestone_template(self, goal_type: str, milestone_number: int, plan_type: str) -> Dict[str, Any]:
        """Get appropriate milestone template based on goal type and sequence"""

        templates = self.milestone_templates.get(goal_type, self.milestone_templates["business"])

        # Select template based on milestone position
        if milestone_number == 1:
            template_key = "foundation"
        elif plan_type == "monthly_focused" and milestone_number <= 3:
            template_key = "growth"
        else:
            template_key = "delivery"

        return templates.get(template_key, templates["foundation"])

    # Initialize template libraries

    def _initialize_milestone_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize milestone templates by goal type"""

        return {
            "business": {
                "foundation": {
                    "title": "Foundation Phase {number}: {goal_title} Setup",
                    "description": "Establish foundational elements and infrastructure for {goal_title} by {target_date}",
                    "milestone_type": "checkpoint",
                    "weight_in_goal": Decimal("15.0"),
                    "priority_level": 9,
                    "success_criteria": {"setup_completed": True, "team_aligned": True},
                    "deliverables": [
                        {
                            "type": "infrastructure",
                            "description": "Basic setup completed",
                        }
                    ],
                    "task_templates": [
                        {
                            "title": "Market Research and Analysis",
                            "description": "Conduct comprehensive market research and competitive analysis",
                            "task_type": "research",
                            "complexity_level": "medium",
                            "estimated_hours": Decimal("20.0"),
                            "requirements": {"deliverable": "market_research_report"},
                            "acceptance_criteria": [{"criteria": "Research report completed and reviewed"}],
                        },
                        {
                            "title": "Team Structure and Role Definition",
                            "description": "Define team structure and assign specific roles and responsibilities",
                            "task_type": "operations",
                            "complexity_level": "low",
                            "estimated_hours": Decimal("10.0"),
                            "requirements": {"deliverable": "org_chart"},
                            "acceptance_criteria": [{"criteria": "All roles defined and communicated"}],
                        },
                    ],
                },
                "growth": {
                    "title": "Growth Phase {number}: {goal_title} Execution",
                    "description": "Execute core strategies and drive growth for {goal_title} by {target_date}",
                    "milestone_type": "deliverable",
                    "weight_in_goal": Decimal("25.0"),
                    "priority_level": 8,
                    "success_criteria": {
                        "kpi_targets_met": True,
                        "growth_metrics_positive": True,
                    },
                    "deliverables": [{"type": "metrics", "description": "Growth targets achieved"}],
                    "task_templates": [
                        {
                            "title": "Marketing Campaign Launch",
                            "description": "Design and execute marketing campaigns to drive customer acquisition",
                            "task_type": "marketing",
                            "complexity_level": "high",
                            "estimated_hours": Decimal("40.0"),
                            "requirements": {
                                "budget_approved": True,
                                "campaign_strategy": "defined",
                            },
                            "acceptance_criteria": [{"criteria": "Campaign launched and performing to targets"}],
                        },
                        {
                            "title": "Sales Process Optimization",
                            "description": "Optimize sales processes and improve conversion rates",
                            "task_type": "sales",
                            "complexity_level": "medium",
                            "estimated_hours": Decimal("25.0"),
                            "requirements": {"crm_system": "configured"},
                            "acceptance_criteria": [{"criteria": "Sales conversion improved by 15%"}],
                        },
                    ],
                },
                "delivery": {
                    "title": "Delivery Phase {number}: {goal_title} Optimization",
                    "description": "Optimize and scale operations for {goal_title} by {target_date}",
                    "milestone_type": "metric",
                    "weight_in_goal": Decimal("20.0"),
                    "priority_level": 7,
                    "success_criteria": {
                        "optimization_targets_met": True,
                        "scalability_proven": True,
                    },
                    "deliverables": [
                        {
                            "type": "optimization",
                            "description": "Operations optimized and scaled",
                        }
                    ],
                    "task_templates": [
                        {
                            "title": "Performance Analytics and Optimization",
                            "description": "Analyze performance data and implement optimization strategies",
                            "task_type": "operations",
                            "complexity_level": "medium",
                            "estimated_hours": Decimal("30.0"),
                            "requirements": {"analytics_dashboard": "implemented"},
                            "acceptance_criteria": [{"criteria": "Performance improved by measurable metrics"}],
                        }
                    ],
                },
            },
            # Additional goal types would be added here
            "technical": {
                "foundation": {
                    "title": "Technical Setup {number}: {goal_title} Architecture",
                    "description": "Establish technical architecture and development environment for {goal_title}",
                    "milestone_type": "checkpoint",
                    "weight_in_goal": Decimal("20.0"),
                    "priority_level": 9,
                    "success_criteria": {
                        "architecture_defined": True,
                        "dev_environment_ready": True,
                    },
                    "deliverables": [
                        {
                            "type": "technical_spec",
                            "description": "Technical architecture documented",
                        }
                    ],
                    "task_templates": [
                        {
                            "title": "System Architecture Design",
                            "description": "Design comprehensive system architecture and technical specifications",
                            "task_type": "development",
                            "complexity_level": "high",
                            "estimated_hours": Decimal("35.0"),
                            "requirements": {"requirements_gathered": True},
                            "acceptance_criteria": [{"criteria": "Architecture design approved by technical team"}],
                        }
                    ],
                }
            },
        }

    def _initialize_task_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize task templates by function"""

        return {
            "development": [
                {
                    "title": "Feature Development Sprint",
                    "description": "Implement core features according to specifications",
                    "task_type": "development",
                    "complexity_level": "high",
                    "estimated_hours": Decimal("60.0"),
                    "requirements": {"specs_defined": True, "design_approved": True},
                    "acceptance_criteria": [{"criteria": "Feature implemented and tested"}],
                }
            ],
            "marketing": [
                {
                    "title": "Content Marketing Campaign",
                    "description": "Create and execute content marketing strategy",
                    "task_type": "marketing",
                    "complexity_level": "medium",
                    "estimated_hours": Decimal("25.0"),
                    "requirements": {"brand_guidelines": "established"},
                    "acceptance_criteria": [{"criteria": "Campaign content published and promoted"}],
                }
            ],
            "sales": [
                {
                    "title": "Sales Pipeline Development",
                    "description": "Build and optimize sales pipeline and processes",
                    "task_type": "sales",
                    "complexity_level": "medium",
                    "estimated_hours": Decimal("20.0"),
                    "requirements": {"crm_configured": True},
                    "acceptance_criteria": [{"criteria": "Sales pipeline established with clear stages"}],
                }
            ],
        }

    # Additional helper methods would be implemented here for:
    # - Task creation from plans
    # - Team assignment optimization
    # - Dependency management
    # - Progress tracking integration

    async def _create_milestone_from_plan(self, goal_id: str, milestone_data: Dict[str, Any]) -> str:
        """Create milestone in database from plan data"""
        milestone_id = str(uuid.uuid4())

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO goal_milestones (
                    id, goal_id, title, description, milestone_type, target_date,
                    success_criteria, weight_in_goal, priority_level, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                milestone_id,
                goal_id,
                milestone_data["title"],
                milestone_data["description"],
                milestone_data["milestone_type"],
                milestone_data["target_date"],
                json.dumps(milestone_data["success_criteria"]),
                milestone_data["weight_in_goal"],
                milestone_data["priority_level"],
                json.dumps({"generated_from_plan": True}),
            )

        return milestone_id

    async def _create_task_from_plan(self, goal_id: str, milestone_id: str, task_data: Dict[str, Any]) -> str:
        """Create task in database from plan data"""
        task_id = str(uuid.uuid4())

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO goal_tasks (
                    id, goal_id, milestone_id, title, description, task_type,
                    complexity_level, estimated_hours, due_date, priority,
                    requirements, acceptance_criteria, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
                task_id,
                goal_id,
                milestone_id,
                task_data["title"],
                task_data["description"],
                task_data["task_type"],
                task_data["complexity_level"],
                task_data["estimated_hours"],
                task_data["due_date"],
                task_data["priority"],
                json.dumps(task_data["requirements"]),
                json.dumps(task_data["acceptance_criteria"]),
                json.dumps({"generated_from_plan": True}),
            )

        self.tasks_generated += 1
        return task_id

    # Placeholder implementations for additional helper methods
    def _assess_goal_complexity(self, goal: Dict[str, Any], milestone_count: int) -> str:
        """Assess the complexity of a goal based on various factors"""
        # Simplified implementation
        if milestone_count > 15 or (goal.get("target_value", 0) > 100000):
            return "high"
        elif milestone_count > 8:
            return "medium"
        else:
            return "low"

    def _recommend_team_size(self, goal: Dict[str, Any], complexity: str) -> int:
        """Recommend optimal team size based on goal and complexity"""
        base_size = {"low": 3, "medium": 5, "high": 8}
        return base_size.get(complexity, 5)
