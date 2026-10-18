import React from 'react';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'accent' | 'success' | 'warning' | 'error' | 'outline' | 'seam';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  icon,
  style,
  className = '',
}) => {
  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    borderRadius: 'var(--radius-full, 9999px)',
    fontWeight: 600,
    letterSpacing: '0.02em',
    textTransform: 'uppercase',
  };

  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: { padding: '2px 7px', fontSize: '10px' },
    md: { padding: '3px 9px', fontSize: '11px' },
  };

  const variantStyles: Record<string, React.CSSProperties> = {
    default: {
      backgroundColor: 'var(--bg-quaternary, #1c2433)',
      color: 'var(--text-secondary, #9fa9bc)',
      border: '1px solid var(--border-color, #232c3d)',
    },
    accent: {
      backgroundColor: 'var(--accent-soft, rgba(110, 92, 255, 0.15))',
      color: 'var(--accent-color, #6e5cff)',
      border: '1px solid rgba(110, 92, 255, 0.3)',
    },
    seam: {
      background: 'var(--accent-soft, rgba(110, 92, 255, 0.15))',
      color: '#29d3e6',
      border: '1px solid rgba(41, 211, 230, 0.35)',
    },
    success: {
      backgroundColor: 'var(--success-soft, rgba(52, 211, 153, 0.15))',
      color: 'var(--success-color, #34d399)',
      border: '1px solid rgba(52, 211, 153, 0.3)',
    },
    warning: {
      backgroundColor: 'var(--warning-soft, rgba(245, 166, 35, 0.15))',
      color: 'var(--warning-color, #f5a623)',
      border: '1px solid rgba(245, 166, 35, 0.3)',
    },
    error: {
      backgroundColor: 'var(--error-soft, rgba(243, 105, 127, 0.15))',
      color: 'var(--error-color, #f26b7a)',
      border: '1px solid rgba(243, 105, 127, 0.3)',
    },
    outline: {
      backgroundColor: 'transparent',
      color: 'var(--text-primary, #e7ecf5)',
      border: '1px solid var(--border-strong, #303b50)',
    },
  };

  return (
    <span
      style={{
        ...baseStyle,
        ...sizeStyles[size],
        ...variantStyles[variant],
        ...style,
      }}
      className={className}
    >
      {icon}
      {children}
    </span>
  );
};
