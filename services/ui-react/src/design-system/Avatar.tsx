import React from 'react';

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  name?: string;
  fallbackEmoji?: string;
  fallback?: React.ReactNode;
  src?: string;
  alt?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'seam' | 'default' | 'subtle';
  status?: 'online' | 'busy' | 'offline' | string;
  isOnline?: boolean;
}

export const Avatar: React.FC<AvatarProps> = ({
  name,
  fallbackEmoji,
  fallback,
  src,
  alt = 'Avatar',
  size = 'md',
  variant = 'seam',
  status,
  isOnline,
  className = '',
  style,
  ...props
}) => {
  const sizeMap = {
    xs: 'w-6 h-6 text-[10px]',
    sm: 'w-8 h-8 text-xs',
    md: 'w-9 h-9 text-sm',
    lg: 'w-11 h-11 text-base',
    xl: 'w-14 h-14 text-lg',
  };

  const variantStyle: React.CSSProperties = {
    background: variant === 'seam' 
      ? 'var(--seam, linear-gradient(90deg, #6e5cff, #29d3e6))' 
      : 'var(--bg-quaternary, #1c2433)',
    color: '#ffffff',
    border: '1px solid var(--border-color, #232c3d)',
    ...style,
  };

  const effectiveStatus = status ?? (isOnline ? 'online' : undefined);

  const displayInitial = fallbackEmoji || fallback || (name ? name.substring(0, 2).toUpperCase() : 'FA');

  return (
    <div
      className={`relative inline-flex items-center justify-center font-bold font-mono rounded-xl overflow-hidden shrink-0 shadow-sm ${sizeMap[size]} ${className}`}
      style={variantStyle}
      title={name}
      {...props}
    >
      {src ? (
        <img src={src} alt={alt || name} className="w-full h-full object-cover" />
      ) : (
        <span>{displayInitial}</span>
      )}
      {effectiveStatus && (
        <span 
          className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-[var(--bg-secondary,#0b0e15)] ${
            effectiveStatus === 'online' 
              ? 'bg-emerald-400' 
              : effectiveStatus === 'busy' 
                ? 'bg-amber-400' 
                : 'bg-slate-500'
          }`}
        />
      )}
    </div>
  );
};
