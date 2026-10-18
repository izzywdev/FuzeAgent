import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  icon,
  style,
  className = '',
  ...props
}) => {
  return (
    <div style={{ position: 'relative', display: 'flex', alignItems: 'center', width: '100%' }}>
      {icon && (
        <span
          style={{
            position: 'absolute',
            left: '10px',
            color: 'var(--text-tertiary, #66718a)',
            pointerEvents: 'none',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {icon}
        </span>
      )}
      <input
        style={{
          width: '100%',
          backgroundColor: 'var(--bg-quaternary, #1c2433)',
          border: '1px solid var(--border-color, #232c3d)',
          borderRadius: 'var(--radius-md, 6px)',
          color: 'var(--text-primary, #e7ecf5)',
          padding: icon ? '8px 12px 8px 34px' : '8px 12px',
          fontSize: '13px',
          outline: 'none',
          boxSizing: 'border-box',
          fontFamily: 'inherit',
          ...style,
        }}
        className={className}
        {...props}
      />
    </div>
  );
};

export interface AvatarProps {
  name: string;
  avatarUrl?: string;
  size?: 'sm' | 'md' | 'lg';
  status?: 'online' | 'offline' | 'busy';
  fallbackEmoji?: string;
}

export const Avatar: React.FC<AvatarProps> = ({
  name,
  avatarUrl,
  size = 'md',
  status,
  fallbackEmoji,
}) => {
  const sizeMap = {
    sm: { size: 24, fontSize: 11 },
    md: { size: 32, fontSize: 13 },
    lg: { size: 42, fontSize: 18 },
  };

  const { size: px, fontSize } = sizeMap[size];

  const getInitials = (n: string) => {
    return n
      .split(' ')
      .map(part => part[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();
  };

  return (
    <div style={{ position: 'relative', display: 'inline-flex' }}>
      <div
        style={{
          width: `${px}px`,
          height: `${px}px`,
          borderRadius: '50%',
          backgroundColor: 'var(--bg-quaternary, #1c2433)',
          border: '1px solid var(--border-color, #232c3d)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 600,
          color: 'var(--text-primary, #e7ecf5)',
          fontSize: `${fontSize}px`,
          overflow: 'hidden',
        }}
      >
        {avatarUrl ? (
          <img src={avatarUrl} alt={name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : fallbackEmoji ? (
          fallbackEmoji
        ) : (
          getInitials(name)
        )}
      </div>
      {status && (
        <span
          style={{
            position: 'absolute',
            bottom: 0,
            right: 0,
            width: size === 'sm' ? '6px' : '8px',
            height: size === 'sm' ? '6px' : '8px',
            borderRadius: '50%',
            border: '1.5px solid var(--bg-tertiary, #141a26)',
            backgroundColor:
              status === 'online'
                ? 'var(--success-color, #34d399)'
                : status === 'busy'
                ? 'var(--warning-color, #f5a623)'
                : 'var(--text-tertiary, #66718a)',
          }}
        />
      )}
    </div>
  );
};
