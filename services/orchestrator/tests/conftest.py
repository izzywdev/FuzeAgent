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

# Markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.api = pytest.mark.api
pytest.mark.rag = pytest.mark.rag
pytest.mark.a2a = pytest.mark.a2a
pytest.mark.database = pytest.mark.database
pytest.mark.slow = pytest.mark.slow