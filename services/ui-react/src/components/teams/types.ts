/**
 * Teams Component Types
 *
 * This file contains all TypeScript interfaces and types used by the Teams components.
 * These types are specific to the UI layer and extend the base types from the main types file.
 *
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import type { Team, TeamCreate, TeamUpdate, TeamFilters, TeamMember, TeamStats } from '../../types'

// Extended types for UI components
export interface TeamCardProps {
  team: Team
  onEdit?: (team: Team) => void
  onDelete?: (teamId: string) => void
  onViewDetails?: (team: Team) => void
  showStats?: boolean
}

export interface TeamListProps {
  teams: Team[]
  loading?: boolean
  error?: string | null
  onEdit?: (team: Team) => void
  onDelete?: (teamId: string) => void
  onViewDetails?: (team: Team) => void
  onRetry?: () => void
  showStats?: boolean
}

export interface TeamFormModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: TeamCreate | TeamUpdate) => Promise<void>
  initialData?: Team
  mode: 'create' | 'edit'
  loading?: boolean
  error?: string | null
}

export interface TeamStatusBadgeProps {
  status: Team['status']
  size?: 'sm' | 'md' | 'lg'
}

export interface TeamTypeBadgeProps {
  teamType: Team['team_type']
  size?: 'sm' | 'md' | 'lg'
}

export interface TeamStatsCardProps {
  stats: TeamStats
  loading?: boolean
}

export interface TeamMemberCardProps {
  member: TeamMember
  onRemove?: (agentId: string) => void
  showPerformance?: boolean
}

export interface TeamMemberListProps {
  members: TeamMember[]
  loading?: boolean
  onRemoveMember?: (agentId: string) => void
  showPerformance?: boolean
}

// Form validation types
export interface TeamFormErrors {
  name?: string
  description?: string
  team_type?: string
  color?: string
  settings?: string
}

// Filter and search types
export interface TeamListFilters extends TeamFilters {
  onFilterChange?: (filters: TeamFilters) => void
  onSearchChange?: (search: string) => void
  onSortChange?: (sortBy: string, sortOrder: 'asc' | 'desc') => void
}

// Pagination types
export interface TeamPaginationProps {
  currentPage: number
  totalPages: number
  totalItems: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
}

// Export base types for convenience
export type { Team, TeamCreate, TeamUpdate, TeamFilters, TeamMember, TeamStats }
