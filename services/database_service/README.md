# FuzeAgent Database Service

The FuzeAgent Database Service is a standalone PostgreSQL database that stores all the data for the FuzeAgent AI team orchestration platform. This service is designed to be run as a Docker container and includes all the necessary schema and initialization scripts.

## Table of Contents

- [Overview](#overview)
- [Database Schema](#database-schema)
- [Running the Database Service](#running-the-database-service)
- [Connecting to the Database](#connecting-to-the-database)
- [Database Migrations](#database-migrations)
- [Backup and Restore](#backup-and-restore)
- [Troubleshooting](#troubleshooting)

## Overview

The database service is built on PostgreSQL 15 and includes the following features:

- Core tables for organizations, teams, agents, tasks, and conversations
- Model configuration and API key management tables
- Usage tracking and analytics tables
- Automatic extension installation (uuid-ossp, vector)
- Health checks
- Initialization scripts

## Database Schema

The database schema includes the following main tables:

### Core Tables

1. **organizations** - Store organization information
2. **teams** - Store team information within organizations
3. **agents** - Store AI agent information
4. **tasks** - Store tasks assigned to agents
5. **chat_sessions** - Store chat session information
6. **agent_conversations** - Store individual messages in chat sessions

### Model Configuration Tables

1. **organization_provider_credentials** - Store encrypted API credentials for model providers
2. **agent_model_configurations** - Store model configuration for each agent
3. **model_usage_logs** - Track model usage for billing and analytics
4. **model_usage_daily_aggregates** - Daily aggregated usage statistics

### Views

1. **organization_model_usage_summary** - Summary of model usage by organization
2. **agent_model_usage_summary** - Summary of model usage by agent

## Running the Database Service

### Prerequisites

- Docker installed on your system
- Docker Compose (optional, but recommended)

### Using the Management Script (Recommended)

The easiest way to manage the database service is using the provided management script:

```bash
# Build the database image
./database_service/dbctl.sh build

# Run the database container
./database_service/dbctl.sh run

# Check the status
./database_service/dbctl.sh status
```

### Using Docker Run

To run the database service using Docker:

```bash
docker build -t fuzeagent-db ./database_service
docker run -d \
  --name fuzeagent-db \
  -p 5432:5432 \
  -e POSTGRES_DB=ai_context \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  fuzeagent-db
```

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  database:
    build:
      context: ./database_service
    container_name: fuzeagent-db
    environment:
      POSTGRES_DB: ai_context
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d ai_context"]
      interval: 30s
      timeout: 30s
      retries: 3

volumes:
  db_data:
```

Then run:

```bash
docker-compose up -d
```

## Connecting to the Database

### Connection Parameters


- Host: localhost (or the Docker host)
- Port: 5432
- Database: ai_context
- Username: postgres
- Password: password

### Using psql

```bash
psql -h localhost -p 5432 -U postgres -d ai_context
```

### Using Python (asyncpg)

```python
import asyncpg
import asyncio

async def connect_to_db():
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="password",
        database="ai_context"
    )
    return conn

# Example usage
async def main():
    conn = await connect_to_db()
    # Your database operations here
    await conn.close()

asyncio.run(main())
```

### Environment Variables

The database service uses the following environment variables:

- `POSTGRES_DB` - Database name (default: ai_context)
- `POSTGRES_USER` - Database user (default: postgres)
- `POSTGRES_PASSWORD` - Database password (default: password)

## Database Migrations

The database schema is automatically initialized when the container starts for the first time. For subsequent schema changes, you can create additional SQL files in the `init-scripts` directory with a numbered prefix (e.g., `03-add-new-table.sql`).

### Adding New Tables

To add new tables:

1. Create a new SQL file in `init-scripts` with the next number in sequence
2. Add your `CREATE TABLE` statements
3. Add appropriate indexes
4. Rebuild and restart the container

Example migration file (`03-example-table.sql`):

```sql
-- Create example table
CREATE TABLE IF NOT EXISTS example_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_example_name ON example_table(name);
```

## Backup and Restore

### Backup

To create a backup of the database:

```bash
docker exec fuzeagent-db pg_dump -U postgres ai_context > backup.sql
```

For a compressed backup:

```bash
docker exec fuzeagent-db pg_dump -U postgres -Fc ai_context > backup.dump
```

### Restore

To restore from a backup:

```bash
docker exec -i fuzeagent-db psql -U postgres ai_context < backup.sql
```

For a compressed backup:

```bash
docker exec -i fuzeagent-db pg_restore -U postgres -d ai_context < backup.dump
```

### Automated Backups

For production use, consider setting up automated backups using a cron job:

```bash
# Daily backup at 2 AM
0 2 * * * docker exec fuzeagent-db pg_dump -U postgres ai_context > /backups/backup-$(date +%Y%m%d).sql
```

## Troubleshooting

### Common Issues

1. **Connection refused**: Ensure the container is running and the port is correctly mapped
2. **Authentication failed**: Check the username and password
3. **Database does not exist**: Verify the `POSTGRES_DB` environment variable

### Checking Container Status

Using the management script:
```bash
./database_service/dbctl.sh status
```

Or using Docker directly:
```bash
docker ps
```

### Viewing Logs

Using the management script:
```bash
./database_service/dbctl.sh logs
```

Or using Docker directly:
```bash
docker logs fuzeagent-db
```

### Connecting to Container Shell

```bash
docker exec -it fuzeagent-db sh
```

### Health Check

The container includes a health check that can be viewed with:

```bash
docker inspect fuzeagent-db | grep Health
```

## Utilities

The database service includes several utility scripts to help with common database operations:

### Test Connection Script

A simple script to test the database connection and perform basic operations:

```bash
cd database_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python test_connection.py
```

### Sample Data Initialization Script

A script to initialize the database with sample data for testing and development:

```bash
cd database_service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_sample_data.py
```

### Migration Script

A script to handle database schema migrations:

```bash
cd database_service
python3 -m venv venv
source venv/bin/activate
pip install -r migrate_requirements.txt
python migrate.py
```

## Development

### Modifying the Schema

1. Update the SQL files in `init-scripts`
2. Rebuild the Docker image
3. Restart the container (note: this will recreate the database)

### Testing Changes

For development, you can mount the init-scripts directory as a volume:

```bash
docker run -d \
  --name fuzeagent-db \
  -p 5432:5432 \
  -e POSTGRES_DB=ai_context \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -v $(pwd)/database_service/init-scripts:/docker-entrypoint-initdb.d \
  fuzeagent-db
```

This allows you to modify the SQL files and restart the container to test changes without rebuilding the image.