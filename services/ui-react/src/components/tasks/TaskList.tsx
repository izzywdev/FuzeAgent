import React from 'react';
import { TaskCard } from './TaskCard';
import { convertTasksToDisplay } from './utils';
import type { TaskListProps } from './types';
import type { Task } from '../../types';

export function TaskList({
  tasks,
  loading = false,
  error = null,
  onTaskUpdate,
  onTaskDelete,
  onTaskExecute,
  onTaskClick,
  showFilters = true,
  showPagination = true,
  className = ''
}: TaskListProps) {
  const taskDisplays = convertTasksToDisplay(tasks);

  if (loading) {
    return (
      <div className={`flex items-center justify-center py-12 ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading tasks...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-red-50 border border-red-200 rounded-lg p-6 ${className}`}>
        <div className="text-center">
          <div className="text-red-600 mb-2">⚠️</div>
          <p className="text-red-800 font-medium mb-2">Error loading tasks</p>
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className={`text-center py-12 ${className}`}>
        <div className="text-gray-400 mb-4">
          <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No tasks found</h3>
        <p className="text-gray-600">Get started by creating your first task.</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Summary */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {tasks.length} Task{tasks.length !== 1 ? 's' : ''}
            </h3>
            <p className="text-sm text-gray-600">
              {tasks.filter(t => t.status === 'completed').length} completed •
              {tasks.filter(t => t.status === 'in_progress').length} in progress •
              {tasks.filter(t => t.status === 'pending').length} pending
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span className="text-sm text-gray-600">Completed</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-sm text-gray-600">In Progress</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
              <span className="text-sm text-gray-600">Pending</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tasks Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {taskDisplays.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onEdit={onTaskUpdate ? (task) => onTaskUpdate(task.id, { title: task.title }) : undefined}
            onDelete={onTaskDelete}
            onExecute={onTaskExecute}
            onClick={onTaskClick}
          />
        ))}
      </div>
    </div>
  );
}
