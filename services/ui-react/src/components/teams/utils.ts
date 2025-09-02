/**
 * Teams Component Utilities
 *
 * This file contains utility functions and helpers for the Teams components.
 * These include formatting functions, validation helpers, and data transformation utilities.
 *
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import type { Team, TeamCreate, TeamUpdate, TeamFilters, TeamFormErrors } from './types'

// ============================================================================
// FORMATTING UTILITIES
// ============================================================================

/**
 * Format team type for display
 */
export function formatTeamType(teamType: Team['team_type']): string {
  const typeMap: Record<Team['team_type'], string> = {
    development: 'Development',
    operations: 'Operations',
    management: 'Management',
    research: 'Research'
  }
  return typeMap[teamType] || teamType
}

/**
 * Format team status for display
 */
export function formatTeamStatus(status: Team['status']): string {
  const statusMap: Record<Team['status'], string> = {
    active: 'Active',
    inactive: 'Inactive'
  }
  return statusMap[status] || status
}

/**
 * Format efficiency rate as percentage
 */
export function formatEfficiencyRate(rate: number): string {
  return `${rate.toFixed(1)}%`
}

/**
 * Format member count for display
 */
export function formatMemberCount(count: number): string {
  if (count === 0) return 'No members'
  if (count === 1) return '1 member'
  return `${count} members`
}

/**
 * Format task count for display
 */
export function formatTaskCount(count: number): string {
  if (count === 0) return 'No tasks'
  if (count === 1) return '1 task'
  return `${count} tasks`
}

/**
 * Get team status color class
 */
export function getTeamStatusColor(status: Team['status']): string {
  const colorMap: Record<Team['status'], string> = {
    active: 'bg-green-100 text-green-800 border-green-200',
    inactive: 'bg-gray-100 text-gray-800 border-gray-200'
  }
  return colorMap[status] || 'bg-gray-100 text-gray-800 border-gray-200'
}

/**
 * Get team type color class
 */
export function getTeamTypeColor(teamType: Team['team_type']): string {
  const colorMap: Record<Team['team_type'], string> = {
    development: 'bg-blue-100 text-blue-800 border-blue-200',
    operations: 'bg-orange-100 text-orange-800 border-orange-200',
    management: 'bg-purple-100 text-purple-800 border-purple-200',
    research: 'bg-indigo-100 text-indigo-800 border-indigo-200'
  }
  return colorMap[teamType] || 'bg-gray-100 text-gray-800 border-gray-200'
}

// ============================================================================
// VALIDATION UTILITIES
// ============================================================================

/**
 * Validate team creation data
 */
export function validateTeamCreate(data: TeamCreate): TeamFormErrors {
  const errors: TeamFormErrors = {}

  if (!data.name?.trim()) {
    errors.name = 'Team name is required'
  } else if (data.name.trim().length < 2) {
    errors.name = 'Team name must be at least 2 characters'
  } else if (data.name.trim().length > 100) {
    errors.name = 'Team name must be less than 100 characters'
  }

  if (data.description && data.description.length > 500) {
    errors.description = 'Description must be less than 500 characters'
  }

  if (data.team_type && !['development', 'operations', 'management', 'research'].includes(data.team_type)) {
    errors.team_type = 'Invalid team type'
  }

  if (data.color && !/^#[0-9A-Fa-f]{6}$/.test(data.color)) {
    errors.color = 'Color must be a valid hex color (e.g., #FF0000)'
  }

  return errors
}

/**
 * Validate team update data
 */
export function validateTeamUpdate(data: TeamUpdate): TeamFormErrors {
  const errors: TeamFormErrors = {}

  if (data.name !== undefined) {
    if (!data.name?.trim()) {
      errors.name = 'Team name is required'
    } else if (data.name.trim().length < 2) {
      errors.name = 'Team name must be at least 2 characters'
    } else if (data.name.trim().length > 100) {
      errors.name = 'Team name must be less than 100 characters'
    }
  }

  if (data.description && data.description.length > 500) {
    errors.description = 'Description must be less than 500 characters'
  }

  if (data.team_type && !['development', 'operations', 'management', 'research'].includes(data.team_type)) {
    errors.team_type = 'Invalid team type'
  }

  if (data.status && !['active', 'inactive'].includes(data.status)) {
    errors.status = 'Invalid status'
  }

  if (data.color && !/^#[0-9A-Fa-f]{6}$/.test(data.color)) {
    errors.color = 'Color must be a valid hex color (e.g., #FF0000)'
  }

  return errors
}

// ============================================================================
// DATA TRANSFORMATION UTILITIES
// ============================================================================

/**
 * Create default team creation data
 */
export function createDefaultTeamCreate(): TeamCreate {
  return {
    name: '',
    description: '',
    team_type: 'development',
    color: '#2563eb'
  }
}

/**
 * Create team update data from team
 */
export function createTeamUpdateFromTeam(team: Team): TeamUpdate {
  return {
    name: team.name,
    description: team.description,
    team_type: team.team_type,
    color: team.color,
    status: team.status,
    settings: team.settings
  }
}

/**
 * Create default team filters
 */
export function createDefaultTeamFilters(): TeamFilters {
  return {
    status: [],
    team_type: [],
    search: '',
    sort_by: 'created_at',
    sort_order: 'desc'
  }
}

// ============================================================================
// SORTING AND FILTERING UTILITIES
// ============================================================================

/**
 * Sort teams by given criteria
 */
export function sortTeams(teams: Team[], sortBy: string, sortOrder: 'asc' | 'desc'): Team[] {
  return [...teams].sort((a, b) => {
    let aValue: any = a[sortBy as keyof Team]
    let bValue: any = b[sortBy as keyof Team]

    // Handle string comparison
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      aValue = aValue.toLowerCase()
      bValue = bValue.toLowerCase()
    }

    // Handle numeric comparison
    if (typeof aValue === 'number' && typeof bValue === 'number') {
      return sortOrder === 'asc' ? aValue - bValue : bValue - aValue
    }

    // Handle string comparison
    if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1
    if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1
    return 0
  })
}

/**
 * Filter teams by search term
 */
export function filterTeamsBySearch(teams: Team[], searchTerm: string): Team[] {
  if (!searchTerm.trim()) return teams

  const term = searchTerm.toLowerCase()
  return teams.filter(team =>
    team.name.toLowerCase().includes(term) ||
    team.description.toLowerCase().includes(term) ||
    team.team_type.toLowerCase().includes(term)
  )
}

/**
 * Filter teams by status
 */
export function filterTeamsByStatus(teams: Team[], statuses: string[]): Team[] {
  if (!statuses.length) return teams
  return teams.filter(team => statuses.includes(team.status))
}

/**
 * Filter teams by type
 */
export function filterTeamsByType(teams: Team[], types: string[]): Team[] {
  if (!types.length) return teams
  return teams.filter(team => types.includes(team.team_type))
}

// ============================================================================
// STATISTICS UTILITIES
// ============================================================================

/**
 * Calculate team completion rate
 */
export function calculateCompletionRate(team: Team): number {
  if (team.task_count === 0) return 0
  return Math.round((team.completed_task_count / team.task_count) * 100)
}

/**
 * Get team performance indicator
 */
export function getTeamPerformanceIndicator(team: Team): 'excellent' | 'good' | 'average' | 'poor' {
  const efficiency = team.efficiency_rate
  if (efficiency >= 90) return 'excellent'
  if (efficiency >= 75) return 'good'
  if (efficiency >= 60) return 'average'
  return 'poor'
}

/**
 * Get performance indicator color
 */
export function getPerformanceIndicatorColor(indicator: ReturnType<typeof getTeamPerformanceIndicator>): string {
  const colorMap = {
    excellent: 'text-green-600',
    good: 'text-blue-600',
    average: 'text-yellow-600',
    poor: 'text-red-600'
  }
  return colorMap[indicator]
}
