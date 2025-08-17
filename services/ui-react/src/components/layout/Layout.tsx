/**
 * Layout - Main application layout wrapper component
 * 
 * This component provides the consistent structure for all pages including:
 * - Sidebar navigation
 * - Header with title and subtitle
 * - Main content area with proper spacing and scrolling
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import { type ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

/**
 * Props for the Layout component
 */
interface LayoutProps {
  /** The content to render in the main area */
  children: ReactNode
  /** Optional page title to display in the header */
  title?: string
  /** Optional page subtitle to display in the header */
  subtitle?: string
}

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * Main layout component that wraps all application pages
 * 
 * Provides consistent navigation, header, and content structure across
 * the entire application for a cohesive user experience.
 * 
 * @param props - The component props
 * @returns JSX.Element - The rendered layout
 */
export function Layout({ 
  children, 
  title, 
  subtitle 
}: LayoutProps): JSX.Element {
  return (
    <div className="flex h-screen bg-background">
      {/* Left Sidebar Navigation */}
      <Sidebar />
      
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <Header title={title} subtitle={subtitle} />
        
        {/* Main Content with Scrolling */}
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}