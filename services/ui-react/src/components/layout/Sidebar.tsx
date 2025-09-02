/**
 * Sidebar - Left navigation sidebar component
 * 
 * This component provides the main navigation structure for the application including:
 * - Application branding and logo
 * - Primary navigation links with icons
 * - Badge indicators for notifications and counts
 * - Responsive design considerations
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import { NavLink } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Users, 
  Bot, 
  GitBranch,
  Settings,
  BookOpen,
  Activity,
  BarChart3,
  Zap
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { OrganizationSwitcher } from './OrganizationSwitcher'

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

/**
 * Props for the Sidebar component
 */
interface SidebarProps {
  /** Optional CSS class for custom styling */
  className?: string
}

/**
 * Navigation item structure
 */
interface NavigationItem {
  /** Display name of the navigation item */
  name: string
  /** URL path for the navigation item */
  href: string
  /** Icon component to display */
  icon: React.ComponentType<{ className?: string }>
  /** Whether this item is currently active */
  current?: boolean
  /** Optional badge to display (count or label) */
  badge?: string
}

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * Application branding information
 */
const APP_BRAND = {
  name: 'FuzeAgent',
  tagline: 'AI Team Manager',
  logo: Bot
} as const

/**
 * Main navigation items
 */
const NAVIGATION_ITEMS: NavigationItem[] = [
  {
    name: 'Dashboard',
    href: '/',
    icon: LayoutDashboard,
    current: true,
  },
  {
    name: 'Agents',
    href: '/agents',
    icon: Bot,
    badge: '12',
  },
  {
    name: 'Teams',
    href: '/teams',
    icon: Users,
    badge: '4',
  },
  {
    name: 'Organization Chart',
    href: '/organization-chart',
    icon: GitBranch,
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
    badge: 'New',
  },
  {
    name: 'Activity Feed',
    href: '/activity',
    icon: Activity,
  },
  {
    name: 'API Playground',
    href: '/playground',
    icon: Zap,
  },
  {
    name: 'Documentation',
    href: '/docs',
    icon: BookOpen,
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
]

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * Sidebar navigation component
 * 
 * Provides consistent navigation structure and branding across
 * all application pages with proper active state management.
 * 
 * @param props - The component props
 * @returns JSX.Element - The rendered sidebar
 */
export function Sidebar({ className }: SidebarProps): JSX.Element {
  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  /**
   * Render a navigation item with proper styling and badges
   */
  const renderNavigationItem = (item: NavigationItem): JSX.Element => {
    const Icon = item.icon
    
    return (
      <NavLink
        key={item.name}
        to={item.href}
        className={({ isActive }) =>
          cn(
            'flex items-center justify-between px-3 py-2 text-sm font-medium rounded-lg transition-colors hover:bg-accent hover:text-accent-foreground',
            isActive
              ? 'bg-accent text-accent-foreground'
              : 'text-muted-foreground hover:text-foreground'
          )
        }
        aria-label={`Navigate to ${item.name}`}
      >
        <div className="flex items-center space-x-3">
          <Icon className="w-5 h-5" />
          <span>{item.name}</span>
        </div>
        
        {/* Badge indicator */}
        {item.badge && (
          <Badge 
            variant={item.badge === 'New' ? 'default' : 'secondary'}
            className="ml-auto"
          >
            {item.badge}
          </Badge>
        )}
      </NavLink>
    )
  }

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className={cn("flex flex-col w-64 bg-card border-r border-border", className)}>
      {/* Application Logo and Branding */}
      <div className="flex items-center px-6 py-4 border-b border-border">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <APP_BRAND.logo className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">{APP_BRAND.name}</h1>
            <p className="text-xs text-muted-foreground">{APP_BRAND.tagline}</p>
          </div>
        </div>
      </div>

      {/* Organization Switcher */}
      <div className="px-4 py-3 border-b border-border">
        <OrganizationSwitcher />
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 px-4 py-4 space-y-2" role="navigation" aria-label="Main navigation">
        {NAVIGATION_ITEMS.map(renderNavigationItem)}
      </nav>

      {/* Footer Section (Optional) */}
      <div className="p-4 border-t border-border">
        <div className="text-xs text-muted-foreground text-center">
          <p>Version 1.0.0</p>
          <p className="mt-1">© 2025 FuzeAgent</p>
        </div>
      </div>
    </div>
  )
}