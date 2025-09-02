import React from 'react';
import { getTaskStatusConfig } from './utils';
import type { TaskStatus } from './types';

interface TaskStatusBadgeProps {
  status: TaskStatus;
  className?: string;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function TaskStatusBadge({
  status,
  className = '',
  showIcon = true,
  size = 'md'
}: TaskStatusBadgeProps) {
  const config = getTaskStatusConfig(status);

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
      {showIcon && <span>{config.icon}</span>}
      <span>{config.label}</span>
    </span>
  );
}
