/**
 * AgentCard - Displays information about a single AI agent
 * 
 * This component shows agent details including name, type, status, and task statistics.
 * It's used in the dashboard to display active agents and their current state.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

/**
 * Represents an AI agent in the system
 */
interface Agent {
  /** Unique identifier for the agent */
  id: string
  /** Display name of the agent */
  name: string
  /** Type/category of the agent (e.g., "React Developer", "Backend Dev") */
  type: string
  /** Current status of the agent */
  status: 'active' | 'idle' | 'error' | 'offline'
  /** Task statistics for the agent */
  tasks: {
    /** Number of completed tasks */
    completed: number
    /** Number of currently running tasks */
    running: number
    /** Number of pending tasks */
    pending: number
  }
  /** Last activity timestamp */
  lastActivity: string
}

/**
 * Props for the AgentCard component
 */
interface AgentCardProps {
  /** The agent data to display */
  agent: Agent
  /** Optional callback when the card is clicked */
  onClick?: (agentId: string) => void
  /** Optional CSS class for custom styling */
  className?: string
}

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * AgentCard component for displaying agent information
 * 
 * @param props - The component props
 * @returns JSX.Element - The rendered agent card
 */
export function AgentCard({
  agent,
  onClick,
  className = ''
}: AgentCardProps): JSX.Element {
  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  /**
   * Get the appropriate status color class
   */
  const getStatusColorClass = (): string => {
    switch (agent.status) {
      case 'active':
        return 'bg-green-500'
      case 'idle':
        return 'bg-yellow-500'
      case 'error':
        return 'bg-red-500'
      case 'offline':
        return 'bg-gray-500'
      default:
        return 'bg-gray-500'
    }
  }

  /**
   * Get the appropriate status text color class
   */
  const getStatusTextColorClass = (): string => {
    switch (agent.status) {
      case 'active':
        return 'text-green-700'
      case 'idle':
        return 'text-yellow-700'
      case 'error':
        return 'text-red-700'
      case 'offline':
        return 'text-gray-700'
      default:
        return 'text-gray-700'
    }
  }

  /**
   * Get the appropriate status icon
   */
  const getStatusIcon = (): string => {
    switch (agent.status) {
      case 'active':
        return '🤖'
      case 'idle':
        return '😴'
      case 'error':
        return '⚠️'
      case 'offline':
        return '💤'
      default:
        return '🤖'
    }
  }

  /**
   * Handle card click event
   */
  const handleCardClick = (): void => {
    if (onClick) {
      onClick(agent.id)
    }
  }

  /**
   * Format the last activity time
   */
  const formatLastActivity = (): string => {
    try {
      const date = new Date(agent.lastActivity)
      const now = new Date()
      const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))
      
      if (diffInMinutes < 1) return 'Just now'
      if (diffInMinutes < 60) return `${diffInMinutes}m ago`
      if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`
      return `${Math.floor(diffInMinutes / 1440)}d ago`
    } catch {
      return 'Unknown'
    }
  }

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div 
      className={`bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-200 cursor-pointer ${className}`}
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          handleCardClick()
        }
      }}
    >
      {/* Header Section */}
      <div className="flex items-center justify-between mb-3">
        {/* Agent Info */}
        <div className="flex items-center">
          <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mr-3">
            <span className="text-xl">{getStatusIcon()}</span>
          </div>
          <div>
            <h4 className="font-medium text-gray-900 text-sm">{agent.name}</h4>
            <p className="text-xs text-gray-600">{agent.type}</p>
          </div>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center">
          <div className={`w-2 h-2 rounded-full mr-2 ${getStatusColorClass()}`}></div>
          <span className={`text-xs font-medium ${getStatusTextColorClass()} capitalize`}>
            {agent.status}
          </span>
        </div>
      </div>

      {/* Task Statistics */}
      <div className="grid grid-cols-3 gap-2 text-center mb-3">
        <div className="bg-green-50 rounded p-2">
          <div className="text-sm font-semibold text-green-600">{agent.tasks.completed}</div>
          <div className="text-xs text-green-600">Completed</div>
        </div>
        <div className="bg-blue-50 rounded p-2">
          <div className="text-sm font-semibold text-blue-600">{agent.tasks.running}</div>
          <div className="text-xs text-blue-600">Running</div>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <div className="text-sm font-semibold text-gray-600">{agent.tasks.pending}</div>
          <div className="text-xs text-gray-600">Pending</div>
        </div>
      </div>

      {/* Footer Section */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>Last activity: {formatLastActivity()}</span>
        <span className="text-blue-600 hover:text-blue-700">View details →</span>
      </div>
    </div>
  )
}