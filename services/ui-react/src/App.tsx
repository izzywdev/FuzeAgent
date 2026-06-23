import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FiRefreshCw, FiPlus, FiUser, FiActivity, FiCheckCircle, FiUsers, FiBook, FiCode, FiHelpCircle } from 'react-icons/fi'
import AgentDashboard from './components/AgentDashboard'
import CreateAgentModal from './components/CreateAgentModal'
import TasksView from './components/TasksView'
import StatsCards from './components/StatsCards'
import OrganizationSelector from './components/OrganizationSelector'
import TeamSelector from './components/TeamSelector'
import HierarchyView from './components/HierarchyView'
import { api, API_ENDPOINTS } from './config/api'
import type { 
  Agent, Task, AgentTemplate, 
  Organization, Team, 
  OrganizationCreate, TeamCreate 
} from './types'

function App() {
  // Hierarchy state
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [teams, setTeams] = useState<Team[]>([])
  const [currentOrganization, setCurrentOrganization] = useState<Organization | null>(null)
  const [currentTeam, setCurrentTeam] = useState<Team | null>(null)
  
  // Entity state
  const [agents, setAgents] = useState<Agent[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [templates, setTemplates] = useState<AgentTemplate[]>([])
  
  // UI state
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showHierarchy, setShowHierarchy] = useState(false)

  // Helper function to deep compare arrays
  const arraysEqual = (a: any[], b: any[]): boolean => {
    if (a.length !== b.length) return false
    return JSON.stringify(a) === JSON.stringify(b)
  }

  const loadData = useCallback(async (forceRefresh = false) => {
    try {
      setLoading(true)
      
      // Load organizations from hierarchy API and templates from orchestrator API (optional)
      const results = await Promise.allSettled([
        api.hierarchy.get('/organizations'),
        api.orchestrator.get('/templates').then((res) => res.templates)
      ])

      const newOrganizations = results[0].status === 'fulfilled' ? results[0].value : []
      const newTemplates = results[1].status === 'fulfilled' ? results[1].value : []

      if (forceRefresh || !arraysEqual(organizations, newOrganizations)) {
        setOrganizations(newOrganizations)
        if (!currentOrganization && newOrganizations.length > 0) {
          setCurrentOrganization(newOrganizations[0])
        }
      }

      if (forceRefresh || !arraysEqual(templates, newTemplates)) {
        setTemplates(newTemplates)
      }

      // Load teams for current organization
      if (currentOrganization) {
        const newTeams = await api.hierarchy.get(`/teams?organization_id=${currentOrganization.id}`)
        if (forceRefresh || !arraysEqual(teams, newTeams)) {
          setTeams(newTeams)
          if (!currentTeam && newTeams.length > 0) {
            setCurrentTeam(newTeams[0])
          }
        }
      }

      // Load agents and tasks for current team (tasks optional)
      if (currentTeam) {
        const pair = await Promise.allSettled([
          api.hierarchy.get(`/agents?team_id=${currentTeam.id}`),
          api.orchestrator.get('/tasks')
        ])
        const newAgents = pair[0].status === 'fulfilled' ? pair[0].value : []
        const newTasks = pair[1].status === 'fulfilled' ? pair[1].value : []

        if (forceRefresh || !arraysEqual(agents, newAgents)) {
          setAgents(newAgents)
        }
        if (forceRefresh || !arraysEqual(tasks, newTasks)) {
          setTasks(newTasks)
        }
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }, [organizations, teams, agents, tasks, templates, currentOrganization, currentTeam])

  useEffect(() => {
    loadData(true) // Force refresh on initial load
  }, [])

  // WebSocket for real-time updates (optional; may fail if orchestrator is down)
  useEffect(() => {
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(`${API_ENDPOINTS.WEBSOCKET_BASE}/ws`)
    } catch {
      console.warn('WebSocket unavailable, continuing without realtime updates')
      return
    }
    
    ws.onopen = () => {
      console.log('WebSocket connected')
    }
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        console.log('WebSocket message:', message)
        
        switch (message.type) {
          case 'organization_created':
            setOrganizations(prev => {
              const exists = prev.some(org => org.id === message.data.id)
              if (!exists) {
                return [message.data, ...prev]
              }
              return prev
            })
            break
            
          case 'team_created':
            setTeams(prev => {
              const exists = prev.some(team => team.id === message.data.id)
              if (!exists) {
                return [message.data, ...prev]
              }
              return prev
            })
            break
            
          case 'agent_created':
            setAgents(prev => {
              const exists = prev.some(agent => agent.id === message.data.id)
              if (!exists) {
                return [message.data, ...prev]
              }
              return prev
            })
            break
            
          default:
            // For other types, do a selective reload
            loadData(false)
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error)
      }
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
    }
    
    ws.onerror = (error) => {
      console.warn('WebSocket error (ignored):', error)
    }
    
    // Keep connection alive with ping
    const pingInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)
    
    return () => {
      clearInterval(pingInterval)
      ws?.close()
    }
  }, [])

  // Organization management
  const handleSelectOrganization = useCallback(async (org: Organization) => {
    setCurrentOrganization(org)
    setCurrentTeam(null) // Clear current team when switching organizations
    setAgents([]) // Clear agents when switching organizations
    
    // Load teams for the selected organization
    try {
      const newTeams = await api.hierarchy.get(`/teams?organization_id=${org.id}`)
      setTeams(newTeams)
      
      // Auto-select first team if available
      if (newTeams.length > 0) {
        setCurrentTeam(newTeams[0])
      }
    } catch (error) {
      console.error('Error loading teams:', error)
    }
  }, [])

  const handleCreateOrganization = useCallback(async (orgData: OrganizationCreate) => {
    try {
      await api.hierarchy.post('/organizations', orgData)
      await loadData(true) // Reload all data
    } catch (error) {
      console.error('Error creating organization:', error)
      throw error
    }
  }, [loadData])

  // Team management
  const handleSelectTeam = useCallback(async (team: Team) => {
    setCurrentTeam(team)
    setAgents([]) // Clear agents when switching teams
    
    // Load agents for the selected team
    try {
      const newAgents = await api.hierarchy.get(`/agents?team_id=${team.id}`)
      setAgents(newAgents)
    } catch (error) {
      console.error('Error loading agents:', error)
    }
  }, [])

  const handleCreateTeam = useCallback(async (teamData: TeamCreate) => {
    try {
      await api.hierarchy.post('/teams', teamData)
      await loadData(true) // Reload data
    } catch (error) {
      console.error('Error creating team:', error)
      throw error
    }
  }, [loadData])

  // Agent management (uses orchestrator; leave behavior as-is)
  const handleCreateAgent = useCallback(async (agentData: any) => {
    if (!currentTeam) {
      throw new Error('Please select a team first')
    }

    try {
      // Ensure team_id is included in the request at the top level, not in overrides
      const agentPayload = {
        ...agentData,
        team_id: currentTeam.id,
        overrides: {
          ...agentData.overrides
          // Remove team_id from overrides - it's not customizable per API validation
        }
      }

      if (agentData.template_id) {
        await api.orchestrator.post('/agents/from-template', agentPayload)
      } else {
        await api.orchestrator.post('/agents', { ...agentPayload, team_id: currentTeam.id })
      }
      await loadData(true) // Force refresh after creating
      setShowCreateModal(false)
    } catch (error) {
      console.error('Error creating agent:', error)
      throw error
    }
  }, [currentTeam, loadData])

  const handleAssignTask = useCallback(async (agentId: string, taskData: any) => {
    try {
      await api.orchestrator.post(`/agents/${agentId}/tasks`, taskData)
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
              {/* Help Menu */}
              <div className="relative group">
                <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 flex items-center gap-2 transition-colors">
                  <FiHelpCircle />
                  Help
                </button>
                <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-md shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
                  <div className="py-2">
                    <Link
                      to="/docs"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <FiBook className="w-4 h-4" />
                      Documentation
                    </Link>
                    <Link
                      to="/docs/getting-started"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <FiActivity className="w-4 h-4" />
                      Getting Started
                    </Link>
                    <Link
                      to="/docs/api-reference"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <FiCode className="w-4 h-4" />
                      API Reference
                    </Link>
                    <Link
                      to="/playground"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <FiCode className="w-4 h-4" />
                      API Playground
                    </Link>
                    <Link
                      to="/organization-chart"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <FiUsers className="w-4 h-4" />
                      Organization Chart
                    </Link>
                    <div className="border-t border-gray-100 my-2"></div>
                    <a
                      href="https://github.com/yourusername/fuzeagent"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <FiBook className="w-4 h-4" />
                      GitHub Repository
                    </a>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setShowHierarchy(!showHierarchy)}
                className={`px-4 py-2 rounded-md flex items-center gap-2 transition-colors ${
                  showHierarchy 
                    ? 'bg-purple-600 text-white hover:bg-purple-700' 
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                <FiUsers />
                {showHierarchy ? 'Hide Hierarchy' : 'Show Hierarchy'}
              </button>
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
        {/* Hierarchy View */}
        {showHierarchy && (
          <div className="mb-6">
            <HierarchyView
              organizations={organizations}
              teams={teams}
              agents={memoizedAgents}
              currentOrganization={currentOrganization}
              onSelectOrganization={handleSelectOrganization}
              onSelectTeam={handleSelectTeam}
            />
          </div>
        )}

        {/* Organization and Team Selection */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <OrganizationSelector
            organizations={organizations}
            currentOrganization={currentOrganization}
            loading={loading}
            onSelectOrganization={handleSelectOrganization}
            onCreateOrganization={handleCreateOrganization}
          />
          <TeamSelector
            teams={teams}
            currentTeam={currentTeam}
            currentOrganization={currentOrganization}
            loading={loading}
            onSelectTeam={handleSelectTeam}
            onCreateTeam={handleCreateTeam}
          />
        </div>

        {/* Context Information */}
        {currentOrganization && currentTeam && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-blue-600">
                  Current Context: <span className="font-medium">{currentOrganization.name}</span> → <span className="font-medium">{currentTeam.name}</span>
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(true)}
                disabled={!currentTeam}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FiPlus />
                Add Agent to Team
              </button>
            </div>
          </div>
        )}

        {/* Show message if no team selected */}
        {!currentTeam ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <FiUsers className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Select a Team</h3>
            <p className="text-gray-600">
              {!currentOrganization 
                ? "Please select an organization and team to view agents" 
                : "Please select or create a team to view agents"}
            </p>
          </div>
        ) : (
          <>
            {/* Statistics */}
            <StatsCards agents={memoizedAgents} tasks={memoizedTasks} />

            {/* Agents Grid */}
            <div className="bg-white rounded-lg shadow mb-6">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <FiActivity />
                  AI Agents
                  <span className="text-sm font-normal text-blue-600">({currentTeam.name})</span>
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
          </>
        )}
      </main>

      {/* Create Agent Modal */}
      {showCreateModal && (
        <CreateAgentModal
          templates={memoizedTemplates}
          currentTeam={currentTeam}
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateAgent}
        />
      )}
    </div>
  )
}

export default App
