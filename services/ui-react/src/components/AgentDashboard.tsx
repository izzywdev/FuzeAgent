import React, { useState, useMemo, useCallback } from 'react'
import { FiUser, FiActivity, FiSettings } from 'react-icons/fi'
import type { Agent, Task } from '../types'
import AssignTaskModal from './AssignTaskModal'

interface AgentDashboardProps {
  agents: Agent[]
  tasks: Task[]
  onAssignTask: (agentId: string, taskData: any) => Promise<void>
}

const AgentDashboard: React.FC<AgentDashboardProps> = React.memo(({ agents, tasks, onAssignTask }) => {
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [showAssignTaskModal, setShowAssignTaskModal] = useState(false)

  // Memoize color functions
  const getStatusColor = useCallback((status: string) => {
    switch (status.toLowerCase()) {
      case 'active': return 'bg-green-100 text-green-800'
      case 'busy': return 'bg-yellow-100 text-yellow-800'
      case 'inactive': return 'bg-gray-100 text-gray-800'
      case 'error': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }, [])

  const getTypeColor = useCallback((type: string) => {
    switch (type.toLowerCase()) {
      case 'executive': return 'bg-blue-100 text-blue-800'
      case 'developer': return 'bg-green-100 text-green-800'
      case 'specialized': return 'bg-purple-100 text-purple-800'
      case 'qa': return 'bg-yellow-100 text-yellow-800'
      case 'designer': return 'bg-pink-100 text-pink-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }, [])

  const handleAssignTask = useCallback((agentId: string) => {
    setSelectedAgentId(agentId)
    setShowAssignTaskModal(true)
  }, [])

  const handleTaskSubmit = useCallback(async (taskData: any) => {
    if (selectedAgentId) {
      await onAssignTask(selectedAgentId, taskData)
      setShowAssignTaskModal(false)
      setSelectedAgentId(null)
    }
  }, [selectedAgentId, onAssignTask])

  // Memoize task calculations per agent
  const agentTaskData = useMemo(() => {
    return agents.map(agent => {
      const agentTasks = tasks.filter(t => t.assigned_to === agent.id)
      return {
        agent,
        agentTasks,
        pendingTasks: agentTasks.filter(t => t.status === 'pending').length,
        completedTasks: agentTasks.filter(t => t.status === 'completed').length
      }
    })
  }, [agents, tasks])

  if (agents.length === 0) {
    return (
      <div className="text-center py-12">
        <FiUser className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-4 text-gray-500">No agents found. Create your first agent!</p>
      </div>
    )
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agentTaskData.map(({ agent, agentTasks, pendingTasks, completedTasks }) => (
          <div
            key={agent.id}
            className="agent-card border rounded-lg p-4 hover:shadow-md transition-all fade-in bg-white"
          >
            <div className="flex justify-between items-start mb-3">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <FiUser className="text-blue-600" />
                {agent.name}
              </h3>
              <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(agent.status)}`}>
                {agent.status}
              </span>
            </div>
            
            <p className="text-gray-600 text-sm mb-2">{agent.role}</p>
            
            <div className="flex justify-between items-center mb-3">
              <span className={`px-2 py-1 rounded text-xs font-medium ${getTypeColor(agent.type)}`}>
                {agent.type}
              </span>
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <FiActivity />
                {agentTasks.length} tasks
              </span>
            </div>

            {agent.template_id && (
              <div className="mb-3">
                <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                  Template: {agent.template_id}
                </span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="font-semibold text-yellow-600">{pendingTasks}</div>
                <div className="text-gray-500">Pending</div>
              </div>
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="font-semibold text-green-600">{completedTasks}</div>
                <div className="text-gray-500">Completed</div>
              </div>
            </div>

            <div className="space-y-2">
              <button
                onClick={() => handleAssignTask(agent.id)}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded text-sm hover:bg-blue-700 transition-colors"
              >
                Assign Task
              </button>
              <button
                className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded text-sm hover:bg-gray-200 transition-colors flex items-center justify-center gap-2"
              >
                <FiSettings className="text-xs" />
                Configure
              </button>
            </div>
          </div>
        ))}
      </div>

      {showAssignTaskModal && (
        <AssignTaskModal
          agentName={agents.find(a => a.id === selectedAgentId)?.name || ''}
          onClose={() => {
            setShowAssignTaskModal(false)
            setSelectedAgentId(null)
          }}
          onSubmit={handleTaskSubmit}
        />
      )}
    </>
  )
})

export default AgentDashboard