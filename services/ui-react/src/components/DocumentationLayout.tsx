import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  FiBook, 
  FiCode, 
  FiUsers, 
  FiSettings, 
  FiSearch, 
  FiMenu, 
  FiX,
  FiHome,
  FiPlay,
  FiMonitor,
  FiZap
} from 'react-icons/fi'

interface DocsNavItem {
  id: string
  title: string
  path: string
  icon: React.ComponentType<{ className?: string }>
  children?: DocsNavItem[]
}

const navigationItems: DocsNavItem[] = [
  {
    id: 'overview',
    title: 'Overview',
    path: '/docs',
    icon: FiHome
  },
  {
    id: 'getting-started',
    title: 'Getting Started',
    path: '/docs/getting-started',
    icon: FiPlay
  },
  {
    id: 'core-concepts',
    title: 'Core Concepts',
    path: '/docs/core-concepts',
    icon: FiBook,
    children: [
      {
        id: 'organizations-teams',
        title: 'Organizations & Teams',
        path: '/docs/organizations-teams',
        icon: FiUsers
      },
      {
        id: 'creating-agents',
        title: 'Creating Agents',
        path: '/docs/creating-agents',
        icon: FiUsers
      },
      {
        id: 'task-management',
        title: 'Task Management',
        path: '/docs/task-management',
        icon: FiSettings
      }
    ]
  },
  {
    id: 'api-reference',
    title: 'API Reference',
    path: '/docs/api-reference',
    icon: FiCode
  },
  {
    id: 'examples',
    title: 'Examples',
    path: '/docs/examples',
    icon: FiZap,
    children: [
      {
        id: 'quick-start',
        title: 'Quick Start Example',
        path: '/docs/examples/quick-start',
        icon: FiPlay
      },
      {
        id: 'advanced-workflows',
        title: 'Advanced Workflows',
        path: '/docs/examples/advanced-workflows',
        icon: FiSettings
      }
    ]
  },
  {
    id: 'monitoring',
    title: 'Monitoring',
    path: '/docs/monitoring',
    icon: FiMonitor
  }
]

interface DocumentationLayoutProps {
  children: React.ReactNode
  searchQuery?: string
  onSearchChange?: (query: string) => void
}

export default function DocumentationLayout({ 
  children, 
  searchQuery = '', 
  onSearchChange 
}: DocumentationLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const isActiveRoute = (path: string) => {
    if (path === '/docs' && location.pathname === '/docs') return true
    if (path !== '/docs' && location.pathname.startsWith(path)) return true
    return false
  }

  const renderNavItem = (item: DocsNavItem, level = 0) => {
    const Icon = item.icon
    const isActive = isActiveRoute(item.path)
    const hasChildren = item.children && item.children.length > 0
    const isExpanded = hasChildren && item.children!.some(child => isActiveRoute(child.path))

    return (
      <div key={item.id}>
        <Link
          to={item.path}
          className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
            level > 0 ? 'ml-6' : ''
          } ${
            isActive
              ? 'bg-blue-100 text-blue-700 border-r-2 border-blue-700'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
          }`}
          onClick={() => setSidebarOpen(false)}
        >
          <Icon className="w-4 h-4" />
          {item.title}
        </Link>
        
        {hasChildren && (isExpanded || isActive) && (
          <div className="mt-1 space-y-1">
            {item.children!.map(child => renderNavItem(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 rounded-md bg-white shadow-md text-gray-600 hover:text-gray-900"
        >
          {sidebarOpen ? <FiX className="w-5 h-5" /> : <FiMenu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-40 w-80 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <Link to="/" className="flex items-center gap-2">
              <FiUsers className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">FuzeAgent</h1>
                <p className="text-sm text-gray-500">Documentation</p>
              </div>
            </Link>
          </div>

          {/* Search */}
          <div className="p-4 border-b border-gray-200">
            <div className="relative">
              <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search documentation..."
                value={searchQuery}
                onChange={(e) => onSearchChange?.(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4">
            <div className="space-y-2">
              {navigationItems.map(item => renderNavItem(item))}
            </div>
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <div className="text-xs text-gray-500 space-y-1">
              <p>FuzeAgent v1.0.0</p>
              <p>
                <a href="https://github.com/yourusername/fuzeagent" className="text-blue-600 hover:text-blue-800">
                  GitHub
                </a>
                {' • '}
                <a href="/support" className="text-blue-600 hover:text-blue-800">
                  Support
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-gray-600 bg-opacity-50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="lg:ml-80">
        <main className="max-w-4xl mx-auto px-4 py-8 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  )
}