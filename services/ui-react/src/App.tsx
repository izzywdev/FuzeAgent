import { useState, useEffect, useCallback, useMemo } from 'react'
import axios from 'axios'
import { FiRefreshCw, FiPlus, FiUser, FiActivity, FiCheckCircle } from 'react-icons/fi'
import AgentDashboard from './components/AgentDashboard'
import CreateAgentModal from './components/CreateAgentModal'
import TasksView from './components/TasksView'
import StatsCards from './components/StatsCards'
import type { Agent, Task, AgentTemplate } from './types'

const API_BASE = 'http://localhost:8000'

function App() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [templates, setTemplates] = useState<AgentTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Helper function to deep compare arrays
  const arraysEqual = (a: any[], b: any[]): boolean => {
    if (a.length !== b.length) return false
    return JSON.stringify(a) === JSON.stringify(b)
  }

  const loadData = useCallback(async (forceRefresh = false) => {
    try {
      setLoading(true)
      const [agentsRes, tasksRes, templatesRes] = await Promise.all([
        axios.get(`${API_BASE}/agents`),
        axios.get(`${API_BASE}/tasks`),
        axios.get(`${API_BASE}/templates`)
      ])
      
      const newAgents = agentsRes.data
      const newTasks = tasksRes.data
      const newTemplates = templatesRes.data.templates

      // Only update state if data has actually changed
      if (forceRefresh || !arraysEqual(agents, newAgents)) {
        setAgents(newAgents)
      }
      if (forceRefresh || !arraysEqual(tasks, newTasks)) {
        setTasks(newTasks)
      }
      if (forceRefresh || !arraysEqual(templates, newTemplates)) {
        setTemplates(newTemplates)
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }, [agents, tasks, templates])

  useEffect(() => {
    loadData(true) // Force refresh on initial load
  }, [])

  // Smart polling - only check for updates, don't force re-render
  useEffect(() => {
    const interval = setInterval(() => {
      loadData(false) // Don't force refresh, only update if data changed
    }, 30000) // Reduced frequency to 30 seconds
    return () => clearInterval(interval)
  }, [loadData])

  const handleCreateAgent = useCallback(async (agentData: any) => {
    try {
      if (agentData.template_id) {
        await axios.post(`${API_BASE}/agents/from-template`, agentData)
      } else {
        await axios.post(`${API_BASE}/agents`, agentData)
      }
      await loadData(true) // Force refresh after creating
      setShowCreateModal(false)
    } catch (error) {
      console.error('Error creating agent:', error)
      throw error
    }
  }, [loadData])

  const handleAssignTask = useCallback(async (agentId: string, taskData: any) => {
    try {
      await axios.post(`${API_BASE}/agents/${agentId}/tasks`, taskData)
      await loadData(true) // Force refresh after task assignment
    } catch (error) {
      console.error('Error assigning task:', error)
      throw error
    }
  }, [loadData])

  const handleRefresh = useCallback(() => {
    loadData(true) // Force refresh when user clicks refresh
  }, [loadData])

  // Memoize expensive computations
  const memoizedAgents = useMemo(() => agents, [agents])
  const memoizedTasks = useMemo(() => tasks, [tasks])
  const memoizedTemplates = useMemo(() => templates, [templates])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading FuzeAgent...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <nav className="bg-white shadow-lg border-b">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-blue-600 flex items-center gap-2">
                <FiUser className="text-3xl" />
                FuzeAgent
              </h1>
              <span className="ml-2 text-sm text-gray-500">AI Team Manager</span>
            </div>
            <div className="flex space-x-4 items-center">
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2 transition-colors disabled:opacity-50"
              >
                <FiRefreshCw className={loading ? 'animate-spin' : ''} />
                Refresh
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 flex items-center gap-2 transition-colors"
              >
                <FiPlus />
                Create Agent
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4">
        {/* Statistics */}
        <StatsCards agents={memoizedAgents} tasks={memoizedTasks} />

        {/* Agents Grid */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <FiActivity />
              AI Agents
            </h2>
            <p className="text-gray-600 mt-1">Manage your AI team members</p>
          </div>
          <div className="p-6">
            <AgentDashboard 
              agents={memoizedAgents} 
              tasks={memoizedTasks}
              onAssignTask={handleAssignTask}
            />
          </div>
        </div>

        {/* Tasks Section */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <FiCheckCircle />
              Recent Tasks
            </h2>
            <p className="text-gray-600 mt-1">Track task assignments and progress</p>
          </div>
          <div className="p-6">
            <TasksView tasks={memoizedTasks} agents={memoizedAgents} />
          </div>
        </div>
      </main>

      {/* Create Agent Modal */}
      {showCreateModal && (
        <CreateAgentModal
          templates={memoizedTemplates}
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateAgent}
        />
      )}
    </div>
  )
}

export default App
