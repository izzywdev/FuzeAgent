import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'seam';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  className = '',
  disabled,
  style,
  ...props
}) => {
  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    fontWeight: 500,
    borderRadius: 'var(--radius-md, 6px)',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled || loading ? 0.6 : 1,
    transition: 'all 0.15s ease',
    border: '1px solid transparent',
    fontFamily: 'inherit',
    outline: 'none',
  };

  const sizeStyles: Record<string, React.CSSProperties> = {
    sm: { padding: '4px 10px', fontSize: '12px' },
    md: { padding: '7px 14px', fontSize: '13px' },
    lg: { padding: '10px 18px', fontSize: '15px' },
  };

  const variantStyles: Record<string, React.CSSProperties> = {
    primary: {
      backgroundColor: 'var(--accent-color, #6e5cff)',
      color: '#ffffff',
      borderColor: 'transparent',
    },
    seam: {
      background: 'var(--seam, linear-gradient(90deg, #6e5cff 0%, #29d3e6 100%))',
      color: '#ffffff',
      borderColor: 'transparent',
      boxShadow: '0 2px 8px rgba(110, 92, 255, 0.35)',
    },
    secondary: {
      backgroundColor: 'var(--bg-quaternary, #1c2433)',
      color: 'var(--text-primary, #e7ecf5)',
      borderColor: 'var(--border-color, #232c3d)',
    },
    outline: {
      backgroundColor: 'transparent',
      color: 'var(--text-primary, #e7ecf5)',
      borderColor: 'var(--border-strong, #303b50)',
    },
    ghost: {
      backgroundColor: 'transparent',
      color: 'var(--text-secondary, #9fa9bc)',
      borderColor: 'transparent',
    },
    danger: {
      backgroundColor: 'var(--error-soft, rgba(243, 105, 127, 0.15))',
      color: 'var(--error-color, #f26b7a)',
      borderColor: 'rgba(243, 105, 127, 0.3)',
    },
  };

  return (
    <button
      style={{
        ...baseStyle,
        ...sizeStyles[size],
        ...variantStyles[variant],
        ...style,
      }}
      disabled={disabled || loading}
      className={className}
      {...props}
    >
      {loading ? (
        <span
          style={{
            width: '12px',
            height: '12px',
            border: '2px solid currentColor',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 0.6s linear infinite',
          }}
        />
      ) : (
        icon
      )}
      {children}
    </button>
  );
};
