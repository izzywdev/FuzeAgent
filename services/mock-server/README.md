# FuzeAgent Mock API Server

A Python FastAPI-based mock server that provides organization-scoped API endpoints for the FuzeAgent application. This server uses SQLite for data persistence and implements Bearer token authentication for organization isolation.

## Features

- **Organization-scoped data**: All endpoints filter data by organization using Bearer token authentication
- **SQLite persistence**: Data is stored in a SQLite database with persistent volume
- **FastAPI framework**: Modern, fast, and well-documented API framework
- **Docker support**: Containerized with health checks and proper networking
- **CORS enabled**: Supports cross-origin requests from the React frontend

## API Endpoints

### Organizations
- `GET /organizations` - List all organizations (no auth required)
- `POST /organizations` - Create a new organization
- `GET /organizations/{id}` - Get specific organization
- `PUT /organizations/{id}` - Update organization

### Teams (Organization-scoped)
- `GET /teams` - List teams for authenticated organization
- `POST /teams` - Create team for authenticated organization
- `GET /teams/{id}` - Get specific team (must belong to organization)
- `PUT /teams/{id}` - Update team (must belong to organization)

### Agents (Organization-scoped)
- `GET /agents` - List agents for authenticated organization
- `POST /agents` - Create agent for authenticated organization
- `GET /agents/{id}` - Get specific agent (must belong to organization)
- `PUT /agents/{id}` - Update agent (must belong to organization)

## Authentication

All organization-scoped endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer {organization_id}
```

The server validates that the organization ID exists in the database before processing requests.

## Database Schema

The server uses SQLAlchemy with the following main entities:

- **Organizations**: Top-level entities
- **Teams**: Belong to organizations
- **Agents**: Belong to teams (and thus organizations)
- **Tasks**: Can belong to teams or agents
- **Tools**: Organization-level tools with team/agent settings

## Running the Server

### With Docker Compose (Recommended)

The server is included in the main `docker-compose.yml`:

```bash
docker-compose up mock-server
```

### Standalone

```bash
cd services/mock-server
docker-compose up
```

### Development Mode

```bash
cd services/mock-server
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Environment Variables

- `DATABASE_URL`: SQLite database URL (default: `sqlite:///./data/mock_data.db`)

## Data Persistence

The SQLite database is stored in a Docker volume (`mock_data`) to ensure data persists across container restarts.

## Health Checks

The server includes health check endpoints:
- `GET /` - Basic status
- `GET /health` - Health check for Docker

## Logging

The server logs all requests and authentication events for debugging and monitoring.
