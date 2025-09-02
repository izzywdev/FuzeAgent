import type { Task, TaskStatus, TaskPriority, TaskStatusConfig, TaskPriorityConfig, TaskDisplay } from './types';

// Status configurations
export const TASK_STATUS_CONFIGS: Record<TaskStatus, TaskStatusConfig> = {
  pending: {
    label: 'Pending',
    color: '#6b7280',
    bgColor: '#f3f4f6',
    icon: '⏳'
  },
  in_progress: {
    label: 'In Progress',
    color: '#2563eb',
    bgColor: '#dbeafe',
    icon: '🔄'
  },
  completed: {
    label: 'Completed',
    color: '#16a34a',
    bgColor: '#dcfce7',
    icon: '✅'
  },
  failed: {
    label: 'Failed',
    color: '#dc2626',
    bgColor: '#fee2e2',
    icon: '❌'
  }
};

// Priority configurations
export const TASK_PRIORITY_CONFIGS: Record<TaskPriority, TaskPriorityConfig> = {
  low: {
    label: 'Low',
    color: '#16a34a',
    bgColor: '#dcfce7',
    weight: 1
  },
  medium: {
    label: 'Medium',
    color: '#ea580c',
    bgColor: '#fed7aa',
    weight: 2
  },
  high: {
    label: 'High',
    color: '#dc2626',
    bgColor: '#fecaca',
    weight: 3
  },
  critical: {
    label: 'Critical',
    color: '#7c2d12',
    bgColor: '#fed7aa',
    weight: 4
  }
};

// Utility functions
export function getTaskStatusConfig(status: TaskStatus): TaskStatusConfig {
  return TASK_STATUS_CONFIGS[status] || TASK_STATUS_CONFIGS.pending;
}

export function getTaskPriorityConfig(priority: TaskPriority): TaskPriorityConfig {
  return TASK_PRIORITY_CONFIGS[priority] || TASK_PRIORITY_CONFIGS.medium;
}

export function formatTaskDate(dateString: string): string {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return dateString;
  }
}

export function formatTaskDateTime(dateString: string): string {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateString;
  }
}

export function getTaskDuration(createdAt: string, completedAt?: string): string {
  if (!createdAt) return '';

  const start = new Date(createdAt);
  const end = completedAt ? new Date(completedAt) : new Date();
  const diffMs = end.getTime() - start.getTime();

  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (diffDays > 0) {
    return `${diffDays}d ${diffHours}h`;
  } else if (diffHours > 0) {
    return `${diffHours}h ${diffMinutes}m`;
  } else {
    return `${diffMinutes}m`;
  }
}

export function calculateTaskProgress(tasks: Task[]): number {
  if (tasks.length === 0) return 0;
  const completedTasks = tasks.filter(task => task.status === 'completed').length;
  return Math.round((completedTasks / tasks.length) * 100);
}

export function getTasksByStatus(tasks: Task[]): Record<TaskStatus, Task[]> {
  return tasks.reduce((acc, task) => {
    if (!acc[task.status]) {
      acc[task.status] = [];
    }
    acc[task.status].push(task);
    return acc;
  }, {} as Record<TaskStatus, Task[]>);
}

export function getTasksByPriority(tasks: Task[]): Record<TaskPriority, Task[]> {
  return tasks.reduce((acc, task) => {
    if (!acc[task.priority]) {
      acc[task.priority] = [];
    }
    acc[task.priority].push(task);
    return acc;
  }, {} as Record<TaskPriority, Task[]>);
}

export function sortTasks(tasks: Task[], sortBy: string = 'created_at', sortOrder: 'asc' | 'desc' = 'desc'): Task[] {
  return [...tasks].sort((a, b) => {
    let aValue: any;
    let bValue: any;

    switch (sortBy) {
      case 'title':
        aValue = a.title.toLowerCase();
        bValue = b.title.toLowerCase();
        break;
      case 'priority':
        aValue = TASK_PRIORITY_CONFIGS[a.priority]?.weight || 0;
        bValue = TASK_PRIORITY_CONFIGS[b.priority]?.weight || 0;
        break;
      case 'status':
        aValue = a.status;
        bValue = b.status;
        break;
      case 'updated_at':
        aValue = new Date(a.updated_at);
        bValue = new Date(b.updated_at);
        break;
      case 'created_at':
      default:
        aValue = new Date(a.created_at);
        bValue = new Date(b.created_at);
        break;
    }

    if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });
}

export function filterTasks(tasks: Task[], filters: any = {}): Task[] {
  return tasks.filter(task => {
    // Status filter
    if (filters.status?.length && !filters.status.includes(task.status)) {
      return false;
    }

    // Priority filter
    if (filters.priority?.length && !filters.priority.includes(task.priority)) {
      return false;
    }

    // Team filter
    if (filters.team_id && task.team_id !== filters.team_id) {
      return false;
    }

    // Agent filter
    if (filters.agent_id && task.agent_id !== filters.agent_id) {
      return false;
    }

    // Milestone filter
    if (filters.milestone_id && task.milestone_id !== filters.milestone_id) {
      return false;
    }

    // Date range filter
    if (filters.date_range) {
      const taskDate = new Date(task.created_at);
      if (filters.date_range.from) {
        const fromDate = new Date(filters.date_range.from);
        if (taskDate < fromDate) return false;
      }
      if (filters.date_range.to) {
        const toDate = new Date(filters.date_range.to);
        if (taskDate > toDate) return false;
      }
    }

    // Search filter
    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      const searchableText = `${task.title} ${task.description} ${task.team_name} ${task.agent_name} ${task.milestone_title}`.toLowerCase();
      if (!searchableText.includes(searchTerm)) {
        return false;
      }
    }

    return true;
  });
}

export function getTaskStats(tasks: Task[]) {
  const total = tasks.length;
  const byStatus = getTasksByStatus(tasks);
  const byPriority = getTasksByPriority(tasks);

  return {
    total,
    completed: byStatus.completed?.length || 0,
    inProgress: byStatus.in_progress?.length || 0,
    pending: byStatus.pending?.length || 0,
    failed: byStatus.failed?.length || 0,
    critical: byPriority.critical?.length || 0,
    high: byPriority.high?.length || 0,
    medium: byPriority.medium?.length || 0,
    low: byPriority.low?.length || 0,
    completionRate: total > 0 ? Math.round(((byStatus.completed?.length || 0) / total) * 100) : 0
  };
}

export function convertToTaskDisplay(task: Task): TaskDisplay {
  return {
    ...task,
    isExpanded: false,
    isSelected: false,
    canEdit: true,
    canDelete: true,
    canExecute: task.status === 'pending'
  };
}

export function convertTasksToDisplay(tasks: Task[]): TaskDisplay[] {
  return tasks.map(convertToTaskDisplay);
}
