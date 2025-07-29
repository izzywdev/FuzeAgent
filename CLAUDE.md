# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

FuzeAgent is an AI team orchestration platform that creates and manages autonomous AI agents using Claude Code SDK. The system implements a distributed architecture where multiple AI agents collaborate to complete complex software development tasks, with a digital CEO (IzzyAI) coordinating the team.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Management UI                            │
│                    (React + WebSocket + D3.js)                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                    API Gateway (Kong/Traefik)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                 Orchestration Service (FastAPI)                  │
│                        + CrewAI Core                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      Message Queue (RabbitMQ)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                        Agent Containers                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  IzzyAI CEO │  │   CTO Agent │  │  CPO Agent  │  ...       │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │Frontend Dev1│  │Frontend Dev2│  │Backend Dev1 │  ...       │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└──────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                     Shared Services                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐       │
│  │Context Store │  │  MCP Servers │  │  Code Storage  │       │
│  │  (Postgres)  │  │   (Node.js)  │  │   (GitLab)    │       │
│  └──────────────┘  └──────────────┘  └────────────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

## Common Development Commands

### Infrastructure Setup
```bash
# Quick setup (run first time)
./setup.sh

# Start core infrastructure
docker-compose up -d postgres rabbitmq redis

# Start orchestration service
docker-compose up -d orchestrator

# Start management UI
docker-compose up -d ui

# Full stack startup
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Check service status
docker-compose ps
```

### Agent Management
```bash
# Create new agent via API
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Frontend Dev 1",
    "role": "Senior React Developer",
    "type": "developer",
    "config": {
      "goal": "Build responsive React components",
      "tools": ["code_generation", "code_review"],
      "model": "claude-opus-4-20250514"
    }
  }'

# List all agents
curl http://localhost:8000/agents

# Get agent status
curl http://localhost:8000/agents/{agent_id}/status

# Assign task to agent
curl -X POST http://localhost:8000/agents/{agent_id}/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Implement user dashboard",
    "description": "Create a responsive dashboard component",
    "type": "implement_feature"
  }'
```

### Database Operations
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d ai_context

# Run database migrations (when implemented)
docker-compose exec orchestrator python -m alembic upgrade head

# Backup database
docker-compose exec postgres pg_dump -U postgres ai_context > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres ai_context < backup.sql
```

### Development Workflow
```bash
# Build all containers
docker-compose build

# Build specific service
docker-compose build orchestrator

# View real-time agent updates
# Navigate to http://localhost:3000 for WebSocket dashboard

# Monitor message queue
# Navigate to http://localhost:15672 (admin/password from .env)

# Check orchestrator health
curl http://localhost:8000/health
```

## Key Components

### Orchestration Service (FastAPI)
- **Location**: `services/orchestrator/`
- **Main Entry**: `main.py` - FastAPI application with WebSocket support
- **Agent Manager**: `agent_manager.py` - CrewAI integration for agent lifecycle
- **Task Queue**: `task_queue.py` - RabbitMQ task distribution
- **Claude Code Wrapper**: `claude_code_wrapper.py` - Bridge to Claude Code SDK

### Management UI (React)
- **Location**: `services/ui/`
- **Dashboard**: Real-time agent status and task monitoring
- **Team Hierarchy**: D3.js visualization of agent relationships
- **Agent Creation**: Forms for spawning new AI agents
- **WebSocket Context**: Live updates from orchestration service

### Agent Containers
- **Base Container**: `containers/base-agent/` - Common agent functionality
- **Developer Agents**: `containers/developer-agent/` - Code-focused agents with Claude Code
- **Executive Agents**: `containers/executive-agent/` - Planning and coordination agents

### Database Schema
- **Agents Table**: Registry of all AI agents and configurations
- **Tasks Table**: Task assignments, status, and results
- **Interactions Table**: Agent communication history with vector embeddings
- **Agent Hierarchy Table**: Organizational relationships between agents

## Agent Types and Capabilities

### Executive Agents
- **CEO (IzzyAI)**: Strategic planning, resource allocation, team management
- **CTO**: Technical architecture, developer coordination
- **CPO**: Product planning, design oversight, quality assurance

### Developer Agents
- **Frontend Developers**: React, TypeScript, UI/UX implementation
- **Backend Developers**: FastAPI, database design, API development
- **Full-Stack Developers**: End-to-end feature implementation

### Specialist Agents
- **QA Engineers**: Test generation, automation, bug reporting
- **DevOps Engineers**: Infrastructure, deployment, monitoring
- **Designers**: UI mockups, accessibility, design systems

## Task Distribution System

### Task Analysis
Tasks are automatically analyzed for:
- Required skills and expertise
- Complexity level (low/medium/high)
- Estimated completion time
- Dependencies on other tasks
- Recommended agent types

### Task Decomposition
Complex tasks are broken down into subtasks:
- Each subtask assigned to appropriate agent type
- Dependencies tracked and enforced
- Progress monitored in real-time
- Results aggregated and validated

### Agent Selection
Agents are selected based on:
- Current workload and availability
- Skill match for task requirements
- Historical performance on similar tasks
- Team hierarchy and reporting structure

## Environment Configuration

### Required Environment Variables
```bash
# API Keys
ANTHROPIC_API_KEY=your-claude-api-key

# Database
POSTGRES_PASSWORD=secure-password
DATABASE_URL=postgresql://postgres:password@postgres:5432/ai_context

# Message Queue
RABBITMQ_PASSWORD=secure-password
RABBITMQ_URL=amqp://admin:password@rabbitmq:5672/

# Cache
REDIS_URL=redis://redis:6379

# Security
JWT_SECRET=your-jwt-secret
```

### Service Endpoints
- **Management UI**: http://localhost:3000
- **Orchestrator API**: http://localhost:8000
- **RabbitMQ Management**: http://localhost:15672
- **Database**: localhost:5432
- **Redis**: localhost:6379

## Monitoring and Observability

### Grafana Dashboards
- **Agent Performance**: Task completion rates, utilization metrics
- **System Health**: Resource usage, error rates, response times
- **Cost Tracking**: API token usage, operational expenses
- **Team Productivity**: Individual and collective agent metrics

### Logging
- **Structured Logs**: JSON format with correlation IDs
- **Log Aggregation**: Loki for centralized log collection
- **Real-time Monitoring**: Prometheus metrics with alerting

## Development Guidelines

### Adding New Agent Types
1. Create container in `containers/[agent-type]-agent/`
2. Implement agent class with CrewAI integration
3. Add agent type to orchestrator configuration
4. Update UI components for new agent type
5. Define appropriate tools and capabilities

### Task Type Implementation
1. Add task type to `task_distributor.py`
2. Implement task handler in relevant agent containers
3. Update database schema if needed
4. Add UI components for task management
5. Test task distribution and completion

### Scaling Considerations
- **Horizontal Scaling**: Use Kubernetes HPA for agent containers
- **Database Optimization**: Implement connection pooling and read replicas
- **Caching Strategy**: Redis for frequently accessed agent data
- **Load Balancing**: Traefik for distributing API requests

## Security Best Practices

### API Security
- JWT-based authentication for all endpoints
- Rate limiting on agent creation and task assignment
- Input validation for all agent configurations
- Audit logging for administrative actions

### Container Security
- Non-root users in all containers
- Minimal base images with security updates
- Resource limits to prevent resource exhaustion
- Network policies for inter-service communication

### Data Protection
- Encrypted connections between all services
- Secure storage of API keys and credentials
- Regular backups with encryption at rest
- PII handling compliance for agent interactions

## Troubleshooting

### Common Issues

**Agent Creation Fails**
- Check ANTHROPIC_API_KEY is valid
- Verify database connectivity
- Ensure RabbitMQ is running
- Check container resource limits

**Tasks Not Processing**
- Verify agent container status: `docker-compose ps`
- Check RabbitMQ queues: http://localhost:15672
- Review orchestrator logs: `docker-compose logs orchestrator`
- Validate task format and agent compatibility

**UI Not Updating**
- Check WebSocket connection in browser dev tools
- Verify orchestrator WebSocket endpoint
- Restart UI service: `docker-compose restart ui`
- Clear browser cache and refresh

**Database Connection Issues**
- Ensure PostgreSQL is running: `docker-compose ps postgres`
- Check database URL in environment variables
- Verify pgvector extension is installed
- Test connection: `docker-compose exec postgres psql -U postgres -d ai_context`

### Performance Optimization
- Monitor agent utilization via Grafana dashboards
- Scale agent containers based on task queue length
- Optimize database queries with proper indexing
- Implement caching for frequently accessed data
- Use connection pooling for database access

### Cost Management
- Monitor API token usage in real-time
- Set spending limits and alerts
- Optimize agent model selection (GPT-4 vs Claude)
- Implement task prioritization to reduce unnecessary API calls
- Use local models for simple tasks when possible

This platform provides a foundation for building and scaling autonomous AI development teams using Claude Code SDK.