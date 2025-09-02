/**
 * Milestone Priority Badge Component
 *
 * Displays milestone priority with appropriate styling and icons.
 * Supports different sizes and variants for various contexts.
 */

import React from 'react'
import type { MilestonePriorityBadgeProps } from './types'
import { MILESTONE_PRIORITY_CONFIG } from './types'

export function MilestonePriorityBadge({
  priority,
  size = 'medium',
  variant = 'filled'
}: MilestonePriorityBadgeProps): React.ReactElement {
  const config = MILESTONE_PRIORITY_CONFIG[priority]

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

  // Priority icons
  const priorityIcons = {
    low: '↓',
    medium: '→',
    high: '↑',
    critical: '‼'
  }

  return (
    <span
      className={`${baseClasses} ${variantClasses}`}
      role="status"
      aria-label={`Priority: ${config.label}`}
    >
      <span className="relative inline-flex items-center">
        {/* Priority indicator */}
        <span className="mr-1 font-bold" aria-hidden="true">
          {priorityIcons[priority]}
        </span>
        {config.label}
      </span>
    </span>
  )
}
