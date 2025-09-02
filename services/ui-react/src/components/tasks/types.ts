import type { Task, TaskCreate, TaskUpdate, TaskFilters, PaginatedTasksResponse } from '../../types';

// Extended types for UI components
export interface TaskDisplay extends Task {
  // Additional display properties
  isExpanded?: boolean;
  isSelected?: boolean;
  canEdit?: boolean;
  canDelete?: boolean;
  canExecute?: boolean;
}

export interface TaskCardProps {
  task: TaskDisplay;
  onEdit?: (task: Task) => void;
  onDelete?: (taskId: string) => void;
  onExecute?: (taskId: string) => void;
  onClick?: (task: Task) => void;
  className?: string;
}

export interface TaskListProps {
  tasks: TaskDisplay[];
  loading?: boolean;
  error?: string | null;
  onTaskUpdate?: (taskId: string, updates: TaskUpdate) => void;
  onTaskDelete?: (taskId: string) => void;
  onTaskExecute?: (taskId: string) => void;
  onTaskClick?: (task: Task) => void;
  showFilters?: boolean;
  showPagination?: boolean;
  className?: string;
}

export interface TaskFormProps {
  task?: Task;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: TaskCreate | TaskUpdate) => Promise<void>;
  loading?: boolean;
  error?: string | null;
  teams?: Array<{ id: string; name: string }>;
  agents?: Array<{ id: string; name: string }>;
  milestones?: Array<{ id: string; title: string }>;
}

export interface TaskFiltersProps {
  filters: TaskFilters;
  onFiltersChange: (filters: TaskFilters) => void;
  teams?: Array<{ id: string; name: string }>;
  agents?: Array<{ id: string; name: string }>;
  milestones?: Array<{ id: string; title: string }>;
  className?: string;
}

export interface TaskPaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  className?: string;
}

export interface TaskStatsProps {
  tasks: Task[];
  className?: string;
}

export interface TaskSearchProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

// Utility types
export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

export interface TaskStatusConfig {
  label: string;
  color: string;
  bgColor: string;
  icon: string;
}

export interface TaskPriorityConfig {
  label: string;
  color: string;
  bgColor: string;
  weight: number;
}

// Component state types
export interface TasksState {
  tasks: TaskDisplay[];
  loading: boolean;
  error: string | null;
  filters: TaskFilters;
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
  selectedTaskIds: string[];
  showCreateForm: boolean;
  showEditForm: boolean;
  editingTask: Task | null;
}
