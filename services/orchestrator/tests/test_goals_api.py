"""
Comprehensive test coverage for Goals Management API endpoints
"""

import pytest
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from services.orchestrator.main import app
from services.orchestrator.goals_management_service import (
    GoalType,
    GoalStatus,
    OrganizationGoal,
)
from services.orchestrator.goal_conversation_service import (
    ConversationType,
    ConversationStatus,
)
from services.orchestrator.goal_tracking_service import RiskLevel, DeadlineRisk

# Test client
client = TestClient(app)


# Test data fixtures
@pytest.fixture
def sample_goal_data():
    return {
        "title": "Reach $100K MRR",
        "description": "Achieve $100,000 monthly recurring revenue in 6 months",
        "goal_type": "business",
        "target_value": 100000,
        "target_unit": "USD",
        "target_deadline": (date.today() + timedelta(days=180)).isoformat(),
        "priority_level": 10,
        "success_criteria": {
            "revenue_target": 100000,
            "sustainability": "3_consecutive_months",
        },
        "assigned_teams": ["team-1", "team-2"],
        "tags": ["revenue", "growth"],
        "metadata": {"business_critical": True},
    }


@pytest.fixture
def sample_milestone_data():
    return {
        "title": "Month 1 Milestone",
        "description": "Achieve first month targets",
        "target_date": (date.today() + timedelta(days=30)).isoformat(),
        "milestone_type": "deliverable",
        "success_criteria": {"target_achieved": True},
        "priority_level": 8,
        "weight_in_goal": 16.67,
    }


@pytest.fixture
def sample_task_data():
    return {
        "title": "Develop marketing strategy",
        "description": "Create comprehensive marketing strategy for growth",
        "task_type": "marketing",
        "complexity_level": "high",
        "estimated_hours": 40,
        "priority": 8,
        "requirements": {"deliverable": "strategy_document"},
    }


@pytest.fixture
def sample_conversation_data():
    return {
        "conversation_type": "planning",
        "conversation_title": "Strategic Planning Session",
        "initial_context": {"focus": "revenue_growth"},
    }


