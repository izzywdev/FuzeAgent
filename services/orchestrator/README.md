# FuzeAgent Services

This directory contains the various services that make up the FuzeAgent platform.

## Services

1. [Orchestrator](./README.md) - Main orchestration service for AI agents
2. [Database](./database_service/README.md) - Standalone PostgreSQL database service

## Quick Start

To run the entire FuzeAgent platform, use Docker Compose:

```bash
docker-compose up -d
```

This will start all services including:
- PostgreSQL database
- Redis for caching
- RabbitMQ for messaging
- The orchestrator service

## Database Service

The database service is a standalone PostgreSQL database with all the necessary schema for the FuzeAgent platform. It includes:

- Core tables for organizations, teams, agents, tasks, and conversations
- Model configuration and API key management tables
- Usage tracking and analytics tables
- Automatic extension installation (uuid-ossp, vector)

For detailed information on the database service, see the [Database Service README](./database_service/README.md).

### Database Management Script

The database service includes a convenient management script (`database_service/dbctl.sh`) for common operations:

```bash
# Build and run the database service
./database_service/dbctl.sh build
./database_service/dbctl.sh run

# Check status
./database_service/dbctl.sh status

# View logs
./database_service/dbctl.sh logs

# Connect with psql
./database_service/dbctl.sh psql
```