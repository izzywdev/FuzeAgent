import { useState } from 'react'
import { Bot, Users, Activity, TrendingUp, Plus } from 'lucide-react'
import { Layout } from '@/components/layout/Layout'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { AgentCard } from '@/components/dashboard/AgentCard'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

// Mock data - replace with real API calls
const mockMetrics = {
  totalAgents: 12,
  activeAgents: 8,
  tasksCompleted: 145,
  averageResponseTime: '2.3s'
}

const mockAgents = [
  {
    id: '1',
    name: 'IzzyAI CEO',
    type: 'Executive',
    status: 'active' as const,
    tasks: { completed: 23, running: 2, pending: 1 },
    lastActivity: '2 minutes ago'
  },
  {
    id: '2',
    name: 'CTO Agent',
    type: 'Executive',
    status: 'active' as const,
    tasks: { completed: 18, running: 1, pending: 3 },
    lastActivity: '5 minutes ago'
  },
  {
    id: '3',
    name: 'Frontend Dev 1',
    type: 'Developer',
    status: 'idle' as const,
    tasks: { completed: 42, running: 0, pending: 2 },
    lastActivity: '1 hour ago'
  }
]

const recentActivity = [
  {
    id: '1',
    type: 'task_completed',
    agent: 'IzzyAI CEO',
    message: 'Completed strategic planning task',
    time: '2 minutes ago',
    status: 'success'
  },
  {
    id: '2',
    type: 'agent_created',
    agent: 'System',
    message: 'New React Developer agent deployed',
    time: '15 minutes ago',
    status: 'info'
  },
  {
    id: '3',
    type: 'task_failed',
    agent: 'Backend Dev 2',
    message: 'Database migration task failed',
    time: '1 hour ago',
    status: 'error'
  }
]

export function DashboardPage() {
  const [agents] = useState(mockAgents)

  const handleAssignTask = (agentId: string) => {
    console.log('Assign task to agent:', agentId)
  }

  const handleViewDetails = (agentId: string) => {
    console.log('View agent details:', agentId)
  }

  return (
    <Layout 
      title="Dashboard" 
      subtitle="Manage your AI agents and monitor team performance"
    >
      <div className="space-y-6">
        {/* Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            title="Total Agents"
            value={mockMetrics.totalAgents}
            change={{ value: '+2', type: 'increase' }}
            icon={<Bot className="w-6 h-6 text-primary" />}
          />
          <MetricCard
            title="Active Agents"
            value={mockMetrics.activeAgents}
            change={{ value: '+1', type: 'increase' }}
            icon={<Activity className="w-6 h-6 text-primary" />}
          />
          <MetricCard
            title="Tasks Completed"
            value={mockMetrics.tasksCompleted}
            change={{ value: '+12%', type: 'increase' }}
            icon={<TrendingUp className="w-6 h-6 text-primary" />}
          />
          <MetricCard
            title="Avg Response Time"
            value={mockMetrics.averageResponseTime}
            change={{ value: '-0.5s', type: 'increase' }}
            icon={<Users className="w-6 h-6 text-primary" />}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Agents */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-foreground">Active Agents</h2>
              <Button size="sm">
                <Plus className="w-4 h-4 mr-2" />
                Create Agent
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {agents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  onAssignTask={handleAssignTask}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div>
            <h2 className="text-xl font-semibold text-foreground mb-4">Recent Activity</h2>
            <Card>
              <CardHeader>
                <CardTitle>Activity Feed</CardTitle>
                <CardDescription>Latest updates from your AI team</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentActivity.map((activity) => (
                    <div key={activity.id} className="flex items-start space-x-3 p-3 rounded-lg hover:bg-accent/50 transition-colors">
                      <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                        activity.status === 'success' ? 'bg-green-500' :
                        activity.status === 'error' ? 'bg-red-500' :
                        'bg-blue-500'
                      }`}></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-foreground">
                            {activity.agent}
                          </p>
                          <Badge variant="outline" className="text-xs">
                            {activity.time}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {activity.message}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks and shortcuts</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
                <Bot className="w-8 h-8" />
                <span>Deploy New Agent</span>
              </Button>
              <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
                <Users className="w-8 h-8" />
                <span>Create Team</span>
              </Button>
              <Button variant="outline" className="h-auto p-4 flex flex-col items-center space-y-2">
                <Activity className="w-8 h-8" />
                <span>View Analytics</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  )
}