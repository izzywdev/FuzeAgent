import React from 'react';

export interface StatusPillProps {
  status: 'online' | 'idle' | 'running' | 'executing' | 'failed' | 'error' | 'pending' | 'draft';
  label?: string;
  pulse?: boolean;
  style?: React.CSSProperties;
}

export const StatusPill: React.FC<StatusPillProps> = ({
  status,
  label,
  pulse = true,
  style,
}) => {
  const statusConfig: Record<string, { color: string; bg: string; text: string }> = {
    online: { color: 'var(--success-color, #34d399)', bg: 'var(--success-soft, rgba(52, 211, 153, 0.12))', text: label || 'Online' },
    running: { color: 'var(--accent-2, #29d3e6)', bg: 'rgba(41, 211, 230, 0.12)', text: label || 'Running' },
    executing: { color: 'var(--accent-color, #6e5cff)', bg: 'var(--accent-soft, rgba(110, 92, 255, 0.14))', text: label || 'Executing' },
    idle: { color: 'var(--text-tertiary, #66718a)', bg: 'rgba(102, 113, 138, 0.12)', text: label || 'Idle' },
    pending: { color: 'var(--warning-color, #f5a623)', bg: 'var(--warning-soft, rgba(245, 166, 35, 0.12))', text: label || 'Pending' },
    draft: { color: 'var(--warning-color, #f5a623)', bg: 'var(--warning-soft, rgba(245, 166, 35, 0.12))', text: label || 'Draft' },
    failed: { color: 'var(--error-color, #f26b7a)', bg: 'var(--error-soft, rgba(243, 105, 127, 0.12))', text: label || 'Failed' },
    error: { color: 'var(--error-color, #f26b7a)', bg: 'var(--error-soft, rgba(243, 105, 127, 0.12))', text: label || 'Error' },
  };

  const cfg = statusConfig[status] || statusConfig.idle;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '3px 9px',
        borderRadius: 'var(--radius-full, 9999px)',
        fontSize: '11px',
        fontWeight: 600,
        backgroundColor: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.color}33`,
        ...style,
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: cfg.color,
          boxShadow: pulse ? `0 0 6px ${cfg.color}` : 'none',
        }}
      />
      {cfg.text}
    </span>
  );
};