@pytest.fixture
def sample_organization_goal():
    return OrganizationGoal(
        id=str(uuid.uuid4()),
        organization_id=str(uuid.uuid4()),
        title="Test Goal",
        description="Test goal description",
        goal_type=GoalType.BUSINESS,
        priority_level=8,
        target_value=Decimal("100000"),
        target_unit="USD",
        current_value=Decimal("0"),
        success_criteria={"test": True},
        start_date=date.today(),
        target_deadline=date.today() + timedelta(days=180),
        actual_completion_date=None,
        status=GoalStatus.ACTIVE,
        progress_percentage=Decimal("0"),
        completion_confidence=Decimal("0.5"),
        assigned_teams=["team-1"],
        goal_owner_agent_id=None,
        stakeholder_agents=[],
        tags=["test"],
        metadata={"test": True},
        created_by=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


class TestGoalsManagementAPI:
    """Test Goals Management API endpoints"""

    def test_health_check(self):
        """Test the health check endpoint works"""
        response = client.get("/health")
        assert response.status_code == 200

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_create_goal_success(self, mock_goals_service, sample_goal_data):
        """Test successful goal creation"""
        # Mock the service
        mock_goals_service.create_goal = AsyncMock(return_value="goal-123")

        response = client.post(
            "/organizations/org-123/goals",
            json=sample_goal_data,
            params={"created_by": "user-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["status"] == "created"

        # Verify service was called correctly
        mock_goals_service.create_goal.assert_called_once()

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_create_goal_invalid_data(self, mock_goals_service):
        """Test goal creation with invalid data"""
        invalid_data = {
            "title": "",  # Empty title should fail validation
            "description": "Test description",
        }

        response = client.post("/organizations/org-123/goals", json=invalid_data)

        assert response.status_code == 422  # Validation error

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_list_organization_goals(
        self, mock_goals_service, sample_organization_goal
    ):
        """Test listing organization goals"""
        mock_goals_service.list_organization_goals = AsyncMock(
            return_value=[sample_organization_goal]
        )

        response = client.get("/organizations/org-123/goals")

        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == "org-123"
        assert len(data["goals"]) == 1
        assert data["goals"][0]["title"] == "Test Goal"

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_list_goals_with_filters(
        self, mock_goals_service, sample_organization_goal
    ):
        """Test listing goals with status and type filters"""
        mock_goals_service.list_organization_goals = AsyncMock(
            return_value=[sample_organization_goal]
        )

        response = client.get(
            "/organizations/org-123/goals",
            params={
                "status": ["active", "paused"],
                "goal_type": ["business"],
                "limit": 25,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["goals"]) == 1

        # Verify service was called with filters
        mock_goals_service.list_organization_goals.assert_called_once()

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_get_goal_success(self, mock_goals_service, sample_organization_goal):
        """Test getting a specific goal"""
        mock_goals_service.get_goal = AsyncMock(return_value=sample_organization_goal)

        response = client.get("/goals/goal-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_organization_goal.id
        assert data["title"] == sample_organization_goal.title
        assert data["goal_type"] == "business"
        assert data["status"] == "active"

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_get_goal_not_found(self, mock_goals_service):
        """Test getting non-existent goal"""
        mock_goals_service.get_goal = AsyncMock(return_value=None)

        response = client.get("/goals/nonexistent-goal")

        assert response.status_code == 404
        assert "Goal not found" in response.json()["detail"]

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_get_goal_overview(self, mock_goals_service):
        """Test getting goal overview"""
        mock_overview = {
            "goal": {"id": "goal-123", "title": "Test Goal"},
            "milestones": [{"id": "milestone-1", "title": "Test Milestone"}],
            "tasks": [{"id": "task-1", "title": "Test Task"}],
            "summary": {"total_milestones": 1, "total_tasks": 1},
        }
        mock_goals_service.get_goal_overview = AsyncMock(return_value=mock_overview)

        response = client.get("/goals/goal-123/overview")

        assert response.status_code == 200
        data = response.json()
        assert data["goal"]["id"] == "goal-123"
        assert len(data["milestones"]) == 1
        assert len(data["tasks"]) == 1

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_update_goal_progress(self, mock_goals_service):
        """Test updating goal progress"""
        mock_goals_service.update_goal_progress = AsyncMock(return_value=True)

        update_data = {
            "progress_percentage": 25.5,
            "current_value": 25000,
            "completion_confidence": 0.7,
            "notes": "Good progress this month",
        }

        response = client.put("/goals/goal-123/progress", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["status"] == "updated"

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_update_goal_progress_not_found(self, mock_goals_service):
        """Test updating progress for non-existent goal"""
        mock_goals_service.update_goal_progress = AsyncMock(return_value=False)

        update_data = {"progress_percentage": 25.5}

        response = client.put("/goals/nonexistent-goal/progress", json=update_data)

        assert response.status_code == 404


class TestMilestonesAPI:
    """Test Milestones API endpoints"""

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_create_milestone(self, mock_goals_service, sample_milestone_data):
        """Test creating a milestone"""
        mock_goals_service.create_milestone = AsyncMock(return_value="milestone-123")

        response = client.post("/goals/goal-123/milestones", json=sample_milestone_data)

        assert response.status_code == 200
        data = response.json()
        assert data["milestone_id"] == "milestone-123"
        assert data["status"] == "created"

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_create_task_from_milestone(self, mock_goals_service, sample_task_data):
        """Test creating a task from milestone"""
        mock_goals_service.create_task_from_milestone = AsyncMock(
            return_value="task-123"
        )

        response = client.post("/milestones/milestone-123/tasks", json=sample_task_data)

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-123"
        assert data["status"] == "created"


class TestPlanningEngineAPI:
    """Test Planning Engine API endpoints"""

    @patch("services.orchestrator.main.app.state.milestone_task_engine")
    def test_generate_execution_plan(self, mock_engine):
        """Test generating execution plan"""
        mock_plan = {
            "goal_id": "goal-123",
            "plan_type": "monthly_focused",
            "milestones": [{"title": "Month 1", "tasks": []}],
            "summary": {"total_milestones": 1},
        }
        mock_engine.generate_goal_execution_plan = AsyncMock(return_value=mock_plan)

        response = client.post("/goals/goal-123/generate-execution-plan")

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["plan_type"] == "monthly_focused"

    @patch("services.orchestrator.main.app.state.milestone_task_engine")
    def test_generate_monthly_milestones(self, mock_engine):
        """Test generating monthly milestones"""
        milestone_ids = ["milestone-1", "milestone-2", "milestone-3"]
        mock_engine.generate_monthly_milestones = AsyncMock(return_value=milestone_ids)

        response = client.post("/goals/goal-123/generate-monthly-milestones")

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["count"] == 3
        assert data["milestone_ids"] == milestone_ids

    @patch("services.orchestrator.main.app.state.milestone_task_engine")
    def test_generate_weekly_tasks(self, mock_engine):
        """Test generating weekly tasks"""
        task_ids = ["task-1", "task-2", "task-3", "task-4"]
        mock_engine.generate_weekly_tasks_for_milestone = AsyncMock(
            return_value=task_ids
        )

        focus_areas = ["development", "testing"]
        response = client.post(
            "/milestones/milestone-123/generate-weekly-tasks", json=focus_areas
        )

        assert response.status_code == 200
        data = response.json()
        assert data["milestone_id"] == "milestone-123"
        assert data["count"] == 4
        assert data["task_ids"] == task_ids

    @patch("services.orchestrator.main.app.state.milestone_task_engine")
    def test_generate_cross_functional_tasks(self, mock_engine):
        """Test generating cross-functional tasks"""
        functional_tasks = {
            "development": ["dev-task-1", "dev-task-2"],
            "marketing": ["marketing-task-1"],
            "sales": ["sales-task-1", "sales-task-2"],
        }
        mock_engine.generate_cross_functional_tasks = AsyncMock(
            return_value=functional_tasks
        )

        target_functions = ["development", "marketing", "sales"]
        response = client.post(
            "/goals/goal-123/generate-cross-functional-tasks", json=target_functions
        )

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["total_tasks"] == 5
        assert "development" in data["functional_tasks"]
        assert len(data["functional_tasks"]["development"]) == 2


class TestConversationsAPI:
    """Test Goal Conversations API endpoints"""

    @patch("services.orchestrator.main.app.state.goal_conversation_service")
    def test_create_goal_conversation(self, mock_service, sample_conversation_data):
        """Test creating a goal conversation"""
        mock_service.create_goal_conversation = AsyncMock(return_value="conv-123")

        response = client.post(
            "/goals/goal-123/conversations", json=sample_conversation_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv-123"
        assert data["status"] == "created"

    @patch("services.orchestrator.main.app.state.goal_conversation_service")
    def test_get_goal_conversation(self, mock_service):
        """Test getting a goal conversation"""
        mock_conversation = {
            "id": "conv-123",
            "goal_id": "goal-123",
            "conversation_title": "Test Conversation",
            "messages": [],
            "insights_generated": [],
            "action_items": [],
        }
        mock_service.get_conversation = AsyncMock(return_value=mock_conversation)

        response = client.get("/conversations/conv-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "conv-123"
        assert data["goal_id"] == "goal-123"

    @patch("services.orchestrator.main.app.state.goal_conversation_service")
    def test_add_message_to_conversation(self, mock_service):
        """Test adding a message to conversation"""
        mock_service.add_message_to_conversation = AsyncMock(return_value="msg-123")

        message_data = {
            "message_type": "human",
            "sender_name": "Test User",
            "content": "Let's discuss the strategy",
            "metadata": {"importance": "high"},
        }

        response = client.post("/conversations/conv-123/messages", json=message_data)

        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] == "msg-123"
        assert data["status"] == "added"

    @patch("services.orchestrator.main.app.state.goal_conversation_service")
    def test_generate_planning_milestones_from_conversation(self, mock_service):
        """Test generating milestones from conversation"""
        mock_milestones = [
            {"title": "Phase 1", "description": "Initial setup"},
            {"title": "Phase 2", "description": "Implementation"},
        ]
        mock_service.generate_planning_milestones = AsyncMock(
            return_value=mock_milestones
        )

        response = client.post("/conversations/conv-123/generate-milestones")

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv-123"
        assert data["count"] == 2
        assert len(data["milestones"]) == 2

    @patch("services.orchestrator.main.app.state.goal_conversation_service")
    def test_conduct_progress_review(self, mock_service):
        """Test conducting progress review"""
        mock_review = {
            "review_period_days": 30,
            "goal_progress": {"current_progress": 25.0},
            "recommendations": ["Focus on critical tasks"],
        }
        mock_service.conduct_progress_review = AsyncMock(return_value=mock_review)

        response = client.post(
            "/conversations/conv-123/conduct-progress-review?review_period_days=30"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["review_period_days"] == 30
        assert "recommendations" in data

    @patch("services.orchestrator.main.app.state.goal_conversation_service")
    def test_extract_action_items(self, mock_service):
        """Test extracting action items from conversation"""
        mock_action_items = [
            {"id": "action-1", "title": "Review strategy", "status": "pending"},
            {"id": "action-2", "title": "Update timeline", "status": "pending"},
        ]
        mock_service.extract_action_items_from_conversation = AsyncMock(
            return_value=mock_action_items
        )

        response = client.post("/conversations/conv-123/extract-action-items")

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv-123"
        assert data["count"] == 2
        assert len(data["action_items"]) == 2

    @patch("services.orchestrator.main.app.state.goal_conversation_service")
    def test_get_goal_conversations(self, mock_service):
        """Test getting conversations for a goal"""
        mock_conversations = [
            {"id": "conv-1", "conversation_title": "Planning Session"},
            {"id": "conv-2", "conversation_title": "Progress Review"},
        ]
        mock_service.get_goal_conversations = AsyncMock(return_value=mock_conversations)

        response = client.get("/goals/goal-123/conversations?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["count"] == 2
        assert len(data["conversations"]) == 2


class TestTrackingAPI:
    """Test Goal Tracking API endpoints"""

    @patch("services.orchestrator.main.app.state.goal_tracking_service")
    def test_record_progress_tracking(self, mock_service):
        """Test recording progress tracking update"""
        mock_service.record_progress_update = AsyncMock(return_value="snapshot-123")

        progress_data = {
            "progress_percentage": 30.5,
            "current_value": 30500,
            "notes": "Good progress this week",
            "confidence_score": 0.8,
            "trigger_alerts": True,
        }

        response = client.post("/goals/goal-123/track-progress", json=progress_data)

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["snapshot_id"] == "snapshot-123"
        assert data["status"] == "recorded"

    @patch("services.orchestrator.main.app.state.goal_tracking_service")
    def test_assess_deadline_risk(self, mock_service):
        """Test assessing deadline risk"""
        mock_risk = DeadlineRisk(
            goal_id="goal-123",
            risk_level=RiskLevel.MEDIUM,
            probability_of_delay=Decimal("0.4"),
            estimated_completion_date=date.today() + timedelta(days=200),
            days_at_risk=20,
            critical_path_items=[{"type": "overdue_task", "id": "task-1"}],
            mitigation_strategies=[{"strategy": "resource_reallocation"}],
            updated_at=datetime.now(),
        )
        mock_service.assess_goal_deadline_risk = AsyncMock(return_value=mock_risk)

        response = client.get("/goals/goal-123/deadline-risk")

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["risk_level"] == "medium"
        assert data["probability_of_delay"] == 0.4
        assert data["days_at_risk"] == 20
        assert len(data["critical_path_items"]) == 1
        assert len(data["mitigation_strategies"]) == 1

    @patch("services.orchestrator.main.app.state.goal_tracking_service")
    def test_generate_progress_report(self, mock_service):
        """Test generating progress report"""
        mock_report = {
            "goal_id": "goal-123",
            "goal_title": "Test Goal",
            "report_period_days": 30,
            "current_status": {"progress_percentage": 25.0},
            "performance_metrics": {"velocity": 0.8},
            "insights": ["Goal is on track"],
            "recommendations": ["Continue current pace"],
        }
        mock_service.generate_progress_report = AsyncMock(return_value=mock_report)

        response = client.get("/goals/goal-123/progress-report?report_period_days=30")

        assert response.status_code == 200
        data = response.json()
        assert data["goal_id"] == "goal-123"
        assert data["report_period_days"] == 30
        assert "performance_metrics" in data
        assert "insights" in data


class TestDashboardsAPI:
    """Test Dashboard API endpoints"""

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_get_organization_goals_dashboard(self, mock_service):
        """Test getting organization goals dashboard"""
        mock_dashboard = {
            "organization_id": "org-123",
            "goals": [{"id": "goal-1", "title": "Goal 1"}],
            "statistics": {"total_goals": 1, "active_goals": 1},
            "upcoming_deadlines": [],
        }
        mock_service.get_organization_goals_dashboard = AsyncMock(
            return_value=mock_dashboard
        )

        response = client.get("/organizations/org-123/goals-dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == "org-123"
        assert len(data["goals"]) == 1
        assert "statistics" in data

    @patch("services.orchestrator.main.app.state.goal_tracking_service")
    def test_get_tracking_dashboard(self, mock_service):
        """Test getting tracking dashboard"""
        mock_dashboard = {
            "organization_id": "org-123",
            "summary_metrics": {"total_goals": 3, "high_risk_goals": 1},
            "risk_distribution": {"high": 1, "medium": 1, "low": 1},
            "goals_with_risk_assessment": [],
        }
        mock_service.get_organization_tracking_dashboard = AsyncMock(
            return_value=mock_dashboard
        )

        response = client.get("/organizations/org-123/tracking-dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == "org-123"
        assert "summary_metrics" in data
        assert "risk_distribution" in data


class TestErrorHandling:
    """Test error handling for Goals API"""

    @patch("services.orchestrator.main.app.state.goals_service")
    def test_service_error_handling(self, mock_service):
        """Test handling of service errors"""
        mock_service.get_goal = AsyncMock(side_effect=Exception("Database error"))

        response = client.get("/goals/goal-123")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_invalid_goal_type(self):
        """Test validation of invalid goal type"""
        invalid_data = {
            "title": "Test Goal",
            "description": "Test description",
            "goal_type": "invalid_type",  # Invalid enum value
        }

        response = client.post("/organizations/org-123/goals", json=invalid_data)

        assert response.status_code == 422

    def test_invalid_date_format(self):
        """Test validation of invalid date format"""
        invalid_data = {
            "title": "Test Goal",
            "description": "Test description",
            "target_deadline": "invalid-date-format",
        }

        response = client.post("/organizations/org-123/goals", json=invalid_data)

        assert response.status_code == 422


# Integration test fixtures and utilities
class TestGoalsAPIIntegration:
    """Integration tests for Goals API workflows"""

    @patch("services.orchestrator.main.app.state.goals_service")
    @patch("services.orchestrator.main.app.state.milestone_task_engine")
    @patch("services.orchestrator.main.app.state.goal_conversation_service")
    def test_complete_goal_workflow(
        self,
        mock_conv_service,
        mock_engine,
        mock_goals_service,
        sample_goal_data,
        sample_conversation_data,
    ):
        """Test complete workflow: create goal -> create conversation -> generate plan -> track progress"""

        # Mock service responses
        mock_goals_service.create_goal = AsyncMock(return_value="goal-123")
        mock_conv_service.create_goal_conversation = AsyncMock(return_value="conv-123")
        mock_engine.generate_goal_execution_plan = AsyncMock(
            return_value={"goal_id": "goal-123", "milestones": [], "summary": {}}
        )

        # 1. Create goal
        response = client.post("/organizations/org-123/goals", json=sample_goal_data)
        assert response.status_code == 200
        goal_id = response.json()["goal_id"]

        # 2. Create conversation
        response = client.post(
            f"/goals/{goal_id}/conversations", json=sample_conversation_data
        )
        assert response.status_code == 200
        conv_id = response.json()["conversation_id"]

        # 3. Generate execution plan
        response = client.post(f"/goals/{goal_id}/generate-execution-plan")
        assert response.status_code == 200

        # Verify all services were called
        mock_goals_service.create_goal.assert_called_once()
        mock_conv_service.create_goal_conversation.assert_called_once()
        mock_engine.generate_goal_execution_plan.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
