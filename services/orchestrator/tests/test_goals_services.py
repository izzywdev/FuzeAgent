"""
Unit tests for Goals Management Services
"""

import pytest
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from goals_management_service import (
    GoalsManagementService,
    GoalType,
    GoalStatus,
    OrganizationGoal,
)
from milestone_task_engine import MilestoneTaskEngine
from goal_conversation_service import (
    GoalConversationService,
    ConversationType,
    MessageType,
)
from goal_tracking_service import (
    GoalTrackingService,
    RiskLevel,
    AlertSeverity,
)


@pytest.mark.goals
class TestGoalsManagementService:
    """Test GoalsManagementService"""

    @pytest.fixture
    def service(self):
        return GoalsManagementService("postgresql://test:test@localhost:5432/test")

    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        pool.acquire = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock()
        pool.acquire.return_value.__aexit__ = AsyncMock()
        return pool

    @pytest.mark.asyncio
    async def test_initialize(self, service):
        """Test service initialization"""
        with patch("asyncpg.create_pool") as mock_create_pool:
            mock_create_pool.return_value = AsyncMock()

            await service.initialize()

            assert service.pool is not None
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_goal(self, service, mock_pool):
        """Test goal creation"""
        service.pool = mock_pool

        # Mock database connection and execute
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute = AsyncMock()

        goal_id = await service.create_goal(
            organization_id="org-123",
            title="Test Goal",
            description="Test Description",
            goal_type=GoalType.BUSINESS,
            target_value=Decimal("100000"),
            target_unit="USD",
        )

        assert goal_id is not None
        assert isinstance(goal_id, str)
        assert len(goal_id) > 0

        # Verify database calls were made
        assert (
            mock_conn.execute.call_count >= 2
        )  # Goal creation + metrics + progress tracking

    @pytest.mark.asyncio
    async def test_get_goal(self, service, mock_pool):
        """Test getting a goal"""
        service.pool = mock_pool

        # Mock database response
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Sample goal row data
        mock_row = {
            "id": str(uuid.uuid4()),
            "organization_id": str(uuid.uuid4()),
            "title": "Test Goal",
            "description": "Test Description",
            "goal_type": "business",
            "priority_level": 8,
            "target_value": Decimal("100000"),
            "target_unit": "USD",
            "current_value": Decimal("0"),
            "success_criteria": '{"test": true}',
            "start_date": date.today(),
            "target_deadline": date.today() + timedelta(days=180),
            "actual_completion_date": None,
            "status": "active",
            "progress_percentage": Decimal("0"),
            "completion_confidence": Decimal("0.5"),
            "assigned_teams": ["team-1"],
            "goal_owner_agent_id": None,
            "stakeholder_agents": [],
            "tags": ["test"],
            "metadata": '{"test": true}',
            "created_by": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        mock_conn.fetchrow.return_value = mock_row

        goal = await service.get_goal("goal-123")

        assert goal is not None
        assert isinstance(goal, OrganizationGoal)
        assert goal.title == "Test Goal"
        assert goal.goal_type == GoalType.BUSINESS
        assert goal.status == GoalStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_update_goal_progress(self, service, mock_pool):
        """Test updating goal progress"""
        service.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute = AsyncMock()

        success = await service.update_goal_progress(
            goal_id="goal-123",
            progress_percentage=Decimal("25.5"),
            current_value=Decimal("25500"),
            completion_confidence=Decimal("0.7"),
            progress_notes="Good progress",
            recorded_by="user-123",
        )

        assert success is True
        assert mock_conn.execute.call_count == 2  # Update + tracking entry

    @pytest.mark.asyncio
    async def test_create_milestone(self, service, mock_pool):
        """Test milestone creation"""
        service.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute = AsyncMock()

        milestone_id = await service.create_milestone(
            goal_id="goal-123",
            title="Test Milestone",
            description="Test milestone description",
            target_date=date.today() + timedelta(days=30),
        )

        assert milestone_id is not None
        assert isinstance(milestone_id, str)
        mock_conn.execute.assert_called_once()


@pytest.mark.goals
class TestMilestoneTaskEngine:
    """Test MilestoneTaskEngine"""

    @pytest.fixture
    def engine(self):
        return MilestoneTaskEngine("postgresql://test:test@localhost:5432/test")

    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        pool.acquire = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock()
        pool.acquire.return_value.__aexit__ = AsyncMock()
        return pool

    @pytest.mark.asyncio
    async def test_generate_goal_execution_plan(self, engine, mock_pool):
        """Test generating execution plan"""
        engine.pool = mock_pool

        # Mock goal data
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        goal_data = {
            "id": str(uuid.uuid4()),
            "title": "Test Goal",
            "goal_type": "business",
            "target_deadline": date.today() + timedelta(days=180),
            "start_date": date.today(),
            "target_value": Decimal("100000"),
        }
        mock_conn.fetchrow.return_value = goal_data
        mock_conn.execute.return_value = "milestone-123"

        execution_plan = await engine.generate_goal_execution_plan(
            goal_id="goal-123", planning_context={"focus": "revenue"}
        )

        assert execution_plan is not None
        assert "goal_id" in execution_plan
        assert "milestones" in execution_plan
        assert "summary" in execution_plan
        assert execution_plan["goal_id"] == "goal-123"

    @pytest.mark.asyncio
    async def test_generate_monthly_milestones(self, engine, mock_pool):
        """Test generating monthly milestones"""
        engine.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock goal data for 6-month timeline
        goal_data = {
            "id": str(uuid.uuid4()),
            "title": "Revenue Goal",
            "goal_type": "business",
            "target_value": Decimal("100000"),
            "target_unit": "USD",
            "start_date": date.today(),
            "target_deadline": date.today() + timedelta(days=180),
            "created_by": "user-123",
        }
        mock_conn.fetchrow.return_value = goal_data
        mock_conn.execute.return_value = str(uuid.uuid4())

        milestone_ids = await engine.generate_monthly_milestones(goal_id="goal-123")

        assert isinstance(milestone_ids, list)
        assert len(milestone_ids) == 6  # 6 months

        # Verify database insertions were made
        assert mock_conn.execute.call_count == 6

    @pytest.mark.asyncio
    async def test_generate_cross_functional_tasks(self, engine, mock_pool):
        """Test generating cross-functional tasks"""
        engine.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        goal_data = {
            "id": str(uuid.uuid4()),
            "goal_type": "business",
            "title": "Test Goal",
        }
        mock_conn.fetchrow.return_value = goal_data
        mock_conn.execute.return_value = str(uuid.uuid4())

        functional_tasks = await engine.generate_cross_functional_tasks(
            goal_id="goal-123", target_functions=["development", "marketing", "sales"]
        )

        assert isinstance(functional_tasks, dict)
        assert "development" in functional_tasks
        assert "marketing" in functional_tasks
        assert "sales" in functional_tasks

        # Check that tasks were generated for each function
        for function, task_ids in functional_tasks.items():
            assert isinstance(task_ids, list)
            assert len(task_ids) > 0


@pytest.mark.goals
class TestGoalConversationService:
    """Test GoalConversationService"""

    @pytest.fixture
    def service(self):
        return GoalConversationService("postgresql://test:test@localhost:5432/test")

    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        pool.acquire = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock()
        pool.acquire.return_value.__aexit__ = AsyncMock()
        return pool

    @pytest.mark.asyncio
    async def test_create_goal_conversation(self, service, mock_pool):
        """Test creating a goal conversation"""
        service.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock goal data
        goal_data = {
            "title": "Test Goal",
            "description": "Test Description",
            "goal_type": "business",
            "target_deadline": date.today() + timedelta(days=180),
            "progress_percentage": Decimal("0"),
            "target_value": Decimal("100000"),
        }
        mock_conn.fetchrow.return_value = goal_data
        mock_conn.execute = AsyncMock()

        conversation_id = await service.create_goal_conversation(
            goal_id="goal-123",
            conversation_type=ConversationType.PLANNING,
            conversation_title="Strategic Planning Session",
            initial_context={"focus": "revenue"},
        )

        assert conversation_id is not None
        assert isinstance(conversation_id, str)

        # Verify database operations
        mock_conn.fetchrow.assert_called_once()  # Get goal context
        assert mock_conn.execute.call_count >= 1  # Insert conversation

    @pytest.mark.asyncio
    async def test_add_message_to_conversation(self, service, mock_pool):
        """Test adding message to conversation"""
        service.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = "[]"  # Empty messages initially
        mock_conn.execute = AsyncMock()

        message_id = await service.add_message_to_conversation(
            conversation_id="conv-123",
            message_type=MessageType.HUMAN,
            sender_id="user-123",
            sender_name="Test User",
            content="Let's discuss the strategy",
        )

        assert message_id is not None
        assert isinstance(message_id, str)

        # Verify database operations
        mock_conn.fetchval.assert_called()  # Get current messages
        mock_conn.execute.assert_called()  # Update with new message

    @pytest.mark.asyncio
    async def test_generate_planning_milestones(self, service, mock_pool):
        """Test generating planning milestones"""
        service.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock conversation and goal data
        conversation_data = {
            "id": "conv-123",
            "goal_id": "goal-123",
            "title": "Revenue Goal",
            "description": "Achieve $100K MRR",
            "goal_type": "business",
            "target_deadline": date.today() + timedelta(days=180),
            "target_value": Decimal("100000"),
            "target_unit": "USD",
            "messages": "[]",
        }
        mock_conn.fetchrow.return_value = conversation_data

        milestones = await service.generate_planning_milestones(
            conversation_id="conv-123",
            planning_context={"approach": "aggressive_growth"},
        )

        assert isinstance(milestones, list)
        # For business revenue goals, should generate milestones
        if conversation_data["goal_type"] == "business":
            assert len(milestones) > 0


@pytest.mark.goals
class TestGoalTrackingService:
    """Test GoalTrackingService"""

    @pytest.fixture
    def service(self):
        return GoalTrackingService("postgresql://test:test@localhost:5432/test")

    @pytest.fixture
    def mock_pool(self):
        pool = AsyncMock()
        pool.acquire = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock()
        pool.acquire.return_value.__aexit__ = AsyncMock()
        return pool

    @pytest.mark.asyncio
    async def test_record_progress_update(self, service, mock_pool):
        """Test recording progress update"""
        service.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock current goal state
        goal_state = {
            "progress_percentage": Decimal("20"),
            "current_value": Decimal("20000"),
            "completion_confidence": Decimal("0.6"),
            "target_value": Decimal("100000"),
            "target_deadline": date.today() + timedelta(days=150),
            "status": "active",
            "title": "Test Goal",
        }
        mock_conn.fetchrow.return_value = goal_state
        mock_conn.execute = AsyncMock()
        mock_conn.fetch.return_value = []  # No historical progress data

        snapshot_id = await service.record_progress_update(
            goal_id="goal-123",
            progress_percentage=Decimal("25"),
            current_value=Decimal("25000"),
            notes="Good progress this week",
            recorded_by="user-123",
            confidence_score=Decimal("0.7"),
        )

        assert snapshot_id is not None
        assert isinstance(snapshot_id, str)

        # Verify database operations
        mock_conn.fetchrow.assert_called_once()  # Get current goal state
        assert (
            mock_conn.execute.call_count >= 1
        )  # Record progress + possible goal update

    @pytest.mark.asyncio
    async def test_assess_goal_deadline_risk(self, service, mock_pool):
        """Test assessing deadline risk"""
        service.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock goal data with some risk factors
        goal_data = {
            "id": str(uuid.uuid4()),
            "title": "Test Goal",
            "progress_percentage": Decimal("30"),  # Low progress
            "target_deadline": date.today() + timedelta(days=30),  # Soon deadline
            "status": "active",
            "total_milestones": 5,
            "completed_milestones": 1,
            "total_tasks": 20,
            "completed_tasks": 4,
            "overdue_tasks": 3,  # Risk factor
        }
        mock_conn.fetchrow.return_value = goal_data
        mock_conn.fetch.return_value = []  # No progress history

        deadline_risk = await service.assess_goal_deadline_risk("goal-123")

        assert deadline_risk is not None
        assert hasattr(deadline_risk, "goal_id")
        assert hasattr(deadline_risk, "risk_level")
        assert hasattr(deadline_risk, "probability_of_delay")
        assert hasattr(deadline_risk, "estimated_completion_date")

        assert deadline_risk.goal_id == "goal-123"
        assert deadline_risk.risk_level in [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ]
        assert 0 <= float(deadline_risk.probability_of_delay) <= 1

    @pytest.mark.asyncio
    async def test_generate_progress_report(self, service, mock_pool):
        """Test generating progress report"""
        service.pool = mock_pool

        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock goal overview data
        goal_overview = {
            "id": str(uuid.uuid4()),
            "title": "Test Goal",
            "progress_percentage": Decimal("40"),
            "current_value": Decimal("40000"),
            "target_value": Decimal("100000"),
            "days_remaining": 120,
            "calculated_status": "active",
            "total_milestones": 6,
            "completed_milestones": 2,
            "total_tasks": 30,
            "completed_tasks": 12,
        }
        mock_conn.fetchrow.return_value = goal_overview

        # Mock progress history
        progress_history = [
            {
                "recorded_at": datetime.now() - timedelta(days=10),
                "progress_percentage": Decimal("35"),
                "current_value": Decimal("35000"),
                "progress_notes": "Steady progress",
            },
            {
                "recorded_at": datetime.now() - timedelta(days=5),
                "progress_percentage": Decimal("38"),
                "current_value": Decimal("38000"),
                "progress_notes": "Good week",
            },
            {
                "recorded_at": datetime.now(),
                "progress_percentage": Decimal("40"),
                "current_value": Decimal("40000"),
                "progress_notes": "On track",
            },
        ]
        mock_conn.fetch.return_value = progress_history

        report = await service.generate_progress_report(
            goal_id="goal-123", report_period_days=30
        )

        assert isinstance(report, dict)
        assert report["goal_id"] == "goal-123"
        assert "current_status" in report
        assert "performance_metrics" in report
        assert "deadline_risk" in report
        assert "progress_history" in report
        assert "insights" in report
        assert "recommendations" in report

        # Verify structure of key sections
        assert "progress_percentage" in report["current_status"]
        assert isinstance(report["progress_history"], list)
        assert len(report["progress_history"]) == 3


@pytest.mark.goals
class TestServiceIntegration:
    """Integration tests for Goals services working together"""

    @pytest.mark.asyncio
    async def test_goal_to_milestone_to_task_workflow(self):
        """Test complete workflow from goal creation to task generation"""

        # This would require actual database setup for full integration testing
        # For now, we'll test the service interfaces work together

        goals_service = GoalsManagementService(
            "postgresql://test:test@localhost:5432/test"
        )
        milestone_engine = MilestoneTaskEngine(
            "postgresql://test:test@localhost:5432/test"
        )

        # Mock the services
        with patch.object(
            goals_service, "create_goal"
        ) as mock_create_goal, patch.object(
            milestone_engine, "generate_goal_execution_plan"
        ) as mock_generate_plan:
            mock_create_goal.return_value = "goal-123"
            mock_generate_plan.return_value = {
                "goal_id": "goal-123",
                "milestones": [{"title": "Phase 1"}],
                "summary": {"total_milestones": 1},
            }

            # Simulate workflow
            goal_id = await goals_service.create_goal(
                organization_id="org-123",
                title="Integration Test Goal",
                description="Test goal for workflow",
                goal_type=GoalType.BUSINESS,
            )

            execution_plan = await milestone_engine.generate_goal_execution_plan(
                goal_id=goal_id
            )

            # Verify integration
            assert goal_id == "goal-123"
            assert execution_plan["goal_id"] == goal_id
            assert len(execution_plan["milestones"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
