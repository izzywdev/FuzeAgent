/**
 * Milestone Status Badge Component
 *
 * Displays milestone status with appropriate styling and icons.
 * Supports different sizes and variants for various contexts.
 */

import React from 'react'
import type { MilestoneStatusBadgeProps } from './types'
import { MILESTONE_STATUS_CONFIG } from './types'

export function MilestoneStatusBadge({
  status,
  size = 'medium',
  variant = 'filled'
}: MilestoneStatusBadgeProps): React.ReactElement {
  const config = MILESTONE_STATUS_CONFIG[status]

  const sizeClasses = {
    small: 'px-2 py-1 text-xs',
    medium: 'px-2.5 py-1.5 text-sm',
    large: 'px-3 py-2 text-base'
  }

  const baseClasses = `
    inline-flex items-center font-medium rounded-full
    ${sizeClasses[size]}
    transition-colors duration-200
  `

  const variantClasses = variant === 'filled'
    ? `bg-[${config.bgColor}] text-[${config.color}] border border-[${config.borderColor}]`
    : `border-2 border-[${config.borderColor}] text-[${config.color}] bg-transparent hover:bg-[${config.bgColor}]`

  return (
    <span
      className={`${baseClasses} ${variantClasses}`}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      <span className="relative inline-flex items-center">
        {/* Status indicator dot */}
        <span
          className="w-2 h-2 rounded-full mr-2"
          style={{ backgroundColor: config.color }}
          aria-hidden="true"
        />
        {config.label}
      </span>
    </span>
  )
}
