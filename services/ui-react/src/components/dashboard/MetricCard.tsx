/**
 * MetricCard - Displays a single metric with optional change indicator
 * 
 * This component is used throughout the dashboard to display key performance indicators
 * such as total agents, active agents, tasks completed, etc.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import React from 'react'

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

/**
 * Represents the change indicator for a metric
 */
interface MetricChange {
  /** The change value (e.g., "+2", "-5%", "+12%") */
  value: string
  /** The type of change (increase or decrease) */
  type: 'increase' | 'decrease'
}

/**
 * Props for the MetricCard component
 */
interface MetricCardProps {
  /** The title/name of the metric */
  title: string
  /** The current value of the metric */
  value: string | number
  /** Optional change indicator */
  change?: MetricChange
  /** Optional icon to display */
  icon?: React.ReactNode
  /** Optional CSS class for custom styling */
  className?: string
}

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * MetricCard component for displaying dashboard metrics
 * 
 * @param props - The component props
 * @returns JSX.Element - The rendered metric card
 */
export function MetricCard({
  title,
  value,
  change,
  icon,
  className = ''
}: MetricCardProps): JSX.Element {
  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  /**
   * Get the appropriate color class for the change indicator
   */
  const getChangeColorClass = (): string => {
    if (!change) return ''
    
    return change.type === 'increase' 
      ? 'text-green-600 bg-green-100' 
      : 'text-red-600 bg-red-100'
  }

  /**
   * Get the appropriate icon for the change indicator
   */
  const getChangeIcon = (): React.ReactNode => {
    if (!change) return null
    
    return change.type === 'increase' ? (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L12 10.586 14.586 8H12z" clipRule="evenodd" />
      </svg>
    ) : (
      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M12 13a1 1 0 100 2h5a1 1 0 001-1v-5a1 1 0 10-2 0v2.586l-4.293-4.293a1 1 0 00-1.414 0L8 9.586l-4.293-4.293a1 1 0 00-1.414 1.414l5 5a1 1 0 001.414 0L12 9.414 14.586 12H12z" clipRule="evenodd" />
      </svg>
    )
  }

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className={`bg-white p-6 rounded-lg border border-gray-200 shadow-sm ${className}`}>
      <div className="flex items-center justify-between">
        {/* Icon and Title */}
        <div className="flex items-center">
          {icon && (
            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mr-4">
              {icon}
            </div>
          )}
          <div>
            <h3 className="text-sm font-medium text-gray-600">{title}</h3>
            <p className="text-2xl font-semibold text-gray-900 mt-1">{value}</p>
          </div>
        </div>

        {/* Change Indicator */}
        {change && (
          <div className={`flex items-center px-2 py-1 rounded-full text-xs font-medium ${getChangeColorClass()}`}>
            {getChangeIcon()}
            <span className="ml-1">{change.value}</span>
          </div>
        )}
      </div>
    </div>
  )
}