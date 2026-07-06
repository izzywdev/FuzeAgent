# FuzeAgent API Documentation

This document describes the API endpoints used by the FuzeAgent UI. The UI communicates with two main services:
1. **Orchestrator API** - Handles agents, tasks, and orchestration (port 8000)
2. **Hierarchy API** - Handles organizations, teams, and structure (port 8006)

In production, these are accessed through nginx proxy at `/api`.

## Base URLs

- **Development**: 
  - Orchestrator API: `http://localhost:8000`
  - Hierarchy API: `http://localhost:8006`
- **Production**: 
  - Both APIs: `https://your-domain.com/api`

## Authentication

All API requests require authentication via HTTP headers. The UI handles this automatically.

## Endpoints

### 1. Organizations

#### Get Organizations
- **Method**: `GET`
- **Path**: `/organizations`
- **Service**: Hierarchy API
- **Description**: Retrieve all organizations
- **Response**:
  ```json
  [
    {
      "id": "string",
      "name": "string",
      "description": "string (optional)",
      "settings": "object",
      "created_at": "string (ISO 8601)",
      "updated_at": "string (ISO 8601)",
      "team_count": "number (optional)",
      "agent_count": "number (optional)"
    }
  ]
  ```

#### Create Organization
- **Method**: `POST`
- **Path**: `/organizations`
- **Service**: Hierarchy API
- **Description**: Create a new organization
- **Request Body**:
  ```json
  {
    "name": "string",
    "description": "string (optional)",
    "settings": "object (optional)"
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "name": "string",
    "description": "string (optional)",
    "settings": "object",
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Update Organization
- **Method**: `PUT`
- **Path**: `/organizations/{id}`
- **Service**: Hierarchy API
- **Description**: Update an existing organization
- **Request Body**:
  ```json
  {
    "name": "string (optional)",
    "description": "string (optional)",
    "settings": "object (optional)"
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "name": "string",
    "description": "string (optional)",
    "settings": "object",
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Delete Organization
- **Method**: `DELETE`
- **Path**: `/organizations/{id}`
- **Service**: Hierarchy API
- **Description**: Delete an organization
- **Response**: `true` if successful

### 2. Teams

#### Get Teams
- **Method**: `GET`
- **Path**: `/teams`
- **Service**: Hierarchy API
- **Description**: Retrieve all teams, optionally filtered by organization
- **Query Parameters**:
  - `organization_id` (optional): Filter teams by organization ID
- **Response**:
  ```json
  [
    {
      "id": "string",
      "organization_id": "string",
      "name": "string",
      "description": "string (optional)",
      "team_type": "string (development|qa|design|management|general)",
      "settings": "object",
      "created_at": "string (ISO 8601)",
      "updated_at": "string (ISO 8601)",
      "organization_name": "string (optional)",
      "agent_count": "number (optional)"
    }
  ]
  ```

#### Get Team by ID
- **Method**: `GET`
- **Path**: `/teams/{id}`
- **Service**: Hierarchy API
- **Description**: Retrieve a specific team
- **Response**:
  ```json
  {
    "id": "string",
    "organization_id": "string",
    "name": "string",
    "description": "string (optional)",
    "team_type": "string",
    "settings": "object",
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Create Team
- **Method**: `POST`
- **Path**: `/teams`
- **Service**: Hierarchy API
- **Description**: Create a new team
- **Request Body**:
  ```json
  {
    "organization_id": "string",
    "name": "string",
    "description": "string (optional)",
    "team_type": "string (optional)",
    "settings": "object (optional)"
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "organization_id": "string",
    "name": "string",
    "description": "string (optional)",
    "team_type": "string",
    "settings": "object",
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Update Team
- **Method**: `PUT`
- **Path**: `/teams/{id}`
- **Service**: Hierarchy API
- **Description**: Update an existing team
- **Request Body**:
  ```json
  {
    "name": "string (optional)",
    "description": "string (optional)",
    "team_type": "string (optional)",
    "settings": "object (optional)"
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "organization_id": "string",
    "name": "string",
    "description": "string (optional)",
    "team_type": "string",
    "settings": "object",
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Delete Team
- **Method**: `DELETE`
- **Path**: `/teams/{id}`
- **Service**: Hierarchy API
- **Description**: Delete a team
- **Response**: `true` if successful

### 3. Agents

#### Get Agents
- **Method**: `GET`
- **Path**: `/agents`
- **Service**: Orchestrator API
- **Description**: Retrieve all agents, optionally filtered by team
- **Query Parameters**:
  - `team_id` (optional): Filter agents by team ID
- **Response**:
  ```json
  [
    {
      "id": "string",
      "team_id": "string",
      "name": "string",
      "role": "string",
      "type": "string",
      "template_id": "string (optional)",
      "status": "string (active|inactive|busy|error)",
      "config": {
        "goal": "string (optional)",
        "backstory": "string (optional)",
        "system_prompt": "string (optional)",
        "tools": "array of strings (optional)",
        "skills": "array of strings (optional)",
        "model": "string (optional)",
        "temperature": "number (optional)"
      },
      "created_at": "string (ISO 8601)",
      "updated_at": "string (ISO 8601)",
      "team_name": "string (optional)",
      "organization_id": "string (optional)",
      "organization_name": "string (optional)"
    }
  ]
  ```

#### Get Agent by ID
- **Method**: `GET`
- **Path**: `/agents/{id}`
- **Service**: Orchestrator API
- **Description**: Retrieve a specific agent
- **Response**:
  ```json
  {
    "id": "string",
    "team_id": "string",
    "name": "string",
    "role": "string",
    "type": "string",
    "template_id": "string (optional)",
    "status": "string",
    "config": {
      "goal": "string (optional)",
      "backstory": "string (optional)",
      "system_prompt": "string (optional)",
      "tools": "array of strings (optional)",
      "skills": "array of strings (optional)",
      "model": "string (optional)",
      "temperature": "number (optional)"
    },
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Create Agent
- **Method**: `POST`
- **Path**: `/agents`
- **Service**: Orchestrator API
- **Description**: Create a new agent
- **Request Body**:
  ```json
  {
    "team_id": "string",
    "name": "string",
    "role": "string",
    "type": "string",
    "config": {
      "goal": "string",
      "tools": "array of strings",
      "model": "string",
      "temperature": "number"
    }
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "team_id": "string",
    "name": "string",
    "role": "string",
    "type": "string",
    "status": "string",
    "config": {
      "goal": "string",
      "tools": "array of strings",
      "model": "string",
      "temperature": "number"
    },
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Create Agent from Template
- **Method**: `POST`
- **Path**: `/agents/from-template`
- **Service**: Orchestrator API
- **Description**: Create a new agent using a pre-built template
- **Request Body**:
  ```json
  {
    "template_id": "string",
    "overrides": {
      "team_id": "string",
      "name": "string (optional)",
      "goal": "string (optional)",
      "backstory": "string (optional)",
      "temperature": "number (optional)",
      "additional_properties": "any"
    }
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "team_id": "string",
    "name": "string",
    "role": "string",
    "type": "string",
    "status": "string",
    "config": {
      "goal": "string",
      "tools": "array of strings",
      "model": "string",
      "temperature": "number"
    },
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Update Agent
- **Method**: `PUT`
- **Path**: `/agents/{id}`
- **Service**: Orchestrator API
- **Description**: Update an existing agent
- **Request Body**:
  ```json
  {
    "name": "string (optional)",
    "role": "string (optional)",
    "type": "string (optional)",
    "status": "string (optional)",
    "config": {
      "goal": "string (optional)",
      "backstory": "string (optional)",
      "system_prompt": "string (optional)",
      "tools": "array of strings (optional)",
      "skills": "array of strings (optional)",
      "model": "string (optional)",
      "temperature": "number (optional)"
    }
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "team_id": "string",
    "name": "string",
    "role": "string",
    "type": "string",
    "status": "string",
    "config": {
      "goal": "string",
      "backstory": "string",
      "system_prompt": "string",
      "tools": "array of strings",
      "skills": "array of strings",
      "model": "string",
      "temperature": "number"
    },
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

#### Delete Agent
- **Method**: `DELETE`
- **Path**: `/agents/{id}`
- **Service**: Orchestrator API
- **Description**: Delete an agent
- **Response**: `true` if successful

### 4. Agent Templates

#### Get Agent Templates
- **Method**: `GET`
- **Path**: `/agent-templates`
- **Service**: Orchestrator API
- **Description**: Retrieve all agent templates
- **Response**:
  ```json
  {
    "templates": [
      {
        "template_id": "string",
        "name": "string",
        "category": "string",
        "description": "string",
        "system_prompt": "string",
        "default_goal": "string",
        "default_backstory": "string",
        "tools": "array of strings",
        "skills": "array of strings",
        "default_model": "string",
        "default_temperature": "number",
        "customizable_fields": "array of strings"
      }
    ]
  }
  ```

### 5. Tasks

#### Assign Task to Agent
- **Method**: `POST`
- **Path**: `/agents/{id}/tasks`
- **Service**: Orchestrator API
- **Description**: Assign a new task to an agent
- **Request Body**:
  ```json
  {
    "title": "string",
    "description": "string",
    "type": "string",
    "priority": "number (1-10)"
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "title": "string",
    "description": "string",
    "type": "string",
    "assigned_to": "string",
    "assigned_agent_name": "string",
    "status": "string (pending|in_progress|completed|failed)",
    "priority": "number",
    "created_at": "string (ISO 8601)",
    "completed_at": "string (ISO 8601) (optional)",
    "result": "string (optional)"
  }
  ```

### 6. Goals

#### Get Organization Goals
- **Method**: `GET`
- **Path**: `/organizations/{id}/goals`
- **Service**: Orchestrator API
- **Description**: Retrieve all goals for an organization
- **Response**:
  ```json
  [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "priority": "string (low|medium|high|critical)",
      "status": "string (planning|active|completed|on_hold)",
      "target_completion_date": "string (ISO 8601)",
      "progress_percentage": "number",
      "assigned_teams": "array of strings",
      "milestones": [
        {
          "id": "string",
          "title": "string",
          "status": "string",
          "due_date": "string (ISO 8601)"
        }
      ],
      "created_at": "string (ISO 8601)",
      "updated_at": "string (ISO 8601)"
    }
  ]
  ```

#### Create Goal
- **Method**: `POST`
- **Path**: `/organizations/{id}/goals`
- **Service**: Orchestrator API
- **Description**: Create a new goal for an organization
- **Request Body**:
  ```json
  {
    "title": "string",
    "description": "string",
    "priority": "string (low|medium|high|critical)",
    "target_completion_date": "string (ISO 8601)",
    "assigned_teams": "array of strings",
    "goal_type": "string",
    "target_value": "number",
    "target_unit": "string",
    "priority_level": "number"
  }
  ```
- **Response**:
  ```json
  {
    "id": "string",
    "title": "string",
    "description": "string",
    "priority": "string",
    "status": "string",
    "target_completion_date": "string (ISO 8601)",
    "progress_percentage": "number",
    "assigned_teams": "array of strings",
    "milestones": "array",
    "created_at": "string (ISO 8601)",
    "updated_at": "string (ISO 8601)"
  }
  ```

### 7. Knowledge Management

#### Get Knowledge Stats
- **Method**: `GET`
- **Path**: `/knowledge/stats`
- **Service**: Orchestrator API
- **Description**: Retrieve knowledge base statistics
- **Response**:
  ```json
  {
    "totalDocuments": "number",
    "recentDocuments": "array"
  }
  ```

#### Upload Document
- **Method**: `POST`
- **Path**: `/knowledge/documents`
- **Service**: Orchestrator API
- **Description**: Upload a new document to the knowledge base
- **Request Body**: Multipart form data with file content
- **Form Fields**:
  - `file`: The document file
  - `title`: The document title
- **Response**:
  ```json
  {
    "id": "string",
    "title": "string",
    "type": "string",
    "uploaded_at": "string (ISO 8601)"
  }
  ```

## Error Responses

All endpoints may return the following error responses:

- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

Error response format:
```json
{
  "error": "string",
  "message": "string"
}
```

## WebSocket Endpoints

For real-time updates, the UI connects to WebSocket endpoints:

- **Development**: `ws://localhost:8000`
- **Production**: `wss://your-domain.com/api`

## Rate Limiting

API endpoints may be rate-limited. Clients should handle 429 (Too Many Requests) responses appropriately.

## Versioning

The API version is included in the URL path. Currently, all endpoints are at version 1.

## Examples

### cURL Example - Create Agent
```bash
curl -X POST "http://localhost:8000/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "team_123",
    "name": "Frontend Developer",
    "role": "React Developer",
    "type": "developer",
    "config": {
      "goal": "Develop responsive web applications",
      "tools": ["code_generation", "code_review"],
      "model": "claude-sonnet-4-20250514",
      "temperature": 0.7
    }
  }'
```

### JavaScript Example - Get Agents
```javascript
const response = await fetch('http://localhost:8000/agents');
const agents = await response.json();
console.log(agents);
```