# FuzeAgent API Reference

## Base URL
```
http://localhost:8000
```

## Authentication
Currently, the API uses organization-level API key management. Future versions will include JWT-based authentication.

## Rate Limits
- 1000 requests per minute per organization
- 10 concurrent task executions per organization
- 5 concurrent coordination sessions per organization

## Content Type
All requests and responses use `application/json` content type.

---

## Health & Status

### Health Check
Check the health status of the FuzeAgent orchestrator service.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "orchestrator",
  "version": "2.0.0",
  "features": {
    "autonomous_execution": true,
    "multi_agent_coordination": true,
    "file_operations": true,
    "mcp_integration": true,
    "real_time_streaming": true
  }
}
```

---

## Agent Management

### Create Agent
Create a new AI agent with repository and sandbox settings.

```http
POST /agents
```

**Request Body:**
```json
{
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
}
```

**Response:**
```json
{
  "agent_id": "agent-uuid",
  "status": "created",
  "agent": {
    "id": "agent-uuid",
    "name": "Senior React Developer",
    "role": "Frontend development specialist",
    "type": "developer",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### List Agents
Get a list of all AI agents and their current status.

```http
GET /agents
```

**Response:**
```json
{
  "agents": [
    {
      "id": "agent-uuid",
      "name": "Senior React Developer",
      "role": "Frontend development specialist",
      "type": "developer",
      "status": "available",
      "current_task": null,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

### Get Agent Status
Get detailed status information for a specific agent.

```http
GET /agents/{agent_id}/status
```

**Response:**
```json
{
  "agent_id": "agent-uuid",
  "name": "Senior React Developer",
  "status": "busy",
  "current_task": {
    "id": "task-uuid",
    "title": "Implement user authentication",
    "status": "executing"
  },
  "sandbox": {
    "id": "sandbox-uuid",
    "status": "running",
    "workspace_path": "/workspaces/project"
  },
  "model_config": {
    "primary_model": "claude-3-5-sonnet-20241022",
    "temperature": 0.7
  }
}
```

---

## Task Management

### Assign Task to Agent
Assign a specific task to an AI agent.

```http
POST /agents/{agent_id}/tasks
```

**Request Body:**
```json
{
  "title": "Implement user authentication",
  "description": "Create a complete user authentication system with login, signup, and password reset functionality",
  "priority": "high",
  "metadata": {
    "estimated_hours": 8,
    "complexity": "medium"
  }
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "assigned"
}
```

### Start Autonomous Task Execution
Begin autonomous execution of a task using Claude SDK integration.

```http
POST /tasks/{task_id}/execute
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "execution_started",
  "result": {
    "execution_started": true,
    "agent_id": "agent-uuid"
  }
}
```

### Get Task Status
Get detailed task execution status.

```http
GET /tasks/{task_id}/status
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "status": "executing",
  "agent_id": "agent-uuid",
  "current_iteration": 2,
  "iterations_count": 3,
  "started_at": "2024-01-01T00:00:00Z",
  "sandbox_id": "sandbox-uuid",
  "git_branch": "feature/agent-abc123-task-def456",
  "active_execution": true
}
```

### Submit Human Response
Submit human response to a task question or approval request.

```http
POST /tasks/{task_id}/human-response
```

**Request Body:**
```json
{
  "response": "Yes, proceed with the proposed changes"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Human response submitted"
}
```

### Cancel Task Execution
Cancel autonomous execution of a task.

```http
POST /tasks/{task_id}/cancel
```

**Response:**
```json
{
  "status": "cancelled",
  "message": "Task execution cancelled"
}
```

---

## File Operations

### Get File Operations
Get file operations for a task with optional status filtering.

```http
GET /tasks/{task_id}/file-operations?status=pending
```

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `applied`)

**Response:**
```json
{
  "task_id": "task-uuid",
  "operations": [
    {
      "batch_id": "batch-uuid",
      "task_id": "task-uuid",
      "agent_id": "agent-uuid",
      "description": "Claude Code file operations",
      "requires_approval": true,
      "approval_status": "pending",
      "operations_count": 3,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Get File Operations Preview
Get preview of file changes for a batch.

```http
GET /tasks/{task_id}/file-operations/{batch_id}/preview
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "batch_id": "batch-uuid",
  "file_diffs": {
    "src/auth.js": "--- a/src/auth.js\n+++ b/src/auth.js\n@@ -1,3 +1,10 @@\n+const bcrypt = require('bcrypt');\n+const jwt = require('jsonwebtoken');\n+\n // Authentication module\n function login(username, password) {\n-  // TODO: Implement\n+  // Hash password and verify\n+  return bcrypt.compare(password, hashedPassword);\n }"
  }
}
```

### Approve File Operations
Approve or reject file operations from Claude SDK.

```http
POST /tasks/{task_id}/file-operations/{batch_id}/approve
```

**Request Body:**
```json
{
  "approved": true,
  "reason": "Changes look good and follow coding standards"
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "batch_id": "batch-uuid",
  "approved": true,
  "status": "success"
}
```

### Rollback File Operations
Rollback applied file operations.

```http
POST /tasks/{task_id}/file-operations/{batch_id}/rollback
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "batch_id": "batch-uuid",
  "status": "rolled_back"
}
```

---

## Multi-Agent Coordination

### Initiate Multi-Agent Coordination
Initiate multi-agent coordination for complex tasks.

```http
POST /tasks/{task_id}/coordinate
```

**Request Body:**
```json
{
  "coordination_mode": "collaborative",
  "required_agents": ["frontend-dev-1", "backend-dev-1"],
  "required_skills": ["frontend", "backend", "database"]
}
```

**Response:**
```json
{
  "task_id": "task-uuid",
  "coordination_session_id": "session-uuid",
  "status": "coordination_initiated",
  "coordination_mode": "collaborative"
}
```

### Get Coordination Status
Get status of a coordination session.

```http
GET /coordination/{session_id}
```

**Response:**
```json
{
  "session_id": "session-uuid",
  "root_task_id": "task-uuid",
  "coordinator": "agent-uuid",
  "participating_agents": ["agent-1", "agent-2"],
  "coordination_mode": "collaborative",
  "status": "executing",
  "subtasks": {
    "subtask-1": {
      "agent_id": "agent-1",
      "status": "completed"
    },
    "subtask-2": {
      "agent_id": "agent-2",
      "status": "executing"
    }
  },
  "started_at": "2024-01-01T00:00:00Z"
}
```

### Cancel Coordination
Cancel a coordination session.

```http
POST /coordination/{session_id}/cancel
```

**Response:**
```json
{
  "coordination_session_id": "session-uuid",
  "status": "cancelled"
}
```

### Send Agent Communication
Send communication between agents.

```http
POST /agents/{from_agent_id}/communicate/{to_agent_id}
```

**Request Body:**
```json
{
  "message_type": "request",
  "content": "Can you review the API design for the user service?",
  "metadata": {
    "priority": "high",
    "task_id": "task-uuid"
  }
}
```

**Response:**
```json
{
  "communication_id": "comm-uuid",
  "from_agent_id": "agent-1",
  "to_agent_id": "agent-2",
  "status": "sent"
}
```

---

## Model Configuration

### Store Provider API Credentials
Store encrypted API credentials for a model provider.

```http
POST /organizations/{organization_id}/providers/{provider}/credentials
```

**Request Body:**
```json
{
  "provider": "anthropic",
  "api_key": "your-anthropic-api-key",
  "endpoint_url": null,
  "additional_config": {
    "organization": "your-org-id"
  }
}
```

**Response:**
```json
{
  "organization_id": "org-uuid",
  "provider": "anthropic",
  "status": "credentials_stored",
  "message": "API credentials stored successfully"
}
```

### Get Available Models
Get available AI models for an organization.

```http
GET /organizations/{organization_id}/models?provider=anthropic&capabilities=code_generation,reasoning
```

**Query Parameters:**
- `provider` (optional): Filter by provider
- `capabilities` (optional): Filter by capabilities (comma-separated)

**Response:**
```json
{
  "organization_id": "org-uuid",
  "models": [
    {
      "model_id": "claude-3-5-sonnet-20241022",
      "provider": "anthropic",
      "name": "Claude 3.5 Sonnet",
      "description": "Most intelligent model for complex reasoning and coding",
      "capabilities": ["text_generation", "code_generation", "reasoning"],
      "context_window": 200000,
      "max_output_tokens": 8192,
      "cost_per_input_token": 0.003,
      "cost_per_output_token": 0.015,
      "has_credentials": true,
      "available": true
    }
  ],
  "count": 1
}
```

### Configure Agent Model Settings
Configure model settings and preferences for an agent.

```http
POST /agents/{agent_id}/model-configuration
```

**Request Body:**
```json
{
  "primary_model": "claude-3-5-sonnet-20241022",
  "fallback_models": ["claude-3-haiku-20240307"],
  "temperature": 0.7,
  "max_tokens": 4096,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "custom_instructions": "Always write TypeScript with strict mode enabled",
  "use_function_calling": true,
  "streaming_enabled": true,
  "cost_limit_per_task": 5.00
}
```

**Response:**
```json
{
  "agent_id": "agent-uuid",
  "status": "configured",
  "primary_model": "claude-3-5-sonnet-20241022",
  "fallback_models": ["claude-3-haiku-20240307"]
}
```

### Get Agent Model Configuration
Get current model configuration for an agent.

```http
GET /agents/{agent_id}/model-configuration
```

**Response:**
```json
{
  "agent_id": "agent-uuid",
  "configuration": {
    "primary_model": "claude-3-5-sonnet-20241022",
    "fallback_models": ["claude-3-haiku-20240307"],
    "temperature": 0.7,
    "max_tokens": 4096,
    "use_function_calling": true,
    "streaming_enabled": true,
    "cost_limit_per_task": 5.00,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### Estimate Task Cost
Estimate the cost of executing a task with the agent's model configuration.

```http
POST /agents/{agent_id}/tasks/cost-estimate
```

**Request Body:**
```json
{
  "task_description": "Implement user authentication system with JWT tokens",
  "estimated_complexity": "medium"
}
```

**Response:**
```json
{
  "agent_id": "agent-uuid",
  "model": "claude-3-5-sonnet-20241022",
  "estimated_tokens": 5000,
  "estimated_cost_usd": 0.0525,
  "complexity": "medium",
  "cost_breakdown": {
    "input_cost": 0.0105,
    "output_cost": 0.0225
  }
}
```

### Get Model Usage Statistics
Get model usage statistics and costs for an organization.

```http
GET /organizations/{organization_id}/model-usage?days=30
```

**Response:**
```json
{
  "organization_id": "org-uuid",
  "period_days": 30,
  "total_requests": 150,
  "total_tokens": 750000,
  "total_cost": 125.50,
  "model_breakdown": {
    "claude-3-5-sonnet-20241022": {
      "requests": 100,
      "tokens": 500000,
      "cost": 95.25
    },
    "claude-3-haiku-20240307": {
      "requests": 50,
      "tokens": 250000,
      "cost": 30.25
    }
  },
  "agent_breakdown": {
    "agent-1": {
      "requests": 75,
      "tokens": 375000,
      "cost": 62.75
    }
  }
}
```

---

## Goals Management

FuzeAgent includes a comprehensive Goals Management System for organizational planning and execution. This section documents all Goals-related API endpoints.

### Create Organizational Goal
Create a new strategic goal for an organization.

```http
POST /organizations/{organization_id}/goals
```

**Request Body:**
```json
{
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
  },
  "assigned_teams": ["team-1", "team-2"],
  "tags": ["revenue", "growth"],
  "metadata": {
    "business_critical": true
  }
}
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "organization_id": "org-uuid",
  "status": "created",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### List Organization Goals
Get all goals for an organization with optional filtering.

```http
GET /organizations/{organization_id}/goals?status=active&goal_type=business&limit=25
```

**Query Parameters:**
- `status` (optional): Filter by goal status (`active`, `paused`, `completed`, `cancelled`)
- `goal_type` (optional): Filter by goal type (`business`, `technical`, `operational`, `strategic`)
- `priority_min` (optional): Minimum priority level (1-10)
- `limit` (optional): Number of results to return (default: 50, max: 100)
- `offset` (optional): Number of results to skip

**Response:**
```json
{
  "organization_id": "org-uuid",
  "goals": [
    {
      "id": "goal-uuid",
      "title": "Reach $100K MRR",
      "goal_type": "business",
      "status": "active",
      "progress_percentage": 25.5,
      "target_deadline": "2024-12-31",
      "priority_level": 10,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 25,
  "offset": 0
}
```

### Get Goal Details
Get comprehensive information about a specific goal.

```http
GET /goals/{goal_id}
```

**Response:**
```json
{
  "id": "goal-uuid",
  "organization_id": "org-uuid",
  "title": "Reach $100K MRR",
  "description": "Achieve $100,000 monthly recurring revenue in 6 months",
  "goal_type": "business",
  "priority_level": 10,
  "target_value": 100000,
  "target_unit": "USD",
  "current_value": 25000,
  "progress_percentage": 25.0,
  "completion_confidence": 0.7,
  "status": "active",
  "target_deadline": "2024-12-31",
  "assigned_teams": ["team-1", "team-2"],
  "success_criteria": {
    "revenue_target": 100000,
    "sustainability": "3_consecutive_months"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Get Goal Overview
Get comprehensive overview with milestones, tasks, and progress summary.

```http
GET /goals/{goal_id}/overview
```

**Response:**
```json
{
  "goal": {
    "id": "goal-uuid",
    "title": "Reach $100K MRR",
    "progress_percentage": 25.0
  },
  "milestones": [
    {
      "id": "milestone-uuid",
      "title": "Month 1: Foundation",
      "status": "completed",
      "progress_percentage": 100.0
    }
  ],
  "tasks": [
    {
      "id": "task-uuid",
      "title": "Marketing Strategy",
      "status": "completed",
      "assigned_team": "marketing"
    }
  ],
  "summary": {
    "total_milestones": 6,
    "completed_milestones": 1,
    "total_tasks": 24,
    "completed_tasks": 4
  }
}
```

### Update Goal Progress
Update progress tracking for a goal.

```http
PUT /goals/{goal_id}/progress
```

**Request Body:**
```json
{
  "progress_percentage": 30.5,
  "current_value": 30500,
  "completion_confidence": 0.8,
  "notes": "Exceeded monthly target, ahead of schedule"
}
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "status": "updated",
  "previous_progress": 25.0,
  "current_progress": 30.5,
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Generate Goal Execution Plan
Generate comprehensive execution plan with AI-powered milestones and tasks.

```http
POST /goals/{goal_id}/generate-execution-plan
```

**Request Body (Optional):**
```json
{
  "planning_context": {
    "focus": "aggressive_growth",
    "resources": "full_team",
    "constraints": ["budget_limited", "timeline_strict"]
  }
}
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "plan_type": "monthly_focused",
  "milestones": [
    {
      "title": "Month 1: Foundation Setup",
      "target_date": "2024-02-28",
      "tasks": [
        {
          "title": "Develop Marketing Strategy",
          "function": "marketing",
          "estimated_hours": 40
        }
      ]
    }
  ],
  "summary": {
    "total_milestones": 6,
    "total_tasks": 24,
    "estimated_total_hours": 480,
    "cross_functional_areas": ["development", "marketing", "sales"]
  }
}
```

### Generate Monthly Milestones
Generate monthly milestones for a goal automatically.

```http
POST /goals/{goal_id}/generate-monthly-milestones
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "milestone_ids": [
    "milestone-1-uuid",
    "milestone-2-uuid",
    "milestone-3-uuid",
    "milestone-4-uuid",
    "milestone-5-uuid",
    "milestone-6-uuid"
  ],
  "count": 6
}
```

### Generate Cross-Functional Tasks
Generate tasks across multiple functional areas for a goal.

```http
POST /goals/{goal_id}/generate-cross-functional-tasks
```

**Request Body:**
```json
["development", "marketing", "sales", "operations"]
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "functional_tasks": {
    "development": [
      "task-dev-1-uuid",
      "task-dev-2-uuid"
    ],
    "marketing": [
      "task-marketing-1-uuid"
    ],
    "sales": [
      "task-sales-1-uuid",
      "task-sales-2-uuid"
    ],
    "operations": [
      "task-ops-1-uuid"
    ]
  },
  "total_tasks": 6
}
```

### Create Goal Conversation
Create an AI-powered planning conversation for strategic discussions.

```http
POST /goals/{goal_id}/conversations
```

**Request Body:**
```json
{
  "conversation_type": "planning",
  "conversation_title": "Strategic Planning: Path to $100K MRR",
  "initial_context": {
    "focus": "revenue_growth",
    "timeline": "6_months",
    "current_challenges": ["market_competition", "resource_constraints"]
  }
}
```

**Response:**
```json
{
  "conversation_id": "conv-uuid",
  "goal_id": "goal-uuid",
  "status": "created",
  "conversation_type": "planning"
}
```

### Get Goal Conversations
List all conversations for a goal.

```http
GET /goals/{goal_id}/conversations?conversation_type=planning&limit=10
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "conversations": [
    {
      "id": "conv-uuid",
      "conversation_title": "Strategic Planning Session",
      "conversation_type": "planning",
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 1
}
```

### Add Message to Goal Conversation
Add a message to an ongoing goal conversation.

```http
POST /conversations/{conversation_id}/messages
```

**Request Body:**
```json
{
  "message_type": "human",
  "sender_name": "Product Manager",
  "content": "What are the key risks we should consider for the Q2 targets?",
  "metadata": {
    "importance": "high",
    "topic": "risk_assessment"
  }
}
```

**Response:**
```json
{
  "message_id": "msg-uuid",
  "conversation_id": "conv-uuid",
  "status": "added",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Generate Planning Milestones from Conversation
Generate milestones based on conversation analysis.

```http
POST /conversations/{conversation_id}/generate-milestones
```

**Request Body (Optional):**
```json
{
  "planning_context": {
    "approach": "conservative",
    "risk_tolerance": "low"
  }
}
```

**Response:**
```json
{
  "conversation_id": "conv-uuid",
  "milestones": [
    {
      "title": "Market Research Completion",
      "description": "Complete comprehensive market analysis",
      "target_date": "2024-02-15"
    }
  ],
  "count": 3
}
```

### Track Goal Progress with Risk Assessment
Record detailed progress with automated risk assessment.

```http
POST /goals/{goal_id}/track-progress
```

**Request Body:**
```json
{
  "progress_percentage": 35.0,
  "current_value": 35000,
  "notes": "Strong Q1 performance, pipeline looks healthy",
  "confidence_score": 0.85,
  "trigger_alerts": true
}
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "snapshot_id": "snapshot-uuid",
  "status": "recorded",
  "progress_velocity": 0.8,
  "risk_assessment": {
    "risk_level": "low",
    "probability_of_delay": 0.15
  }
}
```

### Assess Deadline Risk
Get comprehensive risk assessment for goal completion.

```http
GET /goals/{goal_id}/deadline-risk
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "risk_level": "medium",
  "probability_of_delay": 0.35,
  "estimated_completion_date": "2025-01-15",
  "days_at_risk": 15,
  "critical_path_items": [
    {
      "type": "overdue_task",
      "id": "task-uuid",
      "title": "Marketing Campaign Launch",
      "days_overdue": 5
    }
  ],
  "mitigation_strategies": [
    {
      "strategy": "resource_reallocation",
      "description": "Assign additional team members to critical tasks",
      "impact": "reduce_risk_by_20_percent"
    }
  ]
}
```

### Generate Progress Report
Generate comprehensive progress report with insights.

```http
GET /goals/{goal_id}/progress-report?report_period_days=30
```

**Response:**
```json
{
  "goal_id": "goal-uuid",
  "goal_title": "Reach $100K MRR",
  "report_period_days": 30,
  "current_status": {
    "progress_percentage": 35.0,
    "current_value": 35000,
    "days_remaining": 150
  },
  "performance_metrics": {
    "velocity": 0.8,
    "acceleration": 0.05,
    "consistency_score": 0.75
  },
  "deadline_risk": {
    "risk_level": "medium",
    "probability_of_delay": 0.35
  },
  "progress_history": [
    {
      "date": "2024-01-01",
      "progress": 25.0,
      "notes": "Solid foundation"
    }
  ],
  "insights": [
    "Progress velocity is above target",
    "Q1 milestones completed ahead of schedule"
  ],
  "recommendations": [
    "Maintain current pace for Q2",
    "Consider accelerating marketing initiatives"
  ]
}
```

### Organization Goals Dashboard
Get comprehensive dashboard view for all organizational goals.

```http
GET /organizations/{organization_id}/goals-dashboard
```

**Response:**
```json
{
  "organization_id": "org-uuid",
  "summary_statistics": {
    "total_goals": 8,
    "active_goals": 6,
    "completed_goals": 2,
    "paused_goals": 0,
    "cancelled_goals": 0
  },
  "progress_overview": {
    "average_progress": 42.5,
    "goals_on_track": 4,
    "goals_at_risk": 2,
    "total_target_value": 500000,
    "total_current_value": 187500
  },
  "upcoming_deadlines": [
    {
      "goal_id": "goal-uuid",
      "title": "Q1 Revenue Target",
      "deadline": "2024-03-31",
      "days_remaining": 15,
      "progress": 85.0
    }
  ],
  "high_priority_goals": [
    {
      "id": "goal-uuid",
      "title": "Reach $100K MRR",
      "priority_level": 10,
      "progress": 35.0,
      "risk_level": "medium"
    }
  ]
}
```

### Organization Tracking Dashboard
Get real-time tracking dashboard with risk analysis.

```http
GET /organizations/{organization_id}/tracking-dashboard
```

**Response:**
```json
{
  "organization_id": "org-uuid",
  "summary_metrics": {
    "total_goals": 8,
    "high_risk_goals": 1,
    "medium_risk_goals": 2,
    "low_risk_goals": 5,
    "goals_requiring_attention": 2
  },
  "risk_distribution": {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 5
  },
  "goals_with_risk_assessment": [
    {
      "goal_id": "goal-uuid",
      "title": "Reach $100K MRR",
      "current_risk": "medium",
      "trend": "improving",
      "last_assessment": "2024-01-15T10:30:00Z"
    }
  ],
  "recent_alerts": [
    {
      "goal_id": "goal-uuid",
      "alert_type": "deadline_risk_increased",
      "message": "Goal deadline risk increased to medium",
      "timestamp": "2024-01-14T15:45:00Z"
    }
  ]
}
```

---

## MCP Integration

### Get MCP Tools
Get available MCP tools for organizational context.

```http
GET /mcp/tools
```

**Response:**
```json
{
  "tools": [
    {
      "name": "get_organization_structure",
      "description": "Get the complete organizational structure including teams and agents",
      "input_schema": {
        "type": "object",
        "properties": {
          "organization_id": {
            "type": "string",
            "description": "Optional organization ID to filter by"
          }
        }
      }
    }
  ]
}
```

### Call MCP Tool
Execute an MCP tool to access organizational context.

```http
POST /mcp/call-tool
```

**Request Body:**
```json
{
  "tool_name": "get_organization_structure",
  "arguments": {
    "organization_id": "org-uuid"
  }
}
```

**Response:**
```json
{
  "organizations": [
    {
      "id": "org-uuid",
      "name": "FuzeAgent Organization",
      "teams": [
        {
          "id": "team-uuid",
          "name": "Development Team Alpha",
          "agents": [
            {
              "id": "agent-uuid",
              "name": "React Developer 1",
              "type": "frontend_developer",
              "status": "available"
            }
          ]
        }
      ]
    }
  ]
}
```

---

## WebSocket Real-time APIs

### Task Status Updates
Real-time task execution updates.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/{task_id}');
```

**Message Types:**
- `status_update`: General task status changes
- `task_finished`: Task completion notification
- `error`: Error notifications

### Conversation Streaming
Real-time Claude SDK conversation streaming.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/{task_id}/conversation');
```

**Message Types:**
- `claude_output`: Real-time Claude responses
- `conversation_ended`: Session completion
- `error`: Connection or streaming errors

### File Operations Updates
Real-time file operations updates.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tasks/{task_id}/file-operations');
```

**Message Types:**
- `pending_operations`: New file operations requiring approval
- `applied_operations`: Successfully applied operations
- `task_completed`: Task completion notification

### Coordination Updates
Real-time multi-agent coordination updates.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/coordination/{session_id}');
```

**Message Types:**
- `coordination_update`: Coordination session status updates
- `coordination_finished`: Coordination completion
- `error`: Coordination errors

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common Error Codes

- `AGENT_NOT_FOUND`: Agent does not exist
- `TASK_NOT_FOUND`: Task does not exist
- `INVALID_MODEL_CONFIG`: Model configuration is invalid
- `INSUFFICIENT_CREDENTIALS`: Missing or invalid API credentials
- `COORDINATION_FAILED`: Multi-agent coordination setup failed
- `FILE_OPERATION_FAILED`: File operation could not be completed
- `SANDBOX_ERROR`: Sandbox environment issue

---

## Rate Limiting

When rate limits are exceeded, the API returns:

```http
HTTP/1.1 429 Too Many Requests
```

```json
{
  "detail": "Rate limit exceeded",
  "retry_after": 60,
  "limit": "1000 requests per minute"
}
```

---

## Pagination

For endpoints that return lists, pagination is supported:

```http
GET /agents?page=2&limit=10
```

**Response includes pagination metadata:**
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 10,
    "total": 25,
    "pages": 3,
    "has_next": true,
    "has_prev": true
  }
}
```

---

## OpenAPI/Swagger Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json