/**
 * Milestones Component Types
 *
 * This file contains TypeScript interfaces and types specific to the milestones UI components.
 * These are component-specific types that may include additional UI state and behavior properties.
 */

import type { Milestone, MilestoneCreate, MilestoneUpdate, MilestoneFilters, Task } from '../../types'

// ============================================================================
// COMPONENT-SPECIFIC TYPES
// ============================================================================

/**
 * Extended milestone type for UI components with additional display properties
 */
export interface MilestoneDisplay extends Milestone {
  /** Formatted target date for display */
  targetDateFormatted: string
  /** Formatted completed date for display */
  completedAtFormatted?: string
  /** Progress percentage as display string */
  progressDisplay: string
  /** Status display label */
  statusLabel: string
  /** Priority display label */
  priorityLabel: string
  /** CSS class for status styling */
  statusClass: string
  /** CSS class for priority styling */
  priorityClass: string
  /** Whether the milestone is overdue */
  isOverdue: boolean
  /** Days until target date (negative if overdue) */
  daysUntilTarget: number
}

/**
 * Milestone form data for create/edit forms
 */
export interface MilestoneFormData {
  title: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  target_date: string
  goal_id?: string
}

/**
 * Milestone list component props
 */
export interface MilestoneListProps {
  milestones: MilestoneDisplay[]
  loading: boolean
  error?: string
  onEdit: (milestone: Milestone) => void
  onDelete: (milestone: Milestone) => void
  onViewTasks: (milestone: Milestone) => void
  onCreateTask: (milestone: Milestone) => void
  selectedMilestoneId?: string
  onSelectMilestone?: (milestoneId: string | undefined) => void
}

/**
 * Milestone card component props
 */
export interface MilestoneCardProps {
  milestone: MilestoneDisplay
  onEdit: (milestone: Milestone) => void
  onDelete: (milestone: Milestone) => void
  onViewTasks: (milestone: Milestone) => void
  onCreateTask: (milestone: Milestone) => void
  isSelected?: boolean
  onSelect?: (milestoneId: string) => void
}

/**
 * Milestone form modal props
 */
export interface MilestoneFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: MilestoneFormData) => Promise<void>
  initialData?: Partial<MilestoneFormData>
  title: string
  submitButtonText: string
  loading: boolean
  goals: Array<{ id: string; title: string }>
  mode: 'create' | 'edit'
}

/**
 * Milestone filter controls props
 */
export interface MilestoneFiltersProps {
  filters: MilestoneFilters
  onFiltersChange: (filters: MilestoneFilters) => void
  availableGoals: Array<{ id: string; title: string }>
}

/**
 * Milestone search and pagination props
 */
export interface MilestonePaginationProps {
  currentPage: number
  totalPages: number
  pageSize: number
  totalItems: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
}

/**
 * Milestone task assignment modal props
 */
export interface MilestoneTaskAssignmentProps {
  isOpen: boolean
  onClose: () => void
  milestone: Milestone
  availableTasks: Task[]
  assignedTaskIds: string[]
  onAssignTask: (taskId: string) => Promise<void>
  onRemoveTask: (taskId: string) => Promise<void>
  loading: boolean
}

/**
 * Milestone progress indicator props
 */
export interface MilestoneProgressProps {
  progress: number
  status: Milestone['status']
  size?: 'small' | 'medium' | 'large'
  showLabel?: boolean
  animated?: boolean
}

/**
 * Milestone status badge props
 */
export interface MilestoneStatusBadgeProps {
  status: Milestone['status']
  size?: 'small' | 'medium' | 'large'
  variant?: 'filled' | 'outlined'
}

/**
 * Milestone priority badge props
 */
export interface MilestonePriorityBadgeProps {
  priority: Milestone['priority']
  size?: 'small' | 'medium' | 'large'
  variant?: 'filled' | 'outlined'
}

// ============================================================================
// UTILITY TYPES
// ============================================================================

/**
 * Sort options for milestone lists
 */
export interface MilestoneSortOption {
  value: 'created_at' | 'target_date' | 'priority' | 'progress_percentage' | 'title'
  label: string
  direction: 'asc' | 'desc'
}

/**
 * Milestone statistics for dashboard/overview
 */
export interface MilestoneStats {
  total: number
  completed: number
  inProgress: number
  notStarted: number
  blocked: number
  overdue: number
  completionRate: number
}

/**
 * Milestone timeline event
 */
export interface MilestoneTimelineEvent {
  id: string
  type: 'created' | 'updated' | 'completed' | 'task_assigned' | 'task_completed'
  milestoneId: string
  milestoneTitle: string
  timestamp: string
  description: string
  user?: string
}

// ============================================================================
// HOOK TYPES
// ============================================================================

/**
 * Return type for useMilestones hook
 */
export interface UseMilestonesReturn {
  milestones: MilestoneDisplay[]
  loading: boolean
  error: string | null
  totalItems: number
  currentPage: number
  totalPages: number
  filters: MilestoneFilters
  createMilestone: (data: MilestoneCreate) => Promise<void>
  updateMilestone: (id: string, data: MilestoneUpdate) => Promise<void>
  deleteMilestone: (id: string) => Promise<void>
  refetch: () => Promise<void>
  setPage: (page: number) => void
  setFilters: (filters: MilestoneFilters) => void
  clearFilters: () => void
}

/**
 * Return type for useMilestoneTasks hook
 */
export interface UseMilestoneTasksReturn {
  tasks: Task[]
  loading: boolean
  error: string | null
  totalItems: number
  assignTask: (taskId: string) => Promise<void>
  removeTask: (taskId: string) => Promise<void>
  refetch: () => Promise<void>
}

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * Milestone status configurations
 */
export const MILESTONE_STATUS_CONFIG = {
  not_started: {
    label: 'Not Started',
    color: '#6b7280',
    bgColor: '#f3f4f6',
    borderColor: '#d1d5db'
  },
  in_progress: {
    label: 'In Progress',
    color: '#2563eb',
    bgColor: '#eff6ff',
    borderColor: '#bfdbfe'
  },
  completed: {
    label: 'Completed',
    color: '#16a34a',
    bgColor: '#f0fdf4',
    borderColor: '#bbf7d0'
  },
  blocked: {
    label: 'Blocked',
    color: '#dc2626',
    bgColor: '#fef2f2',
    borderColor: '#fecaca'
  },
  cancelled: {
    label: 'Cancelled',
    color: '#7c2d12',
    bgColor: '#fef3c7',
    borderColor: '#fde68a'
  }
} as const

/**
 * Milestone priority configurations
 */
export const MILESTONE_PRIORITY_CONFIG = {
  low: {
    label: 'Low',
    color: '#6b7280',
    bgColor: '#f9fafb',
    borderColor: '#e5e7eb'
  },
  medium: {
    label: 'Medium',
    color: '#f59e0b',
    bgColor: '#fffbeb',
    borderColor: '#fde68a'
  },
  high: {
    label: 'High',
    color: '#ea580c',
    bgColor: '#fff7ed',
    borderColor: '#fed7aa'
  },
  critical: {
    label: 'Critical',
    color: '#dc2626',
    bgColor: '#fef2f2',
    borderColor: '#fecaca'
  }
} as const

/**
 * Default milestone filters
 */
export const DEFAULT_MILESTONE_FILTERS: MilestoneFilters = {
  sort_by: 'created_at',
  sort_order: 'desc'
}

/**
 * Milestone progress thresholds for visual indicators
 */
export const PROGRESS_THRESHOLDS = {
  excellent: 90,
  good: 75,
  fair: 50,
  poor: 25,
  critical: 0
} as const
