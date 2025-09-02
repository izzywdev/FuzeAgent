/**
 * Team Type Badge Component
 *
 * Displays a colored badge indicating the team's type.
 * Used throughout the teams interface to show development/operations/etc. type.
 *
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import React from 'react'
import type { TeamTypeBadgeProps } from './types'
import { formatTeamType, getTeamTypeColor } from './utils'

const TeamTypeBadge: React.FC<TeamTypeBadgeProps> = ({
  teamType,
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
        ${getTeamTypeColor(teamType)}
        ${sizeClasses[size]}
      `}
    >
      {formatTeamType(teamType)}
    </span>
  )
}

export default TeamTypeBadge
