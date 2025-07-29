import React, { useMemo } from 'react'
import { FiUser, FiActivity, FiClock, FiCheckCircle } from 'react-icons/fi'
import type { Agent, Task } from '../types'

interface StatsCardsProps {
  agents: Agent[]
  tasks: Task[]
}

const StatsCards: React.FC<StatsCardsProps> = React.memo(({ agents, tasks }) => {
  // Memoize expensive calculations
  const stats = useMemo(() => {
    const activeAgents = agents.filter(a => a.status === 'active').length
    const pendingTasks = tasks.filter(t => t.status === 'pending').length
    const completedTasks = tasks.filter(t => t.status === 'completed').length

    return [
      {
        title: 'Total Agents',
        value: agents.length,
        icon: FiUser,
        color: 'text-blue-600',
        bgColor: 'bg-blue-100'
      },
      {
        title: 'Active Agents',
        value: activeAgents,
        icon: FiActivity,
        color: 'text-green-600',
        bgColor: 'bg-green-100'
      },
      {
        title: 'Pending Tasks',
        value: pendingTasks,
        icon: FiClock,
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-100'
      },
      {
        title: 'Completed Tasks',
        value: completedTasks,
        icon: FiCheckCircle,
        color: 'text-purple-600',
        bgColor: 'bg-purple-100'
      }
    ]
  }, [agents, tasks])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {stats.map((stat, index) => {
        const Icon = stat.icon
        return (
          <div key={index} className="bg-white p-6 rounded-lg shadow fade-in">
            <div className="flex items-center">
              <div className={`p-3 rounded-full ${stat.bgColor} mr-4`}>
                <Icon className={`w-6 h-6 ${stat.color}`} />
              </div>
              <div>
                <p className="text-sm text-gray-600">{stat.title}</p>
                <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
})

export default StatsCards