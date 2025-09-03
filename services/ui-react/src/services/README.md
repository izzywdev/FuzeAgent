# API Service

This directory contains the centralized API service for the FuzeAgent frontend application.

## Files

### `apiService.ts`
The main API service class that provides a clean interface for all backend API operations. This service:

- **Centralizes all API calls** - No more scattered fetch calls throughout components
- **Handles organization context automatically** - Sets organization ID for all requests
- **Provides consistent error handling** - Standardized response format
- **Supports both hierarchy and orchestrator APIs** - Unified interface for different backend services
- **Includes specialized methods** for knowledge management, container operations, conversations, and more

### Key Features

#### Organization Context
The service automatically includes the current organization ID in all requests through the `setOrganizationId()` method.

#### Response Format
All methods return a consistent `ApiResponse<T>` format:
```typescript
interface ApiResponse<T> {
  data: T
  status: number
  ok: boolean
}
```

#### Main API Categories

1. **Organizations** - CRUD operations for organizations
2. **Teams** - Team management and member operations
3. **Agents** - Agent lifecycle and configuration
4. **Tasks** - Task creation, assignment, and management
5. **Knowledge Management** - Document uploads, URL ingestion, content retrieval
6. **Container Management** - Docker container operations for agents
7. **Conversations & Messages** - Chat and conversation management
8. **Tools** - Tool configuration for teams and agents
9. **Goals** - Goal tracking and management

## Usage

### In React Components

```typescript
import { useApiService } from '../../hooks/useApiService'

function MyComponent() {
  const apiService = useApiService()
  const { currentOrganization } = useOrganization()

  const loadData = async () => {
    if (!currentOrganization) return

    const response = await apiService.getAgents()
    if (response.ok) {
      setAgents(response.data?.results || [])
    } else {
      console.error('Failed to load agents:', response.status)
    }
  }
}
```

### Direct Usage

```typescript
import { apiService } from '../services/apiService'

// Set organization context
apiService.setOrganizationId('org-123')

// Make API calls
const response = await apiService.getTeams()
```

## Migration Notes

This refactoring removed direct `fetch()` calls from:

- ✅ `FixedDashboard.tsx`
- ✅ `FixedTeamsPage.tsx` 
- ✅ `FixedAgentsPage.tsx`
- ✅ `CreateAgentPage.tsx`
- ✅ `TeamDetailsPage.tsx`
- ✅ `GoalsPage.tsx`
- ✅ `OrganizationProfilePage.tsx`
- ✅ `FixedOrgChartPage.tsx`
- ✅ `TeamToolsSection.tsx`
- ✅ `AgentToolsSection.tsx`
- ✅ `OrganizationToolsSection.tsx`

### Remaining Work

Some complex fetch calls in `AgentDetailsPage.tsx` for conversations, container management, and real-time features may need additional refinement. These can be refactored incrementally as needed.

## Benefits

1. **Maintainability** - All API logic is centralized and easier to modify
2. **Consistency** - Standardized error handling and response format
3. **Type Safety** - Full TypeScript support with proper interfaces
4. **Testability** - Easier to mock and test API interactions
5. **Organization Context** - Automatic handling of multi-tenant organization scoping
6. **Error Handling** - Consistent error handling across all API calls
