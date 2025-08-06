import { Bot, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'

interface Agent {
  id: string
  name: string
  type: string
  status: 'active' | 'idle' | 'error'
  tasks: {
    completed: number
    running: number
    pending: number
  }
  lastActivity: string
}

interface AgentCardProps {
  agent: Agent
  onAssignTask?: (agentId: string) => void
  onViewDetails?: (agentId: string) => void
}

const statusConfig = {
  active: {
    color: 'bg-green-500',
    icon: CheckCircle,
    text: 'Active'
  },
  idle: {
    color: 'bg-yellow-500',
    icon: Clock,
    text: 'Idle'
  },
  error: {
    color: 'bg-red-500',
    icon: AlertCircle,
    text: 'Error'
  }
}

export function AgentCard({ agent, onAssignTask, onViewDetails }: AgentCardProps) {
  const statusInfo = statusConfig[agent.status]
  const StatusIcon = statusInfo.icon

  return (
    <Card className="agent-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Avatar className="w-10 h-10">
              <AvatarFallback className="bg-primary/10">
                <Bot className="w-5 h-5 text-primary" />
              </AvatarFallback>
            </Avatar>
            <div>
              <CardTitle className="text-lg">{agent.name}</CardTitle>
              <Badge variant="secondary" className="text-xs">
                {agent.type}
              </Badge>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${statusInfo.color}`}></div>
            <StatusIcon className="w-4 h-4 text-muted-foreground" />
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {/* Task Statistics */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2 rounded-lg bg-green-50 dark:bg-green-950/20">
              <div className="text-lg font-semibold text-green-600">
                {agent.tasks.completed}
              </div>
              <div className="text-xs text-green-600/70">Completed</div>
            </div>
            <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/20">
              <div className="text-lg font-semibold text-blue-600">
                {agent.tasks.running}
              </div>
              <div className="text-xs text-blue-600/70">Running</div>
            </div>
            <div className="p-2 rounded-lg bg-gray-50 dark:bg-gray-950/20">
              <div className="text-lg font-semibold text-gray-600">
                {agent.tasks.pending}
              </div>
              <div className="text-xs text-gray-600/70">Pending</div>
            </div>
          </div>

          {/* Last Activity */}
          <div className="text-xs text-muted-foreground">
            Last activity: {agent.lastActivity}
          </div>

          {/* Actions */}
          <div className="flex space-x-2">
            <Button
              size="sm"
              className="flex-1"
              onClick={() => onAssignTask?.(agent.id)}
            >
              Assign Task
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => onViewDetails?.(agent.id)}
            >
              View Details
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}