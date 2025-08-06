# FuzeAgent User Guide

## Table of Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [Core Concepts](#core-concepts)
- [Agent Management](#agent-management)
- [Model Configuration](#model-configuration)
- [Autonomous Task Execution](#autonomous-task-execution)
- [Multi-Agent Coordination](#multi-agent-coordination)
- [Real-time Monitoring](#real-time-monitoring)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

FuzeAgent is an AI team orchestration platform that enables autonomous AI development teams to collaborate on complex software projects. The platform provides:

### 🤖 **Autonomous Agent Execution**
- **Claude SDK Integration**: Interactive AI development with real-time conversation streaming
- **File Operations Engine**: Safe code changes with human approval workflows
- **Multi-Agent Coordination**: Complex task decomposition and agent collaboration

### 🏗️ **Core Features**
- **Agent Management**: Create, configure, and manage AI development agents
- **Task Orchestration**: Assign and monitor complex development tasks
- **Real-time Monitoring**: WebSocket streaming for live progress updates
- **Human-in-the-Loop**: Seamless approval workflows for critical decisions

### 🔗 **Integration Capabilities**
- **MCP (Model Context Protocol)**: Organizational context for AI agents
- **Git Workflow Management**: Automated repository operations
- **Sandbox Environments**: Isolated development containers
- **Database Integration**: PostgreSQL for persistent storage

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for development)
- PostgreSQL database
- API keys for AI model providers (Anthropic, OpenAI, etc.)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/fuzeagent.git
   cd fuzeagent
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the platform**
   ```bash
   docker-compose up -d
   ```

4. **Access the API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Management UI: http://localhost:3000

## Core Concepts

### Organizations
Organizations are the top-level entities that contain teams, agents, and manage API keys for model providers.

### Teams
Teams group related agents together and define collaborative relationships.

### Agents
AI agents are autonomous entities that can execute development tasks using configured AI models.

### Tasks
Tasks represent work items that can be assigned to agents for autonomous execution.

### Models
AI models (Claude, GPT-4, etc.) that power agent intelligence, with configurable parameters.

### Sandboxes
Isolated development environments where agents safely execute code and make changes.

## Agent Management

### Creating an Agent

```bash
curl -X POST "http://localhost:8000/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Senior React Developer",
    "role": "Frontend development specialist",
    "type": "developer",
    "config": {
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.7,
      "tools": ["code_generation", "testing", "code_review"]
    },
    "repository_settings": {
      "repository_url": "https://github.com/your-org/your-repo.git",
      "default_branch": "main"
    },
    "sandbox_settings": {
      "base_image": "fuzeagent/dev-frontend:latest",
      "resource_limits": {
        "memory": "2Gi",
        "cpu": "1.0"
      }
    }
  }'
```

### Agent Types

- **developer**: Code-focused agents (frontend, backend, full-stack)
- **executive**: Planning and coordination agents (CEO, CTO, CPO)
- **specialist**: Domain-specific agents (QA, DevOps, Design)
- **reviewer**: Code review and quality assurance agents

### Agent Status States

- **available**: Ready to accept new tasks
- **busy**: Currently executing a task
- **idle**: Online but not actively working
- **offline**: Not available for task assignment

## Model Configuration

### Setting Up API Keys

Store encrypted API credentials at the organization level:

```bash
curl -X POST "http://localhost:8000/organizations/{org_id}/providers/anthropic/credentials" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "api_key": "your-anthropic-api-key",
    "additional_config": {
      "organization": "your-org-id"
    }
  }'
```

### Supported Providers

- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Haiku
- **OpenAI**: GPT-4 Omni, GPT-4 Omni Mini
- **Google**: Gemini 1.5 Pro
- **Azure OpenAI**: Custom endpoints
- **Custom**: Self-hosted models

### Configuring Agent Models

```bash
curl -X POST "http://localhost:8000/agents/{agent_id}/model-configuration" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_model": "claude-3-5-sonnet-20241022",
    "fallback_models": ["claude-3-haiku-20240307"],
    "temperature": 0.7,
    "max_tokens": 4096,
    "use_function_calling": true,
    "streaming_enabled": true,
    "cost_limit_per_task": 5.00
  }'
```

### Model Selection Guidelines

- **Claude 3.5 Sonnet**: Complex reasoning, advanced coding, research
- **Claude 3 Haiku**: Simple tasks, cost optimization, high volume
- **GPT-4 Omni**: Multimodal tasks, function calling, analysis
- **GPT-4 Omni Mini**: Basic tasks, cost-effective operations
- **Gemini 1.5 Pro**: Long context analysis, document processing

## Autonomous Task Execution

### Creating and Executing Tasks

1. **Create a task**
   ```bash
   curl -X POST "http://localhost:8000/agents/{agent_id}/tasks" \
     -H "Content-Type: application/json" \
     -d '{
       "title": "Implement user authentication",
       "description": "Create a complete user authentication system with login, signup, and password reset functionality",
       "priority": "high",
       "metadata": {
         "estimated_hours": 8,
         "complexity": "medium"
       }
     }'
   ```

2. **Start autonomous execution**
   ```bash
   curl -X POST "http://localhost:8000/tasks/{task_id}/execute"
   ```

3. **Monitor progress via WebSocket**
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/ws/tasks/{task_id}');
   ws.onmessage = (event) => {
     const update = JSON.parse(event.data);
     console.log('Task update:', update);
   };
   ```

### Execution Flow

1. **Analysis**: Agent analyzes task requirements
2. **Setup**: Sandbox and Git environment preparation
3. **Development**: Autonomous code generation and testing
4. **Review**: Code quality checks and validation
5. **Approval**: Human review of significant changes
6. **Commit**: Git integration and pull request creation

### Human-in-the-Loop

Agents will pause execution and request human input for:
- **File Approvals**: Reviewing code changes before application
- **Clarifications**: Questions about requirements or approach
- **Decisions**: Architectural or design choices
- **Confirmations**: Potentially destructive operations

Respond to agent questions:
```bash
curl -X POST "http://localhost:8000/tasks/{task_id}/human-response" \
  -H "Content-Type: application/json" \
  -d '{
    "response": "Yes, proceed with the proposed changes"
  }'
```

## Multi-Agent Coordination

### Initiating Coordination

For complex tasks requiring multiple agents:

```bash
curl -X POST "http://localhost:8000/tasks/{task_id}/coordinate" \
  -H "Content-Type: application/json" \
  -d '{
    "coordination_mode": "collaborative",
    "required_skills": ["frontend", "backend", "database"],
    "required_agents": ["frontend-dev-1", "backend-dev-1"]
  }'
```

### Coordination Modes

- **Sequential**: Tasks executed one after another
- **Parallel**: Tasks executed simultaneously
- **Hierarchical**: Manager delegates to subordinates
- **Collaborative**: Agents work together on shared task

### Agent Communication

Agents can communicate with each other:

```bash
curl -X POST "http://localhost:8000/agents/{from_agent}/communicate/{to_agent}" \
  -H "Content-Type: application/json" \
  -d '{
    "message_type": "request",
    "content": "Can you review the API design for the user service?",
    "metadata": {
      "priority": "high",
      "task_id": "task-123"
    }
  }'
```

### Monitoring Coordination

Track multi-agent coordination in real-time:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/coordination/{session_id}');
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Coordination update:', update);
};
```

## Real-time Monitoring

### WebSocket Endpoints

- **Task Status**: `/ws/tasks/{task_id}` - General task updates
- **Conversations**: `/ws/tasks/{task_id}/conversation` - Claude SDK interactions
- **File Operations**: `/ws/tasks/{task_id}/file-operations` - Code changes
- **Coordination**: `/ws/coordination/{session_id}` - Multi-agent updates

### Monitoring Dashboard

Access the real-time monitoring dashboard at http://localhost:3000 to:
- View active agents and their status
- Monitor task execution progress
- Review file changes and approvals
- Track coordination sessions
- Analyze cost and performance metrics

## API Reference

### Core Endpoints

#### Health Check
- `GET /health` - Service health status

#### Agent Management
- `POST /agents` - Create new agent
- `GET /agents` - List all agents
- `GET /agents/{agent_id}/status` - Get agent status
- `POST /agents/{agent_id}/tasks` - Assign task to agent

#### Task Execution
- `POST /tasks/{task_id}/execute` - Start autonomous execution
- `GET /tasks/{task_id}/status` - Get execution status
- `POST /tasks/{task_id}/human-response` - Submit human response
- `POST /tasks/{task_id}/cancel` - Cancel task execution

#### File Operations
- `GET /tasks/{task_id}/file-operations` - Get file operations
- `POST /tasks/{task_id}/file-operations/{batch_id}/approve` - Approve changes
- `GET /tasks/{task_id}/file-operations/{batch_id}/preview` - Preview changes

#### Multi-Agent Coordination
- `POST /tasks/{task_id}/coordinate` - Initiate coordination
- `GET /coordination/{session_id}` - Get coordination status
- `POST /coordination/{session_id}/cancel` - Cancel coordination

#### Model Configuration
- `POST /organizations/{org_id}/providers/{provider}/credentials` - Store API keys
- `GET /organizations/{org_id}/models` - List available models
- `POST /agents/{agent_id}/model-configuration` - Configure agent model
- `GET /agents/{agent_id}/model-configuration` - Get model config
- `POST /agents/{agent_id}/tasks/cost-estimate` - Estimate task cost

### Response Formats

All API responses follow a consistent JSON format:

```json
{
  "status": "success|error",
  "data": { /* response data */ },
  "message": "Human-readable message",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Handling

HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

## Best Practices

### Agent Configuration

1. **Choose appropriate models** for agent types:
   - Use Claude 3.5 Sonnet for complex reasoning tasks
   - Use Claude 3 Haiku for simple, cost-effective operations
   - Configure fallback models for reliability

2. **Set cost limits** to prevent runaway expenses:
   ```json
   {
     "cost_limit_per_task": 10.00,
     "temperature": 0.3
   }
   ```

3. **Use custom instructions** for domain-specific behavior:
   ```json
   {
     "custom_instructions": "Always write TypeScript with strict mode enabled. Follow the existing code style in the repository."
   }
   ```

### Task Design

1. **Be specific** in task descriptions:
   ```json
   {
     "title": "Implement user authentication",
     "description": "Create JWT-based authentication with bcrypt password hashing, including login, signup, password reset, and email verification endpoints using Express.js and PostgreSQL"
   }
   ```

2. **Break down complex tasks** for better coordination:
   - Split large features into smaller, focused tasks
   - Define clear dependencies between tasks
   - Use coordination for tasks requiring multiple skills

3. **Provide context** through repository settings:
   ```json
   {
     "repository_settings": {
       "repository_url": "https://github.com/your-org/project.git",
       "default_branch": "develop",
       "coding_standards": "https://github.com/your-org/coding-standards"
     }
   }
   ```

### Cost Optimization

1. **Monitor usage** regularly:
   ```bash
   curl "http://localhost:8000/organizations/{org_id}/model-usage?days=7"
   ```

2. **Use appropriate models** for task complexity:
   - Simple tasks → Claude 3 Haiku or GPT-4 Omni Mini
   - Complex tasks → Claude 3.5 Sonnet or GPT-4 Omni

3. **Set cost limits** at agent and task levels
4. **Review and approve** significant operations

### Security

1. **Secure API keys** are encrypted at rest
2. **Use environment variables** for sensitive configuration
3. **Review file operations** before approval
4. **Monitor agent activities** for unexpected behavior
5. **Implement access controls** for production deployments

## Troubleshooting

### Common Issues

#### Agent Not Responding
```bash
# Check agent status
curl "http://localhost:8000/agents/{agent_id}/status"

# Check sandbox health
curl "http://localhost:8000/agents/{agent_id}/sandbox"

# Restart agent if needed
curl -X POST "http://localhost:8000/agents/{agent_id}/restart"
```

#### Task Execution Failures
```bash
# Get task execution details
curl "http://localhost:8000/tasks/{task_id}/status"

# Check task iterations
curl "http://localhost:8000/tasks/{task_id}/iterations"

# Review error logs
curl "http://localhost:8000/tasks/{task_id}/logs"
```

#### Model Configuration Issues
```bash
# Verify API keys
curl "http://localhost:8000/organizations/{org_id}/models"

# Test model connectivity
curl -X POST "http://localhost:8000/agents/{agent_id}/tasks/cost-estimate" \
  -d '{"task_description": "test", "estimated_complexity": "low"}'
```

#### File Operation Problems
```bash
# Check pending operations
curl "http://localhost:8000/tasks/{task_id}/file-operations?status=pending"

# Review operation details
curl "http://localhost:8000/tasks/{task_id}/file-operations/{batch_id}/preview"

# Rollback if needed
curl -X POST "http://localhost:8000/tasks/{task_id}/file-operations/{batch_id}/rollback"
```

### Getting Help

1. **Check logs**: `docker-compose logs -f orchestrator`
2. **API documentation**: http://localhost:8000/docs
3. **Health status**: http://localhost:8000/health
4. **Database status**: Check PostgreSQL connectivity
5. **File an issue**: GitHub repository issues

### Performance Tuning

1. **Adjust worker counts** in docker-compose.yml
2. **Optimize database queries** with proper indexing
3. **Configure resource limits** for sandboxes
4. **Monitor memory usage** and scale accordingly
5. **Use caching** for frequently accessed data

---

---

## Goals Management System

FuzeAgent includes a comprehensive Goals Management System for organizational planning, tracking, and execution.

### Goals Overview

The Goals Management System provides:
- **Organizational Goals**: Strategic objectives with targets and deadlines
- **AI-Powered Planning**: Automatic milestone and task generation
- **Progress Tracking**: Real-time monitoring with risk assessment
- **Conversation Support**: AI-powered planning discussions
- **Cross-functional Coordination**: Tasks across development, marketing, sales, and operations

### Creating Goals

Create organizational goals via the API:

```bash
curl -X POST http://localhost:8000/organizations/{org_id}/goals \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Reach $100K MRR",
    "description": "Achieve $100,000 monthly recurring revenue in 6 months",
    "goal_type": "business",
    "target_value": 100000,
    "target_unit": "USD",
    "target_deadline": "2024-12-31",
    "priority_level": 10,
    "success_criteria": {
      "revenue_target": 100000,
      "sustainability": "3_consecutive_months"
    }
  }'
```

### Generating Execution Plans

Automatically generate milestones and tasks:

```bash
# Generate comprehensive execution plan
curl -X POST http://localhost:8000/goals/{goal_id}/generate-execution-plan

# Generate monthly milestones
curl -X POST http://localhost:8000/goals/{goal_id}/generate-monthly-milestones

# Generate cross-functional tasks
curl -X POST http://localhost:8000/goals/{goal_id}/generate-cross-functional-tasks \
  -H "Content-Type: application/json" \
  -d '["development", "marketing", "sales", "operations"]'
```

### AI-Powered Conversations

Create strategic planning conversations:

```bash
curl -X POST http://localhost:8000/goals/{goal_id}/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_type": "planning",
    "conversation_title": "Strategic Planning Session",
    "initial_context": {"focus": "revenue_growth"}
  }'
```

### Progress Tracking

Track goal progress with detailed monitoring:

```bash
curl -X POST http://localhost:8000/goals/{goal_id}/track-progress \
  -H "Content-Type: application/json" \
  -d '{
    "progress_percentage": 25.5,
    "current_value": 25500,
    "confidence_score": 0.7,
    "notes": "Good progress this month"
  }'
```

### Risk Assessment

Get comprehensive risk analysis:

```bash
# Assess deadline risk
curl http://localhost:8000/goals/{goal_id}/deadline-risk

# Generate progress report
curl http://localhost:8000/goals/{goal_id}/progress-report?report_period_days=30
```

### Dashboards

Access organizational dashboards:

```bash
# Goals overview dashboard
curl http://localhost:8000/organizations/{org_id}/goals-dashboard

# Real-time tracking dashboard
curl http://localhost:8000/organizations/{org_id}/tracking-dashboard
```

### Goals API Endpoints

Key Goals Management endpoints:

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/organizations/{org_id}/goals` | POST | Create organizational goal |
| `/goals/{goal_id}/generate-execution-plan` | POST | Generate milestones and tasks |
| `/goals/{goal_id}/conversations` | POST | Create planning conversation |
| `/goals/{goal_id}/track-progress` | POST | Record progress update |
| `/goals/{goal_id}/deadline-risk` | GET | Assess completion risk |
| `/organizations/{org_id}/goals-dashboard` | GET | Goals overview |

---

## Next Steps

1. **Explore the API**: Use the interactive Swagger documentation at `/docs`
2. **Create your first agent**: Follow the getting started guide
3. **Set up organizational goals**: Use the Goals Management System
4. **Set up monitoring**: Configure real-time dashboards
5. **Scale your team**: Add more agents and coordination
6. **Integrate with CI/CD**: Automate your development pipeline

For more advanced topics, see our [Advanced Configuration Guide](ADVANCED_CONFIG.md) and [API Reference](API_REFERENCE.md).