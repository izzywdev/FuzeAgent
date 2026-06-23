import React, { useMemo, useCallback } from 'react'
import { FiClock, FiCheckCircle, FiAlertCircle, FiUser } from 'react-icons/fi'
import type { Task, Agent } from '../types'

interface TasksViewProps {
  tasks: Task[]
  agents: Agent[]
}

const TasksView: React.FC<TasksViewProps> = React.memo(({ tasks, agents }) => {
  const getStatusColor = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'in_progress': return 'bg-blue-100 text-blue-800'
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'failed': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }, [])

  const getStatusIcon = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'completed': return <FiCheckCircle className="w-4 h-4" />
      case 'in_progress': return <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      case 'pending': return <FiClock className="w-4 h-4" />
      case 'failed': return <FiAlertCircle className="w-4 h-4" />
      default: return <FiClock className="w-4 h-4" />
    }
  }, [])

  const getPriorityColor = useCallback((priority: number) => {
    if (priority >= 8) return 'text-red-600'
    if (priority >= 6) return 'text-yellow-600'
    if (priority >= 4) return 'text-blue-600'
    return 'text-gray-600'
  }, [])

  // Memoize agent lookup map
  const agentMap = useMemo(() => {
    return agents.reduce((map, agent) => {
      map[agent.id] = agent.name
      return map
    }, {} as Record<string, string>)
  }, [agents])

  const getAgentName = useCallback((agentId: string) => {
    return agentMap[agentId] || 'Unknown Agent'
  }, [agentMap])

  // Memoize sorted tasks
  const sortedTasks = useMemo(() => {
    return [...tasks].sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  }, [tasks])

  if (tasks.length === 0) {
    return (
      <div className="text-center py-12">
        <FiCheckCircle className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-4 text-gray-500">No tasks assigned yet. Create tasks for your agents!</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-3 px-4 font-medium text-gray-900">Task</th>
            <th className="text-left py-3 px-4 font-medium text-gray-900">Status</th>
            <th className="text-left py-3 px-4 font-medium text-gray-900">Assigned To</th>
            <th className="text-left py-3 px-4 font-medium text-gray-900">Priority</th>
            <th className="text-left py-3 px-4 font-medium text-gray-900">Created</th>
          </tr>
        </thead>
        <tbody>
          {sortedTasks.map((task) => (
            <tr key={task.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
              <td className="py-4 px-4">
                <div>
                  <p className="font-medium text-gray-900">{task.title}</p>
                  <p className="text-sm text-gray-600 max-w-md truncate">{task.description}</p>
                  <span className="inline-block mt-1 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                    {task.type.replace('_', ' ')}
                  </span>
                </div>
              </td>
              <td className="py-4 px-4">
                <div className="flex items-center gap-2">
                  {getStatusIcon(task.status)}
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(task.status)}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </div>
              </td>
              <td className="py-4 px-4">
                <div className="flex items-center gap-2">
                  <FiUser className="w-4 h-4 text-gray-400" />
                  <span className="font-medium text-gray-900">{getAgentName(task.assigned_to)}</span>
                </div>
              </td>
              <td className="py-4 px-4">
                <span className={`font-semibold ${getPriorityColor(task.priority)}`}>
                  {task.priority}
                </span>
              </td>
              <td className="py-4 px-4 text-sm text-gray-600">
                {new Date(task.created_at).toLocaleDateString()}
                <br />
                <span className="text-xs text-gray-400">
                  {new Date(task.created_at).toLocaleTimeString()}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
})

export default TasksView