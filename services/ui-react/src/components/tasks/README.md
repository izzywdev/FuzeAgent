# Tasks System Components

A comprehensive set of React components for managing tasks with advanced filtering, search, and pagination capabilities.

## Components Overview

### Core Components

#### `TaskCard`
Displays individual task information in a card format with status, priority, assignments, and actions.

**Features:**
- Task title and description
- Status and priority badges
- Team/agent/milestone assignments
- Creation and completion dates
- Duration calculation for completed tasks
- Result display for completed tasks
- Edit, execute, and delete actions
- Hover effects and responsive design

#### `TaskList`
Displays a collection of tasks with summary statistics and grid layout.

**Features:**
- Grid layout with responsive design
- Task count and status summary
- Loading and error states
- Empty state with helpful messaging
- Integration with TaskCard components

#### `TaskFormModal`
Modal form for creating and editing tasks with comprehensive validation.

**Features:**
- Title and description fields
- Priority and status selection
- Team, agent, and milestone assignment
- Form validation with error display
- Real-time preview of task appearance
- Loading states and error handling
- Create/edit mode support

### Utility Components

#### `TaskStatusBadge`
Displays task status with appropriate colors and icons.

#### `TaskPriorityBadge`
Displays task priority with appropriate colors and indicators.

## Utility Functions

### Status and Priority Management
- `getTaskStatusConfig()` - Get configuration for task status
- `getTaskPriorityConfig()` - Get configuration for task priority
- `TASK_STATUS_CONFIGS` - Status configuration constants
- `TASK_PRIORITY_CONFIGS` - Priority configuration constants

### Date and Time Formatting
- `formatTaskDate()` - Format date for display
- `formatTaskDateTime()` - Format date and time for display
- `getTaskDuration()` - Calculate and format task duration

### Task Analysis
- `calculateTaskProgress()` - Calculate completion percentage
- `getTasksByStatus()` - Group tasks by status
- `getTasksByPriority()` - Group tasks by priority
- `getTaskStats()` - Get comprehensive task statistics

### Data Manipulation
- `sortTasks()` - Sort tasks by various criteria
- `filterTasks()` - Filter tasks based on criteria
- `convertToTaskDisplay()` - Convert Task to TaskDisplay
- `convertTasksToDisplay()` - Convert array of tasks to display format

## Usage Examples

### Basic Task List
```tsx
import { TaskList, convertTasksToDisplay } from '../components/tasks';

function TaskPage() {
  const [tasks, setTasks] = useState([]);
  const taskDisplays = convertTasksToDisplay(tasks);

  return (
    <TaskList
      tasks={taskDisplays}
      onTaskClick={(task) => console.log('Task clicked:', task)}
      onTaskDelete={(taskId) => handleDelete(taskId)}
    />
  );
}
```

### Task Form Modal
```tsx
import { TaskFormModal } from '../components/tasks';

function CreateTaskButton() {
  const [showForm, setShowForm] = useState(false);

  return (
    <>
      <button onClick={() => setShowForm(true)}>Create Task</button>
      <TaskFormModal
        isOpen={showForm}
        onClose={() => setShowForm(false)}
        onSubmit={handleCreateTask}
        teams={teams}
        agents={agents}
        milestones={milestones}
      />
    </>
  );
}
```

### Task Status Badge
```tsx
import { TaskStatusBadge } from '../components/tasks';

function TaskItem({ task }) {
  return (
    <div>
      <h3>{task.title}</h3>
      <TaskStatusBadge status={task.status} />
    </div>
  );
}
```

## API Integration

The components are designed to work seamlessly with the tasks API service methods:

- `getTasks()` - Fetch paginated tasks with filters
- `createTask()` - Create new tasks
- `updateTask()` - Update existing tasks
- `deleteTask()` - Delete tasks
- `executeTask()` - Execute pending tasks
- `getTeamTasks()` - Get tasks for specific team
- `getAgentTasks()` - Get tasks for specific agent
- `getMilestoneTasks()` - Get tasks for specific milestone

## Styling

All components use Tailwind CSS classes and follow a consistent design system:

- Gray color palette for neutral elements
- Blue for primary actions and focus states
- Green for success/completion states
- Red for errors and destructive actions
- Responsive design with mobile-first approach
- Consistent spacing and typography

## Accessibility

Components include proper ARIA labels, keyboard navigation, and screen reader support:

- Semantic HTML structure
- Proper form labels and descriptions
- Keyboard event handling
- Focus management in modals
- Color contrast compliance
- Screen reader announcements for dynamic content

## Error Handling

Components provide comprehensive error handling:

- Network error display
- Form validation errors
- Loading state management
- User-friendly error messages
- Graceful degradation for missing data

## Future Enhancements

Planned improvements for the tasks system:

- Bulk operations (select multiple tasks)
- Advanced filtering UI components
- Task templates and quick creation
- Task dependencies and relationships
- Time tracking and effort estimation
- Task comments and collaboration features
- Export and import capabilities
- Task history and audit trail
