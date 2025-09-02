/**
 * Milestones Utility Functions
 *
 * This file contains utility functions for milestone data manipulation,
 * formatting, and business logic operations.
 */

import type {
  Milestone,
  MilestoneDisplay,
  MilestoneStats,
  Task
} from './types'
import { MILESTONE_STATUS_CONFIG, MILESTONE_PRIORITY_CONFIG, PROGRESS_THRESHOLDS } from './types'

/**
 * Convert a milestone to display format with additional UI properties
 */
export function milestoneToDisplay(milestone: Milestone): MilestoneDisplay {
  const now = new Date()
  const targetDate = new Date(milestone.target_date)
  const daysUntilTarget = Math.ceil((targetDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))

  return {
    ...milestone,
    targetDateFormatted: formatDate(milestone.target_date),
    completedAtFormatted: milestone.completed_at ? formatDate(milestone.completed_at) : undefined,
    progressDisplay: `${milestone.progress_percentage}%`,
    statusLabel: MILESTONE_STATUS_CONFIG[milestone.status].label,
    priorityLabel: MILESTONE_PRIORITY_CONFIG[milestone.priority].label,
    statusClass: getStatusClass(milestone.status),
    priorityClass: getPriorityClass(milestone.priority),
    isOverdue: daysUntilTarget < 0 && milestone.status !== 'completed',
    daysUntilTarget
  }
}

/**
 * Convert multiple milestones to display format
 */
export function milestonesToDisplay(milestones: Milestone[]): MilestoneDisplay[] {
  return milestones.map(milestoneToDisplay)
}

/**
 * Format date for display
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

/**
 * Format date and time for display
 */
export function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * Get CSS class for milestone status
 */
export function getStatusClass(status: Milestone['status']): string {
  const config = MILESTONE_STATUS_CONFIG[status]
  return `bg-[${config.bgColor}] text-[${config.color}] border border-[${config.borderColor}]`
}

/**
 * Get CSS class for milestone priority
 */
export function getPriorityClass(priority: Milestone['priority']): string {
  const config = MILESTONE_PRIORITY_CONFIG[priority]
  return `bg-[${config.bgColor}] text-[${config.color}] border border-[${config.borderColor}]`
}

/**
 * Calculate milestone statistics
 */
export function calculateMilestoneStats(milestones: Milestone[]): MilestoneStats {
  const total = milestones.length
  const completed = milestones.filter(m => m.status === 'completed').length
  const inProgress = milestones.filter(m => m.status === 'in_progress').length
  const notStarted = milestones.filter(m => m.status === 'not_started').length
  const blocked = milestones.filter(m => m.status === 'blocked').length
  const overdue = milestones.filter(m => {
    const targetDate = new Date(m.target_date)
    const now = new Date()
    return targetDate < now && m.status !== 'completed'
  }).length

  return {
    total,
    completed,
    inProgress,
    notStarted,
    blocked,
    overdue,
    completionRate: total > 0 ? Math.round((completed / total) * 100) : 0
  }
}

/**
 * Get progress color based on percentage
 */
export function getProgressColor(progress: number): string {
  if (progress >= PROGRESS_THRESHOLDS.excellent) return '#16a34a' // green
  if (progress >= PROGRESS_THRESHOLDS.good) return '#2563eb' // blue
  if (progress >= PROGRESS_THRESHOLDS.fair) return '#f59e0b' // amber
  if (progress >= PROGRESS_THRESHOLDS.poor) return '#ea580c' // orange
  return '#dc2626' // red
}

/**
 * Calculate milestone progress based on tasks
 */
export function calculateProgressFromTasks(tasks: Task[]): number {
  if (tasks.length === 0) return 0

  const completedTasks = tasks.filter(task => task.status === 'completed').length
  return Math.round((completedTasks / tasks.length) * 100)
}

/**
 * Get milestone status based on progress and tasks
 */
export function getStatusFromProgress(
  currentStatus: Milestone['status'],
  progress: number,
  hasTasks: boolean
): Milestone['status'] {
  if (progress === 100 && hasTasks) {
    return 'completed'
  }
  if (progress > 0 && currentStatus === 'not_started') {
    return 'in_progress'
  }
  return currentStatus
}

/**
 * Validate milestone data
 */
export function validateMilestoneData(data: {
  title: string
  description: string
  target_date: string
  goal_id?: string
}): { isValid: boolean; errors: string[] } {
  const errors: string[] = []

  if (!data.title.trim()) {
    errors.push('Title is required')
  }

  if (!data.description.trim()) {
    errors.push('Description is required')
  }

  if (!data.target_date) {
    errors.push('Target date is required')
  } else {
    const targetDate = new Date(data.target_date)
    const now = new Date()
    if (targetDate < now) {
      errors.push('Target date must be in the future')
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  }
}

/**
 * Sort milestones by various criteria
 */
export function sortMilestones(
  milestones: Milestone[],
  sortBy: 'created_at' | 'target_date' | 'priority' | 'progress_percentage' | 'title',
  sortOrder: 'asc' | 'desc' = 'desc'
): Milestone[] {
  const sorted = [...milestones].sort((a, b) => {
    let comparison = 0

    switch (sortBy) {
      case 'created_at':
        comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        break
      case 'target_date':
        comparison = new Date(a.target_date).getTime() - new Date(b.target_date).getTime()
        break
      case 'priority':
        const priorityOrder = { low: 1, medium: 2, high: 3, critical: 4 }
        comparison = priorityOrder[a.priority] - priorityOrder[b.priority]
        break
      case 'progress_percentage':
        comparison = a.progress_percentage - b.progress_percentage
        break
      case 'title':
        comparison = a.title.localeCompare(b.title)
        break
    }

    return sortOrder === 'desc' ? -comparison : comparison
  })

  return sorted
}

/**
 * Filter milestones by various criteria
 */
export function filterMilestones(
  milestones: Milestone[],
  filters: {
    status?: string[]
    priority?: string[]
    search?: string
    goal_id?: string
  }
): Milestone[] {
  return milestones.filter(milestone => {
    // Filter by goal
    if (filters.goal_id && milestone.goal_id !== filters.goal_id) {
      return false
    }

    // Filter by status
    if (filters.status && filters.status.length > 0 && !filters.status.includes(milestone.status)) {
      return false
    }

    // Filter by priority
    if (filters.priority && filters.priority.length > 0 && !filters.priority.includes(milestone.priority)) {
      return false
    }

    // Filter by search
    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      const matchesTitle = milestone.title.toLowerCase().includes(searchLower)
      const matchesDescription = milestone.description.toLowerCase().includes(searchLower)
      if (!matchesTitle && !matchesDescription) {
        return false
      }
    }

    return true
  })
}

/**
 * Get milestones due within a timeframe
 */
export function getMilestonesDueWithin(
  milestones: Milestone[],
  days: number
): Milestone[] {
  const now = new Date()
  const futureDate = new Date()
  futureDate.setDate(now.getDate() + days)

  return milestones.filter(milestone => {
    const targetDate = new Date(milestone.target_date)
    return targetDate >= now && targetDate <= futureDate && milestone.status !== 'completed'
  })
}

/**
 * Get overdue milestones
 */
export function getOverdueMilestones(milestones: Milestone[]): Milestone[] {
  const now = new Date()
  return milestones.filter(milestone => {
    const targetDate = new Date(milestone.target_date)
    return targetDate < now && milestone.status !== 'completed'
  })
}

/**
 * Group milestones by status
 */
export function groupMilestonesByStatus(milestones: Milestone[]): Record<string, Milestone[]> {
  return milestones.reduce((groups, milestone) => {
    if (!groups[milestone.status]) {
      groups[milestone.status] = []
    }
    groups[milestone.status].push(milestone)
    return groups
  }, {} as Record<string, Milestone[]>)
}

/**
 * Group milestones by priority
 */
export function groupMilestonesByPriority(milestones: Milestone[]): Record<string, Milestone[]> {
  return milestones.reduce((groups, milestone) => {
    if (!groups[milestone.priority]) {
      groups[milestone.priority] = []
    }
    groups[milestone.priority].push(milestone)
    return groups
  }, {} as Record<string, Milestone[]>)
}
