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

interface SidebarProps {
  className?: string
}

const navigation = [
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

export function Sidebar({ className }: SidebarProps) {
  return (
    <div className={cn("flex flex-col w-64 bg-card border-r border-border", className)}>
      {/* Logo */}
      <div className="flex items-center px-6 py-4 border-b border-border">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Bot className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">FuzeAgent</h1>
            <p className="text-xs text-muted-foreground">AI Team Manager</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 space-y-2">
        {navigation.map((item) => (
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
          >
            <div className="flex items-center space-x-3">
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <span>{item.name}</span>
            </div>
            {item.badge && (
              <Badge variant="secondary" className="ml-auto">
                {item.badge}
              </Badge>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center space-x-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
            <span className="text-sm font-medium text-primary">AI</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground">IzzyAI</p>
            <p className="text-xs text-muted-foreground">CEO Agent</p>
          </div>
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
        </div>
      </div>
    </div>
  )
}