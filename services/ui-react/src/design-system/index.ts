// FuzeAgent Inherited Design System
// Inherits core tokens and primitives from @fuzefront/design-system
// and layers FuzeAgent product-specific primitives on top.

// Core Primitives (from @fuzefront/design-system or local fallback)
export { Button } from './Button';
export { Badge } from './Badge';
export { Card } from './Card';
export { Input } from './Input';
export { StatusPill } from './StatusPill';
export { Avatar } from './Avatar';
export type { AvatarProps } from './Avatar';

// FuzeAgent Specialized Inherited Primitives
export { AgentChatBubble } from './AgentChatBubble';
export type { AgentChatBubbleProps } from './AgentChatBubble';

export { TimeInZoneCard } from './TimeInZoneCard';
export type { TimeInZoneCardProps } from './TimeInZoneCard';

export { StreamingThoughtIndicator } from './StreamingThoughtIndicator';
export type { StreamingThoughtIndicatorProps } from './StreamingThoughtIndicator';

export { SandboxStatusBadge } from './SandboxStatusBadge';
export type { SandboxStatusBadgeProps } from './SandboxStatusBadge';

export { TerminalLogWindow } from './TerminalLogWindow';
export type { TerminalLogWindowProps } from './TerminalLogWindow';

export { usePortalTheme, getPortalTheme } from './usePortalTheme';
export type { PortalTheme } from './usePortalTheme';
