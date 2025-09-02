import React from 'react';
import { getTaskPriorityConfig } from './utils';
import type { TaskPriority } from './types';

interface TaskPriorityBadgeProps {
  priority: TaskPriority;
  className?: string;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function TaskPriorityBadge({
  priority,
  className = '',
  showLabel = true,
  size = 'md'
}: TaskPriorityBadgeProps) {
  const config = getTaskPriorityConfig(priority);

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base'
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${sizeClasses[size]} ${className}`}
      style={{
        color: config.color,
        backgroundColor: config.bgColor
      }}
    >
      <span>⚡</span>
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}
