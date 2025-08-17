import { useState, useEffect } from 'react'
import { 
  Bot, 
  Plus, 
  Search, 
  Filter,
  Play,
  Pause,
  Trash2,
  Settings,
  Activity
} from 'lucide-react'

interface Agent {
  id: string
  name: string
  type: string
  status: 'active' | 'idle' | 'error' | 'offline'
  description: string
  tasks: {
    completed: number
    running: number
    pending: number
  }
  lastActivity: string
  createdAt: string
  capabilities: string[]
}

export function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8000/agents')
      if (response.ok) {
        const data = await response.json()
        setAgents(data)
      } else {
        throw new Error('Failed to fetch agents')
      }
    } catch (error) {
      console.error('Error fetching agents:', error)
      setError('Failed to load agents')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAgentAction = async (agentId: string, action: 'start' | 'stop' | 'delete') => {
    try {
      const response = await fetch(`http://localhost:8000/agents/${agentId}/${action}`, {
        method: 'POST'
      })
      
      if (response.ok) {
        // Refresh agents list
        await fetchAgents()
      } else {
        throw new Error(`Failed to ${action} agent`)
      }
    } catch (error) {
      console.error(`Error ${action}ing agent:`, error)
      setError(`Failed to ${action} agent`)
    }
  }

  const filteredAgents = agents.filter(agent => {
    const matchesSearch = agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         agent.type.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || agent.status === statusFilter
    return matchesSearch && matchesStatus
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="text-red-400">
            <Activity className="h-5 w-5" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error</h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Agents</h1>
          <p className="text-gray-600">Manage and monitor your AI agents</p>
        </div>
        <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
          <Plus className="h-4 w-4 mr-2" />
          New Agent
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search agents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="idle">Idle</option>
              <option value="error">Error</option>
              <option value="offline">Offline</option>
            </select>
          </div>
        </div>
      </div>

      {/* Agents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredAgents.map((agent) => (
          <div key={agent.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
            <div className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <Bot className="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">{agent.name}</h3>
                      <p className="text-sm text-gray-500">{agent.type}</p>
                    </div>
                  </div>
                  
                  <p className="mt-3 text-sm text-gray-600">{agent.description}</p>
                  
                  <div className="mt-4 flex items-center space-x-4 text-sm text-gray-500">
                    <span>Tasks: {agent.tasks.completed + agent.tasks.running + agent.tasks.pending}</span>
                    <span>Last: {agent.lastActivity}</span>
                  </div>

                  {agent.capabilities && agent.capabilities.length > 0 && (
                    <div className="mt-3">
                      <div className="flex flex-wrap gap-1">
                        {agent.capabilities.slice(0, 3).map((capability, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                          >
                            {capability}
                          </span>
                        ))}
                        {agent.capabilities.length > 3 && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            +{agent.capabilities.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  agent.status === 'active' ? 'bg-green-100 text-green-800' :
                  agent.status === 'idle' ? 'bg-yellow-100 text-yellow-800' :
                  agent.status === 'error' ? 'bg-red-100 text-red-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {agent.status}
                </span>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <div className="flex space-x-2">
                  {agent.status === 'active' ? (
                    <button
                      onClick={() => handleAgentAction(agent.id, 'stop')}
                      className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <Pause className="h-4 w-4 mr-1" />
                      Pause
                    </button>
                  ) : (
                    <button
                      onClick={() => handleAgentAction(agent.id, 'start')}
                      className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <Play className="h-4 w-4 mr-1" />
                      Start
                    </button>
                  )}
                  
                  <button className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    <Settings className="h-4 w-4 mr-1" />
                    Config
                  </button>
                </div>

                <button
                  onClick={() => handleAgentAction(agent.id, 'delete')}
                  className="inline-flex items-center px-3 py-2 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredAgents.length === 0 && (
        <div className="text-center py-12">
          <Bot className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No agents found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {agents.length === 0 ? 'Get started by creating your first AI agent.' : 'Try adjusting your search or filters.'}
          </p>
        </div>
      )}
    </div>
  )
}
