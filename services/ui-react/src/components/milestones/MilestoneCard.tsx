/**
 * Milestone Card Component
 *
 * Displays a milestone in card format with all relevant information,
 * progress indicators, and action buttons.
 */

import React from 'react'
import type { MilestoneCardProps } from './types'
import { MilestoneStatusBadge } from './MilestoneStatusBadge'
import { MilestonePriorityBadge } from './MilestonePriorityBadge'
import { MilestoneProgress } from './MilestoneProgress'

export function MilestoneCard({
  milestone,
  onEdit,
  onDelete,
  onViewTasks,
  onCreateTask,
  isSelected = false,
  onSelect
}: MilestoneCardProps): React.ReactElement {
  const handleCardClick = () => {
    if (onSelect) {
      onSelect(milestone.id)
    }
  }

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    onEdit(milestone)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm(`Are you sure you want to delete "${milestone.title}"? This action cannot be undone.`)) {
      onDelete(milestone)
    }
  }

  const handleViewTasks = (e: React.MouseEvent) => {
    e.stopPropagation()
    onViewTasks(milestone)
  }

  const handleCreateTask = (e: React.MouseEvent) => {
    e.stopPropagation()
    onCreateTask(milestone)
  }

  return (
    <div
      className={`
        bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow duration-200 cursor-pointer
        ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'border-gray-200'}
        ${milestone.isOverdue ? 'border-red-300 bg-red-50' : ''}
      `}
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          handleCardClick()
        }
      }}
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate">
              {milestone.title}
            </h3>
            <p className="text-sm text-gray-600 mt-1 line-clamp-2">
              {milestone.description}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center space-x-2 ml-4">
            <button
              onClick={handleViewTasks}
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
              title="View tasks"
              aria-label={`View tasks for ${milestone.title}`}
            >
              📋
            </button>
            <button
              onClick={handleCreateTask}
              className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-md transition-colors"
              title="Create task"
              aria-label={`Create task for ${milestone.title}`}
            >
              ➕
            </button>
            <button
              onClick={handleEdit}
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
              title="Edit milestone"
              aria-label={`Edit ${milestone.title}`}
            >
              ✏️
            </button>
            <button
              onClick={handleDelete}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
              title="Delete milestone"
              aria-label={`Delete ${milestone.title}`}
            >
              🗑️
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Status and Priority */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MilestoneStatusBadge status={milestone.status} size="small" />
            <MilestonePriorityBadge priority={milestone.priority} size="small" />
          </div>

          {/* Task count */}
          <div className="text-sm text-gray-600">
            {milestone.task_count || 0} tasks
          </div>
        </div>

        {/* Progress */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-sm text-gray-600">
              {milestone.completed_task_count || 0} / {milestone.task_count || 0} completed
            </span>
          </div>
          <MilestoneProgress
            progress={milestone.progress_percentage}
            status={milestone.status}
            size="medium"
            showLabel={true}
            animated={true}
          />
        </div>

        {/* Dates */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <span className="text-gray-500">🎯</span>
              <span className={milestone.isOverdue ? 'text-red-600 font-medium' : 'text-gray-600'}>
                {milestone.targetDateFormatted}
              </span>
            </div>

            {milestone.completedAtFormatted && (
              <div className="flex items-center space-x-1">
                <span className="text-green-500">✅</span>
                <span className="text-gray-600">
                  {milestone.completedAtFormatted}
                </span>
              </div>
            )}
          </div>

          {/* Days remaining */}
          {milestone.daysUntilTarget !== 0 && milestone.status !== 'completed' && (
            <div className={`text-sm font-medium ${
              milestone.isOverdue ? 'text-red-600' : 'text-gray-600'
            }`}>
              {milestone.isOverdue
                ? `${Math.abs(milestone.daysUntilTarget)} days overdue`
                : `${milestone.daysUntilTarget} days left`
              }
            </div>
          )}
        </div>
      </div>

      {/* Footer - Goal information */}
      {milestone.goal && (
        <div className="px-4 pb-3">
          <div className="text-xs text-gray-500">
            Part of: <span className="font-medium text-gray-700">{milestone.goal.title}</span>
          </div>
        </div>
      )}
    </div>
  )
}
