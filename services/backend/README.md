# FuzeAgent Backend Service

Backend service for FuzeAgent with SQLAlchemy, PostgreSQL, and FastAPI.

## Overview

This service provides a complete REST API for FuzeAgent, implementing the schema defined in `New - Schema.pdf`. It uses SQLAlchemy ORM to interact with PostgreSQL and FastAPI to expose a full CRUD API with pagination, search, and filtering for all tables.

## Features

- Complete database schema implementation based on the provided schema
- SQLAlchemy ORM models for all tables
- FastAPI REST API with full CRUD operations
- Pagination, search, and filtering for all endpoints
- Automatic API documentation (Swagger/OpenAPI)
- Database initialization scripts
- Connection pooling and session management

## Database Schema

The schema includes:

1. **Shared Infrastructure**
   - Entities table (global identity registry)

2. **Organizations**
   - Organizations table
   - Organization tools

3. **Teams**
   - Teams table
   - Team lead history

4. **Agents**
   - Agent templates
   - Agent environment variables
   - Agents table

5. **Containers**
   - Containers table

6. **Tools**
   - Organization-level tools
   - Tool parameters
   - Team and agent tool settings

7. **Goals & Milestones**
   - Goals table
   - Goal assignments
   - Milestones table

8. **Tasks**
   - Tasks table
   - Task assignments

9. **Conversations**
   - Conversations table (1:1 per owner)
   - Conversation messages

10. **Knowledge**
    - Unified knowledge table

## Setup

### Prerequisites

- PostgreSQL 12+ running
- Python 3.11+

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variable for database URL:
```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/fuzeagent"
```

3. Initialize the database:
```bash
python init_db.py
```

4. Start the API server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

Access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Usage

### API Endpoints

All tables have the following CRUD endpoints:

- `GET /api/{table-name}` - List all items (with pagination and search)
- `GET /api/{table-name}/{id}` - Get a single item by ID
- `POST /api/{table-name}` - Create a new item
- `PUT /api/{table-name}/{id}` - Update an existing item
- `DELETE /api/{table-name}/{id}` - Delete an item

### Query Parameters

- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)
- `search` - Search term (searches across relevant fields)

### Example API Calls

```bash
# List organizations with pagination
curl "http://localhost:8000/api/organizations?page=1&page_size=10"

# Search organizations
curl "http://localhost:8000/api/organizations?search=company"

# Get a specific organization
curl "http://localhost:8000/api/organizations/{org-id}"

# Create a new organization
curl -X POST "http://localhost:8000/api/organizations" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Company", "description": "A great company"}'

# Update an organization
curl -X PUT "http://localhost:8000/api/organizations/{org-id}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# Delete an organization
curl -X DELETE "http://localhost:8000/api/organizations/{org-id}"
```

## Using in Code

```python
from database import SessionLocal, get_db
from models import Organization, Team, Agent

# Using dependency injection
def create_organization(name: str, description: str):
    db = next(get_db())
    org = Organization(name=name, description=description)
    db.add(org)
    db.commit()
    return org

# Using context manager
from database import get_db_context

def list_teams():
    with get_db_context() as db:
        teams = db.query(Team).all()
        return teams
```

## Models

All models are defined in `models.py`. Key models include:

- `Entity` - Global identity registry
- `Organization` - Organizations
- `Team` - Teams
- `Agent` - Agents
- `AgentTemplate` - Agent templates
- `Container` - Containers
- `OrgTool` - Organization tools
- `Goal` - Goals
- `Milestone` - Milestones
- `Task` - Tasks
- `Conversation` - Conversations
- `ConversationMessage` - Conversation messages
- `Knowledge` - Knowledge items

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string (default: `postgresql://postgres:password@localhost:5432/fuzeagent`)

## Docker

Build and run with Docker:

```bash
docker build -t fuzeagent-backend .
docker run -e DATABASE_URL="your-connection-string" fuzeagent-backend
```
