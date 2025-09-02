/**
 * Milestone List Component
 *
 * Displays a list of milestones with sorting, filtering, and pagination capabilities.
 * Provides a comprehensive view of milestones with actions and status indicators.
 */

import React from 'react'
import type { MilestoneListProps } from './types'
import { MilestoneCard } from './MilestoneCard'

export function MilestoneList({
  milestones,
  loading,
  error,
  onEdit,
  onDelete,
  onViewTasks,
  onCreateTask,
  selectedMilestoneId,
  onSelectMilestone
}: MilestoneListProps): React.ReactElement {
  if (loading) {
    return (
      <div className="space-y-4">
        {/* Loading skeleton */}
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
            <div className="flex items-start justify-between">
              <div className="flex-1 space-y-2">
                <div className="h-5 bg-gray-200 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 rounded w-full"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              </div>
              <div className="flex space-x-2">
                <div className="h-8 w-8 bg-gray-200 rounded"></div>
                <div className="h-8 w-8 bg-gray-200 rounded"></div>
                <div className="h-8 w-8 bg-gray-200 rounded"></div>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
              <div className="h-2 bg-gray-200 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <div className="text-red-600 mr-3">⚠️</div>
          <div>
            <h3 className="text-sm font-medium text-red-800">
              Error loading milestones
            </h3>
            <p className="text-sm text-red-700 mt-1">
              {error}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (milestones.length === 0) {
    return (
      <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
        <div className="text-gray-400 mb-4">
          <div className="text-4xl">🎯</div>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No milestones found
        </h3>
        <p className="text-gray-600">
          Get started by creating your first milestone for this goal.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Milestones count */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">
          Milestones ({milestones.length})
        </h2>
      </div>

      {/* Milestones grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {milestones.map((milestone) => (
          <MilestoneCard
            key={milestone.id}
            milestone={milestone}
            onEdit={onEdit}
            onDelete={onDelete}
            onViewTasks={onViewTasks}
            onCreateTask={onCreateTask}
            isSelected={selectedMilestoneId === milestone.id}
            onSelect={onSelectMilestone}
          />
        ))}
      </div>

      {/* Summary stats */}
      <div className="bg-gray-50 rounded-lg p-4 mt-6">
        <h3 className="text-sm font-medium text-gray-700 mb-3">Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {milestones.filter(m => m.status === 'completed').length}
            </div>
            <div className="text-gray-600">Completed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {milestones.filter(m => m.status === 'in_progress').length}
            </div>
            <div className="text-gray-600">In Progress</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-600">
              {milestones.filter(m => m.status === 'not_started').length}
            </div>
            <div className="text-gray-600">Not Started</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">
              {milestones.filter(m => m.isOverdue).length}
            </div>
            <div className="text-gray-600">Overdue</div>
          </div>
        </div>
      </div>
    </div>
  )
}
