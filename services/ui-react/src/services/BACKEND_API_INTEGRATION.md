# Backend API Integration

## Overview

The UI has been updated to support the new unified backend API that provides complete CRUD operations for all database tables.

## New Backend API

The new backend API is running on port 8000 and provides:

- Complete REST API for all tables with standardized endpoints
- Pagination, search, and filtering on all list endpoints
- Full CRUD operations (Create, Read, Update, Delete)
- Automatic API documentation at `/docs`

## API Endpoints

All tables follow the same pattern:

```
GET    /api/{resource}              - List with pagination and search
GET    /api/{resource}/{id}         - Get single item
POST   /api/{resource}              - Create new item
PUT    /api/{resource}/{id}         - Update item
DELETE /api/{resource}/{id}         - Delete item
```

## Available Resources

- `organizations` - Organizations
- `teams` - Teams
- `agents` - Agents
- `agent-templates` - Agent templates
- `agent-env-vars` - Agent environment variables
- `agent-template-env-vars` - Agent template environment variables
- `containers` - Containers
- `org-tools` - Organization tools
- `org-tool-params` - Organization tool parameters
- `team-tool-settings` - Team tool settings
- `agent-tool-settings` - Agent tool settings
- `goals` - Goals
- `goal-assigned-teams` - Goal assignments
- `milestones` - Milestones
- `tasks` - Tasks
- `task-assignments` - Task assignments
- `conversations` - Conversations
- `conversation-messages` - Conversation messages
- `knowledge` - Knowledge items
- `entities` - Entity registry
- `team-lead-history` - Team lead history

## Configuration

The backend API URL is configured in `src/config/api.ts` and can be overridden with the environment variable:

```bash
VITE_BACKEND_API_URL=http://localhost:8000
```

## Integration Points

1. **Direct API Calls**: You can make direct fetch calls using the backend API endpoints
2. **Update Existing Services**: The existing `apiService.ts` can be updated to use the new endpoints
3. **Create New Services**: Create specialized services for specific resources

## Example Usage

```typescript
// Fetch organizations
const response = await fetch('http://localhost:8000/api/organizations?page=1&page_size=10')
const data = await response.json()

// Create a new organization
const newOrg = await fetch('http://localhost:8000/api/organizations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'My Organization',
    description: 'A great organization'
  })
})

// Update an organization
const updated = await fetch('http://localhost:8000/api/organizations/{id}', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'Updated Name' })
})
```

## Response Format

All list endpoints return paginated results:

```typescript
{
  items: [...],      // Array of items
  total: 100,        // Total count
  page: 1,           // Current page
  page_size: 20,     // Items per page
  total_pages: 5     // Total number of pages
}
```

## Migration Path

To migrate existing code to use the new backend API:

1. Update API calls to use the new endpoint format (`/api/{resource}`)
2. Update response handling to expect the new paginated format
3. Remove organization-scoped logic (the backend handles this)
4. Test all CRUD operations

## Testing

You can test the API using:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Direct HTTP requests (curl, Postman, etc.)
