# Teams Components

This directory contains modular React components for managing teams in the FuzeAgent application. All components follow the established design patterns and provide comprehensive team management functionality.

## Components Overview

### Core Components

#### `TeamCard`
Displays a team's information in a card format with stats and actions.

**Props:**
- `team: Team` - Team data to display
- `onEdit?: (team: Team) => void` - Edit callback
- `onDelete?: (teamId: string) => void` - Delete callback
- `onViewDetails?: (team: Team) => void` - View details callback
- `showStats?: boolean` - Whether to show statistics (default: true)

**Features:**
- Team name, description, type, and status
- Member count, task count, completion rate, and efficiency
- Action buttons for edit, delete, and view details

#### `TeamList`
Displays a paginated list of teams with loading states and error handling.

**Props:**
- `teams: Team[]` - Array of teams to display
- `loading?: boolean` - Loading state
- `error?: string | null` - Error message
- `onEdit?: (team: Team) => void` - Edit callback
- `onDelete?: (teamId: string) => void` - Delete callback
- `onViewDetails?: (team: Team) => void` - View details callback
- `onRetry?: () => void` - Retry callback for errors
- `showStats?: boolean` - Whether to show statistics

**Features:**
- Responsive grid layout
- Loading skeleton states
- Error states with retry option
- Empty state when no teams exist

#### `TeamFormModal`
Modal dialog for creating and editing teams with validation.

**Props:**
- `isOpen: boolean` - Modal visibility
- `onClose: () => void` - Close callback
- `onSubmit: (data: TeamCreate | TeamUpdate) => Promise<void>` - Submit callback
- `initialData?: Team` - Initial data for edit mode
- `mode: 'create' | 'edit'` - Modal mode
- `loading?: boolean` - Loading state
- `error?: string | null` - Error message

**Features:**
- Form validation with real-time feedback
- Team type and color selection
- Status management (edit mode only)
- Loading states and error handling

### Badge Components

#### `TeamStatusBadge`
Displays a colored badge for team status.

**Props:**
- `status: Team['status']` - Status to display
- `size?: 'sm' | 'md' | 'lg'` - Badge size

#### `TeamTypeBadge`
Displays a colored badge for team type.

**Props:**
- `teamType: Team['team_type']` - Team type to display
- `size?: 'sm' | 'md' | 'lg'` - Badge size

## Usage Examples

### Basic Team List
```tsx
import { TeamList } from '../components/teams'
import { useTeams } from '../hooks/useTeams'

const TeamsPage = () => {
  const { teams, loading, error, refetch } = useTeams()

  return (
    <TeamList
      teams={teams}
      loading={loading}
      error={error}
      onRetry={refetch}
      onEdit={(team) => console.log('Edit team:', team)}
      onDelete={(teamId) => console.log('Delete team:', teamId)}
    />
  )
}
```

### Team Creation Modal
```tsx
import { TeamFormModal } from '../components/teams'
import { useCreateTeam } from '../hooks/useTeams'

const CreateTeamButton = () => {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const { mutate: createTeam, isLoading, error } = useCreateTeam()

  const handleSubmit = async (data: TeamCreate) => {
    await createTeam(data)
    setIsModalOpen(false)
  }

  return (
    <>
      <button onClick={() => setIsModalOpen(true)}>
        Create Team
      </button>
      <TeamFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleSubmit}
        mode="create"
        loading={isLoading}
        error={error?.message}
      />
    </>
  )
}
```

### Team Card with Custom Actions
```tsx
import { TeamCard } from '../components/teams'

const CustomTeamCard = ({ team }) => {
  const handleViewDetails = (team) => {
    // Navigate to team details page
    navigate(`/teams/${team.id}`)
  }

  const handleEdit = (team) => {
    // Open edit modal
    setEditingTeam(team)
  }

  const handleDelete = (teamId) => {
    if (confirm('Are you sure you want to delete this team?')) {
      deleteTeam(teamId)
    }
  }

  return (
    <TeamCard
      team={team}
      onViewDetails={handleViewDetails}
      onEdit={handleEdit}
      onDelete={handleDelete}
      showStats={true}
    />
  )
}
```

## Styling and Theming

All components use Tailwind CSS classes and follow the established design system:

- **Colors**: Blue (#2563eb) for primary actions, gray for secondary
- **Spacing**: Consistent padding and margins using Tailwind spacing scale
- **Typography**: Standard text sizes and weights
- **States**: Hover, focus, loading, and error states are properly styled
- **Responsive**: Components work well on mobile, tablet, and desktop

## Accessibility

Components include proper accessibility features:

- Semantic HTML elements
- ARIA labels where needed
- Keyboard navigation support
- Screen reader friendly
- Focus management in modals

## Error Handling

Components handle various error states:

- Network errors with retry options
- Validation errors with helpful messages
- Loading states with skeleton UI
- Empty states with helpful messaging

## Performance

Components are optimized for performance:

- Efficient re-rendering with proper key props
- Lazy loading where applicable
- Minimal bundle size
- Tree-shakeable exports

## Dependencies

Components depend on:

- React 18+
- Tailwind CSS
- TypeScript types from main types file
- Utility functions from utils file

## Contributing

When adding new components or modifying existing ones:

1. Follow the established naming conventions
2. Include proper TypeScript types
3. Add comprehensive documentation
4. Include usage examples
5. Test accessibility and responsive design
6. Update this README with new components

## Future Enhancements

Planned improvements:

- Team member management components
- Team statistics dashboard
- Advanced filtering and search
- Bulk operations
- Team templates
- Performance analytics charts
