/**
 * Milestone Progress Component
 *
 * Displays milestone progress with animated progress bars and status indicators.
 * Supports different sizes and visual styles.
 */

import React from 'react'
import type { MilestoneProgressProps } from './types'
import { getProgressColor } from './utils'

export function MilestoneProgress({
  progress,
  status,
  size = 'medium',
  showLabel = true,
  animated = true
}: MilestoneProgressProps): React.ReactElement {
  const progressColor = getProgressColor(progress)

  const sizeClasses = {
    small: {
      container: 'h-2',
      text: 'text-xs'
    },
    medium: {
      container: 'h-3',
      text: 'text-sm'
    },
    large: {
      container: 'h-4',
      text: 'text-base'
    }
  }

  const isCompleted = status === 'completed'
  const isBlocked = status === 'blocked'

  // Adjust progress bar appearance based on status
  let displayProgress = progress
  let barColor = progressColor

  if (isCompleted) {
    displayProgress = 100
    barColor = '#16a34a' // green
  } else if (isBlocked) {
    barColor = '#dc2626' // red
  }

  return (
    <div className="flex items-center space-x-3">
      {/* Progress bar */}
      <div
        className={`
          flex-1 bg-gray-200 rounded-full overflow-hidden
          ${sizeClasses[size].container}
        `}
        role="progressbar"
        aria-valuenow={displayProgress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Progress: ${displayProgress}%`}
      >
        <div
          className={`
            h-full rounded-full transition-all duration-500 ease-out
            ${animated ? 'transition-all duration-1000 ease-out' : ''}
            ${isBlocked ? 'bg-red-500' : ''}
          `}
          style={{
            width: `${displayProgress}%`,
            backgroundColor: isBlocked ? undefined : barColor,
            transition: animated ? 'width 0.5s ease-out' : 'none'
          }}
        />
      </div>

      {/* Progress label */}
      {showLabel && (
        <div className={`text-gray-600 font-medium ${sizeClasses[size].text} min-w-[3rem] text-right`}>
          {displayProgress}%
        </div>
      )}

      {/* Status indicators */}
      <div className="flex items-center space-x-1">
        {isCompleted && (
          <span className="text-green-600" aria-label="Completed">
            ✓
          </span>
        )}
        {isBlocked && (
          <span className="text-red-600" aria-label="Blocked">
            ⚠
          </span>
        )}
      </div>
    </div>
  )
}
