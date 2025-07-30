# FuzeAgent Testing Guide

This document provides comprehensive information about the testing framework for the FuzeAgent orchestrator service.

## Overview

The FuzeAgent test suite includes comprehensive coverage for:
- **API Endpoints**: Organizations, Teams, Agents, Templates
- **RAG System**: Conversation storage, knowledge management, semantic search
- **A2A Protocol**: Agent-to-agent communication and task delegation
- **Migration System**: Database schema migrations and version management
- **Claude SDK Integration**: AI-powered code generation and development
- **MCP Server**: Model Context Protocol integration for Claude Desktop

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest configuration and fixtures
├── test_api_organizations.py      # Organization API tests
├── test_api_teams.py             # Team API tests
├── test_api_agents.py            # Agent API tests
├── test_api_templates.py         # Agent template API tests
├── test_rag_manager.py           # RAG system functionality tests
├── test_a2a_protocol.py          # A2A protocol tests
├── test_migration_manager.py     # Database migration tests
├── test_claude_code_wrapper.py   # Claude SDK wrapper tests
└── test_mcp_server.py            # MCP server tests
```

## Test Categories

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (require services)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.database` - Tests requiring database connection
- `@pytest.mark.rag` - RAG system tests
- `@pytest.mark.a2a` - A2A protocol tests
- `@pytest.mark.mcp` - MCP server tests
- `@pytest.mark.slow` - Slow-running tests

## Quick Start

### Prerequisites

1. **Python 3.11+** with required dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio pytest-cov faker httpx
   ```

2. **Docker and Docker Compose** for integration tests

### Running Tests

#### Option 1: Quick Unit Tests (Fastest)
```bash
# Run unit tests only (no external services required)
./scripts/test-quick.sh unit
```

#### Option 2: Full Test Suite
```bash
# Run all tests with Docker infrastructure
./scripts/run-tests.sh
```

#### Option 3: Specific Test Categories
```bash
# Run specific test types
./scripts/test-quick.sh api
./scripts/test-quick.sh rag
./scripts/test-quick.sh a2a
```

#### Option 4: Manual pytest Commands
```bash
# Unit tests only
pytest tests/ -m "unit" -v

# API tests (requires test database)
pytest tests/ -m "api" -v

# All tests with coverage
pytest tests/ --cov=. --cov-report=html
```

## Test Infrastructure

### Docker Test Environment

The test suite uses isolated Docker containers:

```bash
# Start test infrastructure
docker-compose -f test_docker-compose.yml up -d

# Run tests
./scripts/run-tests.sh

# Cleanup
docker-compose -f test_docker-compose.yml down -v
```

**Test services:**
- **PostgreSQL** with pgvector extension (port 5434)
- **Redis** for caching (port 6380)
- **Test API service** (port 8001)

### Test Database

The test database is automatically configured with:
- Vector extension for RAG functionality
- UUID extension for ID generation
- Separate database (`ai_context_test`) to avoid conflicts
- Automatic migrations before test runs

## Test Configuration

### Environment Variables

```bash
# Required for all tests
export TESTING=1
export ANTHROPIC_API_KEY="test-api-key"

# For integration tests
export DATABASE_URL="postgresql://postgres:password@localhost:5434/ai_context_test"
export REDIS_URL="redis://localhost:6380"
```

### pytest.ini Configuration

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    api: API endpoint tests
    rag: RAG functionality tests
    a2a: A2A protocol tests
    mcp: MCP functionality tests
    database: Tests requiring database
    slow: Slow running tests
```

## Writing Tests

### Test Structure Example

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.api
@pytest.mark.database
class TestAgentsAPI:
    """Test Agent API endpoints"""
    
    def test_create_agent(self, client: TestClient, setup_test_data):
        """Test creating a new agent"""
        # Test implementation
        pass
```

### Available Fixtures

**Core Fixtures:**
- `client` - FastAPI test client
- `db_pool` - Database connection pool
- `migration_manager` - Database migration manager
- `rag_manager` - RAG system manager
- `a2a_manager` - A2A protocol manager

**Mock Fixtures:**
- `mock_anthropic_client` - Mocked Anthropic API client
- `sample_organization` - Sample organization data
- `sample_team` - Sample team data
- `sample_agent` - Sample agent data

**Utility Fixtures:**
- `temp_directory` - Temporary directory for file tests
- `setup_test_data` - Pre-populated test data

### Test Data Management

Tests use the Faker library for generating realistic test data:

```python
from faker import Faker
fake = Faker()

def test_with_fake_data():
    org_name = fake.company()
    user_email = fake.email()
    # Use in test
```

## Coverage Reports

### Generating Coverage Reports

```bash
# HTML coverage report
pytest --cov=. --cov-report=html tests/

# Terminal coverage report
pytest --cov=. --cov-report=term-missing tests/

# XML coverage report (for CI)
pytest --cov=. --cov-report=xml tests/
```

Coverage reports are generated in:
- `htmlcov/index.html` - Interactive HTML report
- `coverage.xml` - XML report for CI systems

### Coverage Targets

- **Overall Coverage**: >85%
- **API Endpoints**: >95%
- **Core Business Logic**: >90%
- **Integration Points**: >80%

## Continuous Integration

### GitHub Actions Workflow

The CI pipeline runs:

1. **Unit Tests** - Fast tests without external dependencies
2. **Integration Tests** - Tests with database and Redis  
3. **API Tests** - Full API endpoint coverage
4. **RAG/A2A Tests** - Advanced functionality tests
5. **Security Scanning** - Bandit and Safety checks
6. **Code Quality** - Black, isort, flake8, mypy
7. **Docker Build** - Container build verification

### Running CI Locally

```bash
# Install act (GitHub Actions runner)
# https://github.com/nektos/act

# Run the full CI pipeline
act push

# Run specific jobs
act -j test
act -j lint
```

## Performance Testing

### Benchmark Tests

```bash
# Run performance benchmarks
pytest tests/ --benchmark-only

# Compare benchmark results
pytest tests/ --benchmark-compare=0001
```

### Load Testing

For API load testing, use the included load test scripts:

```bash
# Start test infrastructure
docker-compose -f test_docker-compose.yml up -d fuzeagent-test-api

# Run load tests (requires additional tools)
pip install locust
locust -f tests/load_tests.py --host http://localhost:8001
```

## Debugging Tests

### Common Issues

1. **Port Conflicts**
   ```bash
   # Check for port usage
   netstat -tulpn | grep :5434
   
   # Kill conflicting processes
   sudo fuser -k 5434/tcp
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connectivity
   psql -h localhost -p 5434 -U postgres -d ai_context_test -c "SELECT 1;"
   ```

3. **Migration Failures**
   ```bash
   # Reset test database
   docker-compose -f test_docker-compose.yml down -v
   docker-compose -f test_docker-compose.yml up -d
   ```

### Debug Mode

```bash
# Run tests with debug output
pytest tests/ -v -s --tb=long

# Run single test with debugging
pytest tests/test_api_agents.py::TestAgentsAPI::test_create_agent -v -s
```

### Using pdb Debugger

```python
def test_with_debugging():
    import pdb; pdb.set_trace()
    # Test code here
```

## Contributing

### Test Requirements for New Features

1. **Unit tests** for all new functions/classes
2. **Integration tests** for API endpoints
3. **Error handling tests** for edge cases
4. **Performance tests** for critical paths
5. **Documentation** for complex test scenarios

### Test Review Checklist

- [ ] Tests follow naming conventions
- [ ] Appropriate test markers are used
- [ ] Tests are isolated and don't depend on each other
- [ ] Mock external dependencies appropriately
- [ ] Include both positive and negative test cases
- [ ] Add performance tests for new features
- [ ] Update this documentation if needed

## Troubleshooting

### Common Test Failures

**Database connection timeouts:**
```bash
# Increase Docker resources or check network connectivity
docker-compose -f test_docker-compose.yml logs fuzeagent-test-db
```

**Import errors:**
```bash
# Ensure PYTHONPATH includes current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Async test issues:**
```bash
# Ensure pytest-asyncio is installed and configured
pip install pytest-asyncio
```

### Getting Help

1. Check test logs: `./scripts/run-tests.sh -v`
2. Run individual test files: `pytest tests/test_specific.py -v`
3. Check Docker logs: `docker-compose -f test_docker-compose.yml logs`
4. Review CI pipeline results in GitHub Actions

For additional support, check the main project documentation or open an issue in the repository.