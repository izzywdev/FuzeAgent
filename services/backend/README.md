# FuzeAgent Backend Service

Backend service for FuzeAgent with SQLAlchemy and PostgreSQL.

## Overview

This service provides the core database layer for FuzeAgent, implementing the schema defined in `New - Schema.pdf`. It uses SQLAlchemy ORM to interact with PostgreSQL.

## Features

- Complete database schema implementation based on the provided schema
- SQLAlchemy ORM models for all tables
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

## Usage

### Initialize Database

Run the initialization script to create all tables:

```bash
python init_db.py
```

### Using in Code

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
