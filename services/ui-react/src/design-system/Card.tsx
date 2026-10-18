import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  seamAccent?: boolean;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  seamAccent = false,
  hoverable = false,
  style,
  className = '',
  ...props
}) => {
  return (
    <div
      style={{
        backgroundColor: 'var(--bg-tertiary, #141a26)',
        border: '1px solid var(--border-color, #232c3d)',
        borderRadius: 'var(--radius-lg, 8px)',
        position: 'relative',
        overflow: 'hidden',
        transition: hoverable ? 'all 0.2s ease' : 'none',
        ...style,
      }}
      className={className}
      {...props}
    >
      {seamAccent && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '2px',
            background: 'var(--seam, linear-gradient(90deg, #6e5cff 0%, #29d3e6 100%))',
          }}
        />
      )}
      {children}
    </div>
  );
};
