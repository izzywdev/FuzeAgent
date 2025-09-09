# FuzeAgent Mock-Server Database Schema

## Overview

The FuzeAgent Mock-Server uses SQLite with SQLAlchemy ORM for data persistence. The database schema implements a hierarchical organizational structure with support for teams, agents, tools, goals, milestones, and tasks.

## Database Configuration

- **Database Type**: SQLite
- **Database File**: `./data/mock_data_v2.db`
- **ORM**: SQLAlchemy with declarative base
- **Connection**: `sqlite:///./data/mock_data_v2.db`

## Entity Relationship Diagram

```
Organization (1) ──→ (N) Team (1) ──→ (N) Agent
     │                    │
     │                    │
     └──→ (N) OrgTool ──→ (N) TeamToolSetting
     │                    │
     │                    └──→ (N) AgentToolSetting
     │
     └──→ (N) Goal (1) ──→ (N) Milestone (1) ──→ (N) Task
```

## Tables and Relationships

### 1. Organizations Table (`organizations`)

**Primary Entity** - Root of the hierarchy

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PRIMARY KEY | Unique organization identifier |
| `name` | String | NOT NULL | Organization name |
| `description` | Text | NULLABLE | Organization description |
| `industry` | String | NULLABLE | Industry classification |
| `size` | String | NULLABLE | Organization size |
| `founded` | String | NULLABLE | Founded year |
| `website` | String | NULLABLE | Organization website |
| `settings` | Text | NULLABLE | JSON configuration string |
| `created_at` | DateTime | DEFAULT: utcnow() | Creation timestamp |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |
| `team_count` | Integer | DEFAULT: 0 | Cached team count |
| `agent_count` | Integer | DEFAULT: 0 | Cached agent count |

**Relationships:**
- One-to-Many: `teams` (Organization → Team)
- One-to-Many: `tools` (Organization → OrgTool)
- One-to-Many: `goals` (Organization → Goal)

### 2. Teams Table (`teams`)

**Hierarchical Entity** - Belongs to Organization

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PRIMARY KEY | Unique team identifier |
| `organization_id` | String | FOREIGN KEY → organizations.id, NOT NULL | Parent organization |
| `name` | String | NOT NULL | Team name |
| `description` | Text | NULLABLE | Team description |
| `team_type` | String | NULLABLE | Type: development, operations, management, research |
| `color` | String | DEFAULT: "#2563eb" | UI color representation |
| `status` | String | DEFAULT: "active" | Team status |
| `settings` | Text | NULLABLE | JSON configuration string |
| `created_at` | DateTime | DEFAULT: utcnow() | Creation timestamp |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |

**Relationships:**
- Many-to-One: `organization` (Team → Organization)
- One-to-Many: `agents` (Team → Agent)
- One-to-Many: `tool_settings` (Team → TeamToolSetting)

### 3. Agents Table (`agents`)

**Hierarchical Entity** - Belongs to Team

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PRIMARY KEY | Unique agent identifier |
| `team_id` | String | FOREIGN KEY → teams.id, NOT NULL | Parent team |
| `name` | String | NOT NULL | Agent name |
| `role` | String | NULLABLE | Agent role/position |
| `type` | String | DEFAULT: "developer" | Agent type |
| `status` | String | DEFAULT: "active" | Agent status |
| `config` | Text | NULLABLE | JSON configuration string |
| `template_id` | String | NULLABLE | Agent template reference |
| `created_at` | DateTime | DEFAULT: utcnow() | Creation timestamp |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |

**Relationships:**
- Many-to-One: `team` (Agent → Team)
- One-to-Many: `tool_settings` (Agent → AgentToolSetting)

### 4. Organization Tools Table (`org_tools`)

**Configuration Entity** - Organization-level tool definitions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PRIMARY KEY | Unique tool identifier |
| `org_id` | String | FOREIGN KEY → organizations.id, NOT NULL | Parent organization |
| `key` | String | NOT NULL | Tool key/identifier |
| `name` | String | NOT NULL | Tool display name |
| `description` | Text | NULLABLE | Tool description |
| `default_config` | Text | NULLABLE | JSON default configuration |
| `is_active` | Boolean | DEFAULT: true | Tool active status |
| `created_at` | DateTime | DEFAULT: utcnow() | Creation timestamp |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |

**Relationships:**
- Many-to-One: `organization` (OrgTool → Organization)
- One-to-Many: `team_settings` (OrgTool → TeamToolSetting)
- One-to-Many: `agent_settings` (OrgTool → AgentToolSetting)

### 5. Team Tool Settings Table (`team_tool_settings`)

**Junction Table** - Many-to-Many relationship between Teams and Tools

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `team_id` | String | FOREIGN KEY → teams.id, PRIMARY KEY | Team identifier |
| `tool_id` | String | FOREIGN KEY → org_tools.id, PRIMARY KEY | Tool identifier |
| `enabled` | Boolean | DEFAULT: false | Tool enabled status for team |
| `config_override` | Text | NULLABLE | JSON configuration override |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |

**Relationships:**
- Many-to-One: `team` (TeamToolSetting → Team)
- Many-to-One: `tool` (TeamToolSetting → OrgTool)

### 6. Agent Tool Settings Table (`agent_tool_settings`)

**Junction Table** - Many-to-Many relationship between Agents and Tools

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `agent_id` | String | FOREIGN KEY → agents.id, PRIMARY KEY | Agent identifier |
| `tool_id` | String | FOREIGN KEY → org_tools.id, PRIMARY KEY | Tool identifier |
| `enabled` | Boolean | DEFAULT: false | Tool enabled status for agent |
| `config_override` | Text | NULLABLE | JSON configuration override |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |

**Relationships:**
- Many-to-One: `agent` (AgentToolSetting → Agent)
- Many-to-One: `tool` (AgentToolSetting → OrgTool)

### 7. Goals Table (`goals`)

**Hierarchical Entity** - Belongs to Organization

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PRIMARY KEY | Unique goal identifier |
| `organization_id` | String | FOREIGN KEY → organizations.id, NOT NULL | Parent organization |
| `title` | String | NOT NULL | Goal title |
| `description` | Text | NULLABLE | Goal description |
| `status` | String | DEFAULT: "active" | Goal status: planning, active, completed, on_hold |
| `priority` | String | DEFAULT: "medium" | Priority: low, medium, high, critical |
| `target_date` | DateTime | NULLABLE | Target completion date |
| `created_at` | DateTime | DEFAULT: utcnow() | Creation timestamp |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |

**Relationships:**
- Many-to-One: `organization` (Goal → Organization)
- One-to-Many: `milestones` (Goal → Milestone) with CASCADE DELETE

### 8. Milestones Table (`milestones`)

**Hierarchical Entity** - Belongs to Goal

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PRIMARY KEY | Unique milestone identifier |
| `goal_id` | String | FOREIGN KEY → goals.id, NOT NULL | Parent goal |
| `title` | String | NOT NULL | Milestone title |
| `description` | Text | NULLABLE | Milestone description |
| `status` | String | DEFAULT: "not_started" | Status: not_started, in_progress, completed, blocked, cancelled |
| `priority` | String | DEFAULT: "medium" | Priority: low, medium, high, critical |
| `progress_percentage` | Integer | DEFAULT: 0 | Progress percentage (0-100) |
| `target_date` | DateTime | NOT NULL | Target completion date |
| `completed_at` | DateTime | NULLABLE | Completion timestamp |
| `created_at` | DateTime | DEFAULT: utcnow() | Creation timestamp |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |

**Relationships:**
- Many-to-One: `goal` (Milestone → Goal)
- One-to-Many: `tasks` (Milestone → Task) with CASCADE DELETE

### 9. Tasks Table (`tasks`)

**Hierarchical Entity** - Can belong to Team, Agent, and Milestone

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PRIMARY KEY | Unique task identifier |
| `title` | String | NOT NULL | Task title |
| `description` | Text | NULLABLE | Task description |
| `status` | String | DEFAULT: "pending" | Status: pending, in_progress, completed, failed |
| `priority` | String | DEFAULT: "medium" | Priority: low, medium, high, critical |
| `team_id` | String | FOREIGN KEY → teams.id, NULLABLE | Assigned team |
| `agent_id` | String | FOREIGN KEY → agents.id, NULLABLE | Assigned agent |
| `milestone_id` | String | FOREIGN KEY → milestones.id, NULLABLE | Related milestone |
| `result` | Text | NULLABLE | Task execution result |
| `created_at` | DateTime | DEFAULT: utcnow() | Creation timestamp |
| `updated_at` | DateTime | DEFAULT: utcnow(), ON UPDATE: utcnow() | Last update timestamp |
| `completed_at` | DateTime | NULLABLE | Completion timestamp |

**Relationships:**
- Many-to-One: `milestone` (Task → Milestone)

## Data Flow and Business Logic

### Hierarchical Structure
1. **Organization** → **Teams** → **Agents**
2. **Organization** → **Goals** → **Milestones** → **Tasks**
3. **Organization** → **Tools** → **Team/Agent Settings**

### Tool Configuration Inheritance
- Tools are defined at the organization level (`org_tools`)
- Teams can override tool settings (`team_tool_settings`)
- Agents can override team settings (`agent_tool_settings`)
- Configuration inheritance: Agent > Team > Organization Default

### Task Assignment Hierarchy
- Tasks can be assigned to teams, agents, and milestones
- Tasks must have a team assignment for organization scoping
- Tasks can optionally be assigned to agents and milestones

### Status Management
- **Goals**: planning, active, completed, on_hold
- **Milestones**: not_started, in_progress, completed, blocked, cancelled
- **Tasks**: pending, in_progress, completed, failed
- **Agents**: active, inactive, suspended
- **Teams**: active, inactive

### Progress Tracking
- Goals track progress via milestone completion
- Milestones track progress via task completion
- Automatic progress calculation based on child entity completion

## Database Initialization

The database automatically initializes with sample data if empty:

1. **Sample Organization**: "Demo Organization"
2. **Sample Team**: "Development Team"
3. **Sample Agent**: "Sample Agent"

## API Endpoints Structure

### Organization Scoping
All API endpoints are scoped to organizations using:
- `X-Organization-Token` header for authentication
- Organization validation in all operations
- Automatic filtering by organization membership

### CRUD Operations
Each entity supports full CRUD operations:
- **Create**: POST endpoints with validation
- **Read**: GET endpoints with pagination, filtering, and search
- **Update**: PUT endpoints with partial updates
- **Delete**: DELETE endpoints with cascade handling

### Pagination and Filtering
- Consistent pagination across all list endpoints
- Advanced filtering by status, priority, dates
- Text search capabilities
- Sorting by multiple fields

## Security Considerations

### Authentication
- Bearer token authentication for organization access
- Organization-scoped data access
- Token validation against database

### Data Isolation
- All operations scoped to organization
- Cross-organization data access prevented
- Team and agent access validated through organization membership

## Performance Considerations

### Caching
- Organization-level counters (`team_count`, `agent_count`)
- Calculated progress percentages cached
- Relationship data loaded efficiently

### Indexing
- Primary keys automatically indexed
- Foreign key relationships indexed
- Search fields optimized for text queries

## Migration and Schema Evolution

The current schema uses SQLAlchemy's declarative base for automatic table creation. Future schema changes should be handled through:

1. Database migration scripts
2. Version-controlled schema updates
3. Backward compatibility considerations
4. Data migration procedures

## Sample Data Structure

```json
{
  "organization": {
    "id": "a50af4d0-27f1-40ae-aea0-e847dc5c4ba9",
    "name": "Demo Organization",
    "teams": [
      {
        "id": "team-1",
        "name": "Development Team",
        "agents": [
          {
            "id": "agent-1",
            "name": "Sample Agent",
            "type": "developer"
          }
        ]
      }
    ],
    "goals": [
      {
        "id": "goal-1",
        "title": "Q1 Objectives",
        "milestones": [
          {
            "id": "milestone-1",
            "title": "Phase 1 Complete",
            "tasks": [
              {
                "id": "task-1",
                "title": "Implement Feature X",
                "status": "pending"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

This schema provides a comprehensive foundation for managing organizational hierarchies, agent workflows, and project management within the FuzeAgent system.
