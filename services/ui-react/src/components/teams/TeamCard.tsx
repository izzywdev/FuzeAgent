/**
 * Team Card Component
 *
 * Displays a team's information in a card format with actions.
 * Shows team details, stats, and provides edit/delete/view actions.
 *
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import React from 'react'
import type { TeamCardProps } from './types'
import TeamStatusBadge from './TeamStatusBadge'
import TeamTypeBadge from './TeamTypeBadge'
import {
  formatMemberCount,
  formatTaskCount,
  formatEfficiencyRate,
  calculateCompletionRate,
  getTeamPerformanceIndicator,
  getPerformanceIndicatorColor
} from './utils'

const TeamCard: React.FC<TeamCardProps> = ({
  team,
  onEdit,
  onDelete,
  onViewDetails,
  showStats = true
}) => {
  const completionRate = calculateCompletionRate(team)
  const performanceIndicator = getTeamPerformanceIndicator(team)
  const performanceColor = getPerformanceIndicatorColor(performanceIndicator)

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {team.name}
          </h3>
          <div className="flex items-center gap-2 mb-2">
            <TeamTypeBadge teamType={team.team_type} size="sm" />
            <TeamStatusBadge status={team.status} size="sm" />
          </div>
          {team.description && (
            <p className="text-sm text-gray-600 line-clamp-2">
              {team.description}
            </p>
          )}
        </div>
      </div>

      {/* Stats */}
      {showStats && (
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {team.agent_count}
            </div>
            <div className="text-sm text-gray-600">
              {formatMemberCount(team.agent_count)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {team.task_count}
            </div>
            <div className="text-sm text-gray-600">
              {formatTaskCount(team.task_count)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {completionRate}%
            </div>
            <div className="text-sm text-gray-600">Completion Rate</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-bold ${performanceColor}`}>
              {formatEfficiencyRate(team.efficiency_rate)}
            </div>
            <div className="text-sm text-gray-600">Efficiency</div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-100">
        <div className="text-xs text-gray-500">
          Created {new Date(team.created_at).toLocaleDateString()}
        </div>
        <div className="flex items-center gap-2">
          {onViewDetails && (
            <button
              onClick={() => onViewDetails(team)}
              className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors"
            >
              View Details
            </button>
          )}
          {onEdit && (
            <button
              onClick={() => onEdit(team)}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded-md transition-colors"
            >
              Edit
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(team.id)}
              className="px-3 py-1 text-sm text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default TeamCard
