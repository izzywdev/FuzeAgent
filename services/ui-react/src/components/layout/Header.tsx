/**
 * Header - Top navigation and information bar component
 * 
 * This component displays the page title, subtitle, and provides access to:
 * - Global search functionality
 * - Notification center
 * - User settings and profile
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import { Bell, Search, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

/**
 * Props for the Header component
 */
interface HeaderProps {
  /** The main page title to display */
  title?: string
  /** Optional subtitle/description for the page */
  subtitle?: string
}

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * Default values for header props
 */
const DEFAULT_HEADER_PROPS = {
  title: "Dashboard",
  subtitle: "Manage your AI agents and teams"
} as const

/**
 * User information (in a real app, this would come from context/auth)
 */
const CURRENT_USER = {
  name: "Admin User",
  email: "admin@fuzeagent.com",
  avatar: "AU" // Avatar initials
} as const

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * Header component for the main application layout
 * 
 * Provides consistent header information and navigation controls
 * across all application pages.
 * 
 * @param props - The component props
 * @returns JSX.Element - The rendered header
 */
export function Header({ 
  title = DEFAULT_HEADER_PROPS.title, 
  subtitle = DEFAULT_HEADER_PROPS.subtitle 
}: HeaderProps): JSX.Element {
  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  /**
   * Handle search input changes
   */
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const searchTerm = event.target.value
    // TODO: Implement global search functionality
    console.log('Search term:', searchTerm)
  }

  /**
   * Handle notification button click
   */
  const handleNotificationsClick = (): void => {
    // TODO: Implement notification center
    console.log('Notifications clicked')
  }

  /**
   * Handle settings button click
   */
  const handleSettingsClick = (): void => {
    // TODO: Navigate to settings page
    console.log('Settings clicked')
  }

  /**
   * Handle user profile click
   */
  const handleUserProfileClick = (): void => {
    // TODO: Navigate to user profile page
    console.log('User profile clicked')
  }

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <header className="border-b border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/50">
      <div className="flex items-center justify-between px-6 py-4">
        {/* Page Title and Subtitle */}
        <div>
          <h1 className="text-2xl font-bold text-foreground">{title}</h1>
          {subtitle && (
            <p className="text-muted-foreground">{subtitle}</p>
          )}
        </div>

        {/* Right Side Controls */}
        <div className="flex items-center space-x-4">
          {/* Global Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search agents, teams..."
              className="pl-10 pr-4 py-2 w-64 text-sm bg-background border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
              onChange={handleSearchChange}
              aria-label="Search agents, teams, and other content"
            />
          </div>

          {/* Notifications */}
          <Button 
            variant="ghost" 
            size="icon" 
            className="relative"
            onClick={handleNotificationsClick}
            aria-label="View notifications"
          >
            <Bell className="w-5 h-5" />
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 w-5 h-5 rounded-full p-0 flex items-center justify-center text-xs"
              aria-label="3 unread notifications"
            >
              3
            </Badge>
          </Button>

          {/* Settings */}
          <Button 
            variant="ghost" 
            size="icon"
            onClick={handleSettingsClick}
            aria-label="Open settings"
          >
            <Settings className="w-5 h-5" />
          </Button>

          {/* User Profile */}
          <div className="flex items-center space-x-3">
            <Avatar 
              className="cursor-pointer hover:opacity-80 transition-opacity"
              onClick={handleUserProfileClick}
            >
              <AvatarFallback className="bg-primary/10 text-primary">
                {CURRENT_USER.avatar}
              </AvatarFallback>
            </Avatar>
            <div className="hidden md:block">
              <p className="text-sm font-medium text-foreground">{CURRENT_USER.name}</p>
              <p className="text-xs text-muted-foreground">{CURRENT_USER.email}</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}