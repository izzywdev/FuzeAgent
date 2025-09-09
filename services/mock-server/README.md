# FuzeAgent Mock Server v2.0

A complete rebuild of the FuzeAgent mock server using PostgreSQL, SQLAlchemy ORM, and FastAPI with full CRUD operations, pagination, search, and filtering capabilities.

## Features

- **PostgreSQL Database**: Uses the FuzeAgentMock schema with full entity management
- **SQLAlchemy ORM**: Complete model definitions matching the database schema
- **FastAPI**: Modern, fast web framework with automatic API documentation
- **Alembic Migrations**: Database schema versioning and migration management
- **Full CRUD Operations**: Create, Read, Update, Delete for all entities
- **Pagination**: Efficient pagination for large datasets
- **Search & Filtering**: Advanced search and filtering capabilities
- **Docker Support**: Containerized deployment with Docker Compose

## Database Schema

The mock server uses the `FuzeAgentMock` PostgreSQL schema with the following entities:

- **Organizations**: Top-level organizational units
- **Teams**: Teams within organizations
- **Agents**: AI agents within teams
- **Agent Templates**: Reusable agent configurations
- **Goals**: Organizational goals and objectives
- **Milestones**: Goal milestones and checkpoints
- **Tasks**: Individual tasks assigned to teams/agents
- **Knowledge**: Knowledge base items
- **Conversations**: Chat conversations
- **Tools**: Organization and team tools

## API Endpoints

### Organizations
- `GET /organizations` - List organizations with pagination
- `GET /organizations/{id}` - Get specific organization
- `POST /organizations` - Create new organization
- `PUT /organizations/{id}` - Update organization
- `DELETE /organizations/{id}` - Delete organization

### Teams
- `GET /teams` - List teams with pagination
- `GET /teams/{id}` - Get specific team
- `POST /teams` - Create new team
- `PUT /teams/{id}` - Update team
- `DELETE /teams/{id}` - Delete team

### Agents
- `GET /agents` - List agents with pagination
- `GET /agents/{id}` - Get specific agent
- `POST /agents` - Create new agent
- `PUT /agents/{id}` - Update agent
- `DELETE /agents/{id}` - Delete agent

### Agent Templates
- `GET /agent-templates` - List agent templates
- `GET /agent-templates/{id}` - Get specific template
- `POST /agent-templates` - Create new template
- `PUT /agent-templates/{id}` - Update template
- `DELETE /agent-templates/{id}` - Delete template

### Goals
- `GET /goals` - List goals with pagination
- `GET /goals/{id}` - Get specific goal
- `POST /goals` - Create new goal
- `PUT /goals/{id}` - Update goal
- `DELETE /goals/{id}` - Delete goal

### Tasks
- `GET /tasks` - List tasks with pagination
- `GET /tasks/{id}` - Get specific task
- `POST /tasks` - Create new task
- `PUT /tasks/{id}` - Update task
- `DELETE /tasks/{id}` - Delete task

### Knowledge
- `GET /knowledge` - List knowledge items
- `GET /knowledge/{id}` - Get specific knowledge item
- `POST /knowledge` - Create new knowledge item
- `PUT /knowledge/{id}` - Update knowledge item
- `DELETE /knowledge/{id}` - Delete knowledge item

## Query Parameters

All list endpoints support the following query parameters:

- `page` (int): Page number (default: 1)
- `size` (int): Page size (default: 20, max: 100)
- `sort_by` (str): Field to sort by
- `sort_order` (str): Sort order - "asc" or "desc" (default: "asc")
- `q` (str): Search query
- Entity-specific filters (e.g., `team_id`, `organization_id`, `status`)

## Installation

### Using Docker Compose (Recommended)

```bash
# Start the services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://ariWeinberg:ariWeinberg@localhost:5432/ariWeinberg"

# Run migrations
alembic upgrade head

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Database Migrations

The server uses Alembic for database migrations:

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1

# View migration history
alembic history
```

## Development

### Project Structure

```
services/mock-server/
├── alembic/                 # Database migrations
│   ├── versions/           # Migration files
│   ├── env.py             # Alembic environment
│   └── script.py.mako     # Migration template
├── models.py              # SQLAlchemy models
├── schemas.py             # Pydantic schemas
├── crud.py                # CRUD operations
├── database.py            # Database configuration
├── main.py                # FastAPI application
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Docker Compose setup
└── README.md              # This file
```

### Adding New Endpoints

1. Add the model to `models.py`
2. Add Pydantic schemas to `schemas.py`
3. Add CRUD operations to `crud.py`
4. Add API endpoints to `main.py`
5. Create and run migrations if needed

### Testing

```bash
# Run tests (when implemented)
pytest

# Test specific endpoint
curl http://localhost:8001/organizations
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `PYTHONPATH`: Python path (set to /app in Docker)

## Health Check

The server provides a health check endpoint:
- `GET /health` - Returns server status

## Breaking Changes from v1

This is a complete rebuild with the following breaking changes:

- **Database**: Changed from SQLite to PostgreSQL
- **ORM**: Changed from custom ORM to SQLAlchemy
- **API**: Completely new REST API with different endpoints
- **Schema**: Uses the FuzeAgentMock PostgreSQL schema
- **Migrations**: Now uses Alembic for database migrations

## License

Part of the FuzeAgent project.
