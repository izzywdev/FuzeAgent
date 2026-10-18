import React from 'react';

export interface SandboxStatusBadgeProps {
  status: 'running' | 'provisioning' | 'booting' | 'executing' | 'terminated' | 'error' | string;
  label?: string;
}

export const SandboxStatusBadge: React.FC<SandboxStatusBadgeProps> = ({
  status,
  label,
}) => {
  const norm = status.toLowerCase();
  
  let bg = 'rgba(104, 117, 141, 0.15)';
  let border = 'rgba(104, 117, 141, 0.3)';
  let text = 'var(--text-secondary, #9fa9bc)';
  let dotColor = '#68758d';
  let pulse = false;

  if (norm === 'running' || norm === 'online' || norm === 'healthy') {
    bg = 'rgba(16, 185, 129, 0.15)';
    border = 'rgba(16, 185, 129, 0.35)';
    text = '#10b981';
    dotColor = '#10b981';
  } else if (norm === 'executing' || norm === 'processing') {
    bg = 'rgba(110, 92, 255, 0.2)';
    border = 'rgba(110, 92, 255, 0.4)';
    text = '#a78bfa';
    dotColor = '#6e5cff';
    pulse = true;
  } else if (norm === 'provisioning' || norm === 'booting' || norm === 'pending') {
    bg = 'rgba(245, 158, 11, 0.15)';
    border = 'rgba(245, 158, 11, 0.35)';
    text = '#f59e0b';
    dotColor = '#f59e0b';
    pulse = true;
  } else if (norm === 'error' || norm === 'failed') {
    bg = 'rgba(239, 68, 68, 0.15)';
    border = 'rgba(239, 68, 68, 0.35)';
    text = '#ef4444';
    dotColor = '#ef4444';
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-medium border shadow-sm"
      style={{
        backgroundColor: bg,
        borderColor: border,
        color: text,
      }}
    >
      <span 
        className={`w-1.5 h-1.5 rounded-full ${pulse ? 'animate-ping' : ''}`}
        style={{ backgroundColor: dotColor }}
      />
      <span>{label || status}</span>
    </span>
  );
};
