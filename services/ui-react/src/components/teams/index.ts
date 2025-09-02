/**
 * Teams Components Index
 *
 * Central export file for all team-related components.
 * Import from this file to access all team components.
 *
 * @author FuzeAgent Team
 * @version 1.0.0
 */

// Main Components
export { default as TeamCard } from './TeamCard'
export { default as TeamList } from './TeamList'
export { default as TeamFormModal } from './TeamFormModal'
export { default as TeamStatusBadge } from './TeamStatusBadge'
export { default as TeamTypeBadge } from './TeamTypeBadge'

// Types
export type {
  TeamCardProps,
  TeamListProps,
  TeamFormModalProps,
  TeamStatusBadgeProps,
  TeamTypeBadgeProps,
  TeamFormErrors,
  TeamListFilters,
  TeamPaginationProps,
  TeamMember,
  TeamStats
} from './types'

// Utilities
export {
  formatTeamType,
  formatTeamStatus,
  formatEfficiencyRate,
  formatMemberCount,
  formatTaskCount,
  getTeamStatusColor,
  getTeamTypeColor,
  validateTeamCreate,
  validateTeamUpdate,
  createDefaultTeamCreate,
  createTeamUpdateFromTeam,
  createDefaultTeamFilters,
  sortTeams,
  filterTeamsBySearch,
  filterTeamsByStatus,
  filterTeamsByType,
  calculateCompletionRate,
  getTeamPerformanceIndicator,
  getPerformanceIndicatorColor
} from './utils'
