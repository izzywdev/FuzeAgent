import React, { useState } from 'react';
import { TaskStatusBadge } from './TaskStatusBadge';
import { TaskPriorityBadge } from './TaskPriorityBadge';
import { formatTaskDate, formatTaskDateTime, getTaskDuration } from './utils';
import type { TaskCardProps } from './types';

export function TaskCard({
  task,
  onEdit,
  onDelete,
  onExecute,
  onClick,
  className = ''
}: TaskCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  const handleClick = () => {
    onClick?.(task);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(task);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`Are you sure you want to delete "${task.title}"?`)) {
      onDelete?.(task.id);
    }
  };

  const handleExecute = (e: React.MouseEvent) => {
    e.stopPropagation();
    onExecute?.(task.id);
  };

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer ${className}`}
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-gray-900 truncate mb-1">
            {task.title}
          </h3>
          {task.description && (
            <p className="text-sm text-gray-600 line-clamp-2">
              {task.description}
            </p>
          )}
        </div>

        {/* Action buttons */}
        <div className={`flex gap-1 ml-2 transition-opacity ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
          {task.canEdit && (
            <button
              onClick={handleEdit}
              className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
              title="Edit task"
            >
              ✏️
            </button>
          )}
          {task.canExecute && task.status === 'pending' && (
            <button
              onClick={handleExecute}
              className="p-1 text-gray-400 hover:text-green-600 transition-colors"
              title="Execute task"
            >
              ▶️
            </button>
          )}
          {task.canDelete && (
            <button
              onClick={handleDelete}
              className="p-1 text-gray-400 hover:text-red-600 transition-colors"
              title="Delete task"
            >
              🗑️
            </button>
          )}
        </div>
      </div>

      {/* Status and Priority */}
      <div className="flex items-center gap-2 mb-3">
        <TaskStatusBadge status={task.status} size="sm" />
        <TaskPriorityBadge priority={task.priority} size="sm" />
      </div>

      {/* Assignment Info */}
      <div className="space-y-1 mb-3">
        {task.team_name && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="font-medium">Team:</span>
            <span>{task.team_name}</span>
          </div>
        )}
        {task.agent_name && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="font-medium">Agent:</span>
            <span>{task.agent_name}</span>
          </div>
        )}
        {task.milestone_title && (
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="font-medium">Milestone:</span>
            <span>{task.milestone_title}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          <span>Created {formatTaskDate(task.created_at)}</span>
          {task.status === 'completed' && task.completed_at && (
            <span>• Completed {formatTaskDate(task.completed_at)}</span>
          )}
        </div>
        {task.status === 'completed' && task.completed_at && (
          <span className="text-green-600 font-medium">
            Duration: {getTaskDuration(task.created_at, task.completed_at)}
          </span>
        )}
      </div>

      {/* Result */}
      {task.result && (
        <div className="mt-3 p-3 bg-gray-50 rounded-md">
          <div className="text-sm font-medium text-gray-700 mb-1">Result:</div>
          <div className="text-sm text-gray-600 whitespace-pre-wrap">
            {task.result.length > 200 ? `${task.result.substring(0, 200)}...` : task.result}
          </div>
        </div>
      )}
    </div>
  );
}
