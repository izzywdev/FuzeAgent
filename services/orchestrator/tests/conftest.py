"""
Pytest configuration and fixtures for FuzeAgent tests
"""

import asyncio
import os
import pytest
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import asyncpg
from fastapi.testclient import TestClient
from faker import Faker

# Set test environment
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5434/ai_context_test"
os.environ["ANTHROPIC_API_KEY"] = "test-api-key"

# Import after setting environment variables
from main_with_hierarchy import app
from database import DatabaseManager
from rag_manager import RAGManager
from a2a_protocol import A2AProtocolManager
from migration_manager import MigrationManager

fake = Faker()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """FastAPI test client"""
    with TestClient(app) as c:
        yield c

@pytest.fixture
async def db_pool():
    """Database connection pool for tests"""
    database_url = os.getenv("DATABASE_URL")
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    
    # Clean up database before each test
    async with pool.acquire() as conn:
        # Drop all tables to start fresh
        await conn.execute("""
            DROP SCHEMA IF EXISTS public CASCADE;
            CREATE SCHEMA public;
            CREATE EXTENSION IF NOT EXISTS vector;
        """)
    
    yield pool
    await pool.close()

@pytest.fixture
async def migration_manager(db_pool):
    """Migration manager for tests"""
    database_url = os.getenv("DATABASE_URL")
    manager = MigrationManager(database_url)
    
    # Run migrations
    await manager.migrate_up()
    
    yield manager

@pytest.fixture
async def rag_manager(migration_manager):
    """RAG manager for tests"""
    database_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    manager = RAGManager(database_url, api_key)
    await manager.initialize()
    
    yield manager
    await manager.close()

@pytest.fixture
async def a2a_manager(migration_manager):
    """A2A protocol manager for tests"""
    database_url = os.getenv("DATABASE_URL")
    
    manager = A2AProtocolManager(database_url)
    await manager.initialize()
    
    yield manager
    await manager.close()

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = """
## Explanation
This is a test implementation.

## Implementation

### Main Code
```python
def test_function():
    return "Hello, World!"
```

### Tests
```python
def test_test_function():
    assert test_function() == "Hello, World!"
```

## Commit Message
feat: add test function
"""
    mock_client.messages.create.return_value = mock_response
    return mock_client

@pytest.fixture
def sample_organization():
    """Sample organization data"""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": fake.company(),
        "description": fake.text(max_nb_chars=200),
        "settings": {"timezone": "UTC", "currency": "USD"},
        "created_at": fake.date_time(),
        "updated_at": fake.date_time()
    }

@pytest.fixture
def sample_team():
    """Sample team data"""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "organization_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": fake.job(),
        "description": fake.text(max_nb_chars=200),
        "team_type": "development",
        "settings": {"max_agents": 10},
        "created_at": fake.date_time(),
        "updated_at": fake.date_time()
    }

@pytest.fixture
def sample_agent():
    """Sample agent data"""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "team_id": "550e8400-e29b-41d4-a716-446655440001",
        "name": fake.name(),
        "role": "Python Developer",
        "type": "python_developer",
        "status": "active",
        "config": {
            "goal": "Develop high-quality Python applications",
            "backstory": "Expert Python developer",
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.7,
            "tools": ["code_generation", "debugging"],
            "skills": ["python", "fastapi", "pytest"]
        },
        "template_id": "python_developer",
        "created_at": fake.date_time(),
        "updated_at": fake.date_time()
    }

@pytest.fixture
def sample_task():
    """Sample task data"""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "title": fake.sentence(nb_words=6),
        "description": fake.text(max_nb_chars=500),
        "assigned_to": "550e8400-e29b-41d4-a716-446655440002",
        "created_by": "user-001",
        "status": "pending",
        "priority": 5,
        "result": None,
        "created_at": fake.date_time(),
        "completed_at": None
    }

@pytest.fixture
async def setup_test_data(migration_manager, sample_organization, sample_team, sample_agent):
    """Setup test data in database"""
    # Create organization
    org_id = await DatabaseManager.create_organization(
        name=sample_organization["name"],
        description=sample_organization["description"],
        settings=sample_organization["settings"]
    )
    
    # Create team
    team_id = await DatabaseManager.create_team(
        organization_id=org_id,
        name=sample_team["name"],
        description=sample_team["description"],
        team_type=sample_team["team_type"],
        settings=sample_team["settings"]
    )
    
    # Create agent
    agent_id = await DatabaseManager.insert_agent(
        team_id=team_id,
        name=sample_agent["name"],
        role=sample_agent["role"],
        type=sample_agent["type"],
        config=sample_agent["config"],
        template_id=sample_agent["template_id"]
    )
    
    return {
        "organization_id": org_id,
        "team_id": team_id,
        "agent_id": agent_id
    }

@pytest.fixture
def temp_directory():
    """Temporary directory for file operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

# Goals Management Test Fixtures
@pytest.fixture
def sample_goal():
    """Sample goal data"""
    from datetime import date, timedelta
    return {
        "id": "550e8400-e29b-41d4-a716-446655440010",
        "organization_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Reach $100K MRR",
        "description": "Achieve $100,000 monthly recurring revenue in 6 months",
        "goal_type": "business",
        "priority_level": 10,
        "target_value": 100000,
        "target_unit": "USD",
        "current_value": 0,
        "success_criteria": {"revenue_target": 100000, "sustainability": "3_consecutive_months"},
        "start_date": date.today(),
        "target_deadline": date.today() + timedelta(days=180),
        "status": "active",
        "progress_percentage": 0,
        "completion_confidence": 0.5,
        "assigned_teams": ["team-1", "team-2"],
        "tags": ["revenue", "growth"],
        "metadata": {"business_critical": True}
    }

@pytest.fixture
def sample_milestone():
    """Sample milestone data"""
    from datetime import date, timedelta
    return {
        "id": "550e8400-e29b-41d4-a716-446655440011",
        "goal_id": "550e8400-e29b-41d4-a716-446655440010",
        "title": "Month 1: Foundation Setup",
        "description": "Establish foundational infrastructure and processes",
        "milestone_type": "checkpoint",
        "target_date": date.today() + timedelta(days=30),
        "success_criteria": {"setup_completed": True, "team_aligned": True},
        "deliverables": [{"type": "infrastructure", "description": "Basic setup completed"}],
        "dependencies": [],
        "status": "planned",
        "progress_percentage": 0,
        "assigned_teams": ["team-1"],
        "priority_level": 8,
        "weight_in_goal": 16.67
    }

@pytest.fixture
def sample_goal_task():
    """Sample goal task data"""
    from datetime import date, timedelta
    return {
        "id": "550e8400-e29b-41d4-a716-446655440012",
        "goal_id": "550e8400-e29b-41d4-a716-446655440010",
        "milestone_id": "550e8400-e29b-41d4-a716-446655440011",
        "title": "Develop marketing strategy",
        "description": "Create comprehensive marketing strategy for customer acquisition",
        "task_type": "marketing",
        "complexity_level": "high",
        "assigned_team_id": "550e8400-e29b-41d4-a716-446655440001",
        "estimated_hours": 40,
        "due_date": date.today() + timedelta(days=14),
        "status": "pending",
        "priority": 8,
        "requirements": {"deliverable": "strategy_document"},
        "acceptance_criteria": [{"criteria": "Strategy document completed and approved"}]
    }

@pytest.fixture
def sample_conversation():
    """Sample goal conversation data"""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440013",
        "goal_id": "550e8400-e29b-41d4-a716-446655440010",
        "conversation_type": "planning",
        "conversation_title": "Strategic Planning: Path to $100K MRR",
        "conversation_summary": "Initial strategic planning conversation",
        "conversation_context": {"focus": "revenue_growth", "timeline": "6_months"},
        "participants": [{"type": "agent", "id": "izzy-ai", "name": "IzzyAI", "role": "CEO"}],
        "messages": [],
        "insights_generated": [],
        "action_items": [],
        "status": "active"
    }

@pytest.fixture
def mock_goals_service():
    """Mock Goals Management Service"""
    service = AsyncMock()
    service.create_goal = AsyncMock(return_value="goal-123")
    service.get_goal = AsyncMock()
    service.list_organization_goals = AsyncMock(return_value=[])
    service.update_goal_progress = AsyncMock(return_value=True)
    service.create_milestone = AsyncMock(return_value="milestone-123")
    service.create_task_from_milestone = AsyncMock(return_value="task-123")
    service.get_goal_overview = AsyncMock()
    service.get_organization_goals_dashboard = AsyncMock()
    return service

@pytest.fixture
def mock_milestone_engine():
    """Mock Milestone Task Engine"""
    engine = AsyncMock()
    engine.generate_goal_execution_plan = AsyncMock()
    engine.generate_monthly_milestones = AsyncMock(return_value=["milestone-1", "milestone-2"])
    engine.generate_weekly_tasks_for_milestone = AsyncMock(return_value=["task-1", "task-2"])
    engine.generate_cross_functional_tasks = AsyncMock()
    return engine

@pytest.fixture
def mock_conversation_service():
    """Mock Goal Conversation Service"""
    service = AsyncMock()
    service.create_goal_conversation = AsyncMock(return_value="conv-123")
    service.get_conversation = AsyncMock()
    service.add_message_to_conversation = AsyncMock(return_value="msg-123")
    service.generate_planning_milestones = AsyncMock(return_value=[])
    service.conduct_progress_review = AsyncMock()
    service.extract_action_items_from_conversation = AsyncMock(return_value=[])
    service.get_goal_conversations = AsyncMock(return_value=[])
    return service

@pytest.fixture
def mock_tracking_service():
    """Mock Goal Tracking Service"""
    service = AsyncMock()
    service.record_progress_update = AsyncMock(return_value="snapshot-123")
    service.assess_goal_deadline_risk = AsyncMock()
    service.generate_progress_report = AsyncMock()
    service.get_organization_tracking_dashboard = AsyncMock()
    return service

# Test data factories for Goals
class GoalDataFactory:
    """Factory for creating test goal data"""
    
    @staticmethod
    def create_goal_data(**overrides):
        """Create goal data with optional overrides"""
        from datetime import date, timedelta
        
        default_data = {
            "title": "Test Goal",
            "description": "Test goal description",
            "goal_type": "business",
            "target_value": 100000,
            "target_unit": "USD",
            "target_deadline": (date.today() + timedelta(days=180)).isoformat(),
            "priority_level": 8,
            "success_criteria": {"test": True},
            "assigned_teams": ["team-1"],
            "tags": ["test"],
            "metadata": {"test_data": True}
        }
        
        return {**default_data, **overrides}

@pytest.fixture
def goal_factory():
    """Provide goal data factory"""
    return GoalDataFactory()

# Database test utilities for Goals
class DatabaseTestUtils:
    """Utilities for database testing"""
    
    @staticmethod
    def mock_database_row(data_dict):
        """Convert dict to mock database row"""
        row = MagicMock()
        for key, value in data_dict.items():
            setattr(row, key, value)
            row[key] = value  # Support both attribute and dict access
        return row
    
    @staticmethod
    def create_mock_goal_row():
        """Create a mock goal database row"""
        import uuid
        from datetime import date, datetime, timedelta
        from decimal import Decimal
        
        return DatabaseTestUtils.mock_database_row({
            'id': str(uuid.uuid4()),
            'organization_id': str(uuid.uuid4()),
            'title': 'Mock Goal',
            'description': 'Mock goal description',
            'goal_type': 'business',
            'priority_level': 8,
            'target_value': Decimal('100000'),
            'target_unit': 'USD',
            'current_value': Decimal('25000'),
            'success_criteria': '{"target_achieved": true}',
            'start_date': date.today(),
            'target_deadline': date.today() + timedelta(days=150),
            'actual_completion_date': None,
            'status': 'active',
            'progress_percentage': Decimal('25.0'),
            'completion_confidence': Decimal('0.7'),
            'assigned_teams': ['team-1', 'team-2'],
            'goal_owner_agent_id': None,
            'stakeholder_agents': [],
            'tags': ['test', 'mock'],
            'metadata': '{"test": true}',
            'created_by': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })

@pytest.fixture
def db_utils():
    """Provide database test utilities"""
    return DatabaseTestUtils()

# Markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.api = pytest.mark.api
pytest.mark.rag = pytest.mark.rag
pytest.mark.a2a = pytest.mark.a2a
pytest.mark.database = pytest.mark.database
pytest.mark.slow = pytest.mark.slow
pytest.mark.goals = pytest.mark.goals