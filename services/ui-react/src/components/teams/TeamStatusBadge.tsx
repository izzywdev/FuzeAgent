/**
 * Team Status Badge Component
 *
 * Displays a colored badge indicating the team's status.
 * Used throughout the teams interface to show active/inactive status.
 *
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import React from 'react'
import type { TeamStatusBadgeProps } from './types'
import { formatTeamStatus, getTeamStatusColor } from './utils'

const TeamStatusBadge: React.FC<TeamStatusBadgeProps> = ({
  status,
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base'
  }

  return (
    <span
      className={`
        inline-flex items-center font-medium rounded-full border
        ${getTeamStatusColor(status)}
        ${sizeClasses[size]}
      `}
    >
      {formatTeamStatus(status)}
    </span>
  )
}

export default TeamStatusBadge
