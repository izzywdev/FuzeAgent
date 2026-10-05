import { useState, useEffect, useCallback, useMemo } from 'react'
import { FiRefreshCw, FiPlus, FiUser, FiActivity, FiCheckCircle, FiUsers } from 'react-icons/fi'
import AgentDashboard from './components/AgentDashboard'
import CreateAgentModal from './components/CreateAgentModal'
import TasksView from './components/TasksView'
import StatsCards from './components/StatsCards'
import OrganizationSelector from './components/OrganizationSelector'
import TeamSelector from './components/TeamSelector'
import HierarchyView from './components/HierarchyView'
import ImageTemplateRegistry from './components/ImageTemplateRegistry'
import BrainsMemoryHierarchy from './components/BrainsMemoryHierarchy'
import SandboxesView from './components/SandboxesView'
import EscalationsView from './components/EscalationsView'
import { MultiAgentChatWorkspace } from './components/MultiAgentChatWorkspace'
import { OrgProvider, useOrgContext } from './context/OrgContext'
import { api, createWebSocket } from './config/api'
import type { 
  Agent, Task, AgentTemplate, 
  Organization, Team, 
  OrganizationCreate, TeamCreate 
} from './types'


function FuzeAgentDashboard() {
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
  const [activeTab, setActiveTab] = useState<'overview' | 'workspace' | 'templates' | 'brains' | 'sandboxes' | 'teams' | 'escalations'>('overview')
  const [showEventsDropdown, setShowEventsDropdown] = useState(false)
  const { activeOrg, isPersonal, user: orgUser, organizations: platformOrgs, switchOrg, recentEvents, allowInAppOrgManagement } = useOrgContext()

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.add('dark')
    }
  }, [])

  // FuzeFront Platform Bridge: Register app-specific menu items into host shell
  useEffect(() => {
    const bridge = typeof window !== 'undefined' ? (window as any).__FUZEFRONT__ : null
    if (bridge?.menu) {
      bridge.menu.add('fuzeagent', [
        { id: 'overview', label: 'Agents Overview', icon: '🤖', order: 1 },
        { id: 'workspace', label: 'Agent Workspace (VS Code)', icon: '🖥️', order: 2 },
        { id: 'templates', label: 'Image Registry', icon: '📦', order: 3 },
        { id: 'brains', label: 'Brains & Memory Wiki', icon: '🧠', order: 4 },
        { id: 'sandboxes', label: 'Sandboxes & Runtime', icon: '🛡️', order: 5 },
        { id: 'teams', label: 'Teams & Hierarchy', icon: '👥', order: 6 },
        { id: 'escalations', label: 'Escalations & Approvals', icon: '⚡', order: 7 },
      ])
    }

    const handleHostNav = (e: any) => {
      const target = e.detail?.section || e.detail?.id || e.detail
      if (typeof target === 'string') {
        const clean = target.replace(/^\/?(app\/)?fuzeagent\/?/, '').replace(/^\//, '')
        if (['overview', 'workspace', 'templates', 'brains', 'sandboxes', 'teams', 'escalations'].includes(clean)) {
          setActiveTab(clean as any)
        } else if (clean === '' || clean === 'agents') {
          setActiveTab('overview')
        }
      }
    }

    const handleOrgSwitch = (e: any) => {
      const org = e.detail?.organization
      if (org?.id && organizations.length > 0) {
        const found = organizations.find((o) => o.id === org.id || o.name === org.name)
        if (found) setCurrentOrganization(found)
      }
    }

    window.addEventListener('fuzefront:navigate', handleHostNav)
    window.addEventListener('fuzefront:org-switched', handleOrgSwitch)
    window.addEventListener('fuzefront:organization-switched', handleOrgSwitch)
    return () => {
      window.removeEventListener('fuzefront:navigate', handleHostNav)
      window.removeEventListener('fuzefront:org-switched', handleOrgSwitch)
      window.removeEventListener('fuzefront:organization-switched', handleOrgSwitch)
      if (bridge?.menu) {
        bridge.menu.remove('fuzeagent')
      }
    }
  }, [organizations])


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
        api.orchestrator.get('/templates').then((res) => (Array.isArray(res) ? res : res.templates))
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
      ws = createWebSocket('/ws')
    } catch (e) {
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
      ws && ws.close()
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
      <div 
        className="min-h-screen flex items-center justify-center"
        style={{ backgroundColor: 'var(--bg-primary, #0f131c)', color: 'var(--text-primary, #e7ecf5)' }}
      >
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto" style={{ borderColor: 'var(--accent-color, #6e5cff)' }}></div>
          <p className="mt-4 text-xs font-mono" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>Loading FuzeAgent Workspace...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="dark min-h-screen text-[var(--text-primary)]" style={{ backgroundColor: 'var(--bg-primary, #0f131c)' }}>
      {/* Header */}
      <nav className="border-b shadow-sm" style={{ backgroundColor: 'var(--bg-secondary, #0b0e15)', borderColor: 'var(--border-color, #232c3d)' }}>
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex items-center gap-6">
              <div className="flex items-center cursor-pointer" onClick={() => setActiveTab('overview')}>
                <h1 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--text-primary, #e7ecf5)' }}>
                  <span className="p-1.5 rounded-lg border text-indigo-400" style={{ backgroundColor: 'rgba(110, 92, 255, 0.15)', borderColor: 'rgba(110, 92, 255, 0.3)' }}>
                    <FiUser className="text-xl" />
                  </span>
                  <span>FuzeAgent</span>
                </h1>
                <span className="ml-2 text-xs font-mono opacity-50 text-[var(--text-secondary)]">v2.0</span>
              </div>

              {/* In-App Tab Switcher (mirrors FuzeFront Left-Side Menu) */}
              <div className="hidden md:flex items-center space-x-1">
                {[
                  { id: 'overview', label: 'Overview', icon: '🤖' },
                  { id: 'workspace', label: 'Workspace (VS Code)', icon: '🖥️' },
                  { id: 'templates', label: 'Image Registry', icon: '📦' },
                  { id: 'brains', label: 'Brains & Memory', icon: '🧠' },
                  { id: 'sandboxes', label: 'Sandboxes', icon: '🛡️' },
                  { id: 'teams', label: 'Teams', icon: '👥' },
                  { id: 'escalations', label: 'Escalations', icon: '⚡' },
                ].map(tab => {
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                        isActive
                          ? 'font-bold shadow-sm'
                          : 'hover:opacity-100 opacity-70'
                      }`}
                      style={{
                        backgroundColor: isActive ? 'var(--bg-quaternary, #1c2433)' : 'transparent',
                        color: isActive ? 'var(--text-primary, #e7ecf5)' : 'var(--text-secondary, #9fa9bc)',
                        border: isActive ? '1px solid var(--accent-color, #6e5cff)' : '1px solid transparent',
                      }}
                    >
                      <span>{tab.icon}</span>
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex space-x-3 items-center">
              {/* Organization & Context Indicator wrapped with Unleash Kill Switch */}
              <div 
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs shadow-sm"
                style={{
                  backgroundColor: 'var(--bg-tertiary, #141a26)',
                  borderColor: 'var(--border-color, #232c3d)'
                }}
              >
                {isPersonal || !activeOrg ? (
                  <div className="flex items-center gap-2">
                    <span className="text-cyan-400 font-semibold flex items-center gap-1">
                      👤 Personal Context
                    </span>
                    {orgUser && (
                      <span className="text-[11px] opacity-75 font-mono text-[var(--text-secondary)] pl-1.5 border-l" style={{ borderColor: 'var(--border-color)' }}>
                        {orgUser.email || orgUser.name}
                      </span>
                    )}
                    <span className="text-[9px] uppercase px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: 'rgba(41, 211, 230, 0.15)', color: '#29d3e6' }}>
                      Portal Context
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-indigo-400 font-semibold flex items-center gap-1">
                      🏢 {activeOrg.name}
                    </span>
                    {activeOrg.tier && (
                      <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded" style={{ backgroundColor: 'rgba(110, 92, 255, 0.2)', color: '#a78bfa' }}>
                        {activeOrg.tier}
                      </span>
                    )}
                    {orgUser && (
                      <span className="text-[11px] text-[var(--text-secondary)] pl-1.5 border-l" style={{ borderColor: 'var(--border-color)' }}>
                        👤 {orgUser.name || orgUser.email}
                      </span>
                    )}
                    <span className="text-[9px] uppercase px-1.5 py-0.5 rounded font-bold" style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-secondary)' }}>
                      Platform Managed
                    </span>
                  </div>
                )}

                {/* Fallback selector only active when Unleash flag 'fuzeagent.in-app-org-management' is explicitly enabled */}
                {allowInAppOrgManagement && (
                  <select
                    value={activeOrg?.id || ''}
                    onChange={(e) => switchOrg(e.target.value)}
                    className="text-xs font-semibold bg-transparent outline-none cursor-pointer ml-1"
                    style={{ color: 'var(--text-primary)' }}
                  >
                    {platformOrgs.map((org) => (
                      <option key={org.id} value={org.id} style={{ background: '#141a26', color: '#e7ecf5' }}>
                        {org.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Real-time Global Event Notifications */}
              <div className="relative">
                <button
                  onClick={() => setShowEventsDropdown(!showEventsDropdown)}
                  className="px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 text-xs transition-colors border"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)',
                    color: 'var(--text-primary, #e7ecf5)'
                  }}
                  title="Global Platform Events"
                >
                  <span className="text-amber-400">⚡</span>
                  <span className="font-semibold">{recentEvents.length}</span>
                </button>
                {showEventsDropdown && (
                  <div 
                    className="absolute right-0 mt-2 w-80 rounded-xl shadow-2xl border p-3 z-50 animate-in fade-in"
                    style={{
                      backgroundColor: 'var(--bg-secondary, #0b0e15)',
                      borderColor: 'var(--border-color, #232c3d)',
                      color: 'var(--text-primary, #e7ecf5)'
                    }}
                  >
                    <div className="flex items-center justify-between border-b pb-2 mb-2" style={{ borderColor: 'var(--border-color)' }}>
                      <span className="text-xs font-bold text-white">Global Events Feed</span>
                      <span className="text-[10px] text-[var(--text-secondary)]">Live platform bus</span>
                    </div>
                    {recentEvents.length === 0 ? (
                      <div className="text-xs text-[var(--text-secondary)] py-3 text-center">No recent events</div>
                    ) : (
                      <div className="max-h-48 overflow-y-auto space-y-1.5">
                        {recentEvents.map((evt) => (
                          <div 
                            key={evt.id} 
                            className="text-xs p-2 rounded border"
                            style={{
                              backgroundColor: 'var(--bg-tertiary, #141a26)',
                              borderColor: 'var(--border-color, #232c3d)'
                            }}
                          >
                            <div className="font-mono text-[10px] text-indigo-400 font-bold uppercase">{evt.type}</div>
                            <div className="text-slate-300 text-[11px] mt-0.5">{evt.message}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <button
                onClick={handleRefresh}
                disabled={loading}
                className="px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-xs transition-colors disabled:opacity-50 border"
                style={{
                  backgroundColor: 'var(--bg-tertiary, #141a26)',
                  borderColor: 'var(--border-color, #232c3d)',
                  color: 'var(--text-primary, #e7ecf5)'
                }}
              >
                <FiRefreshCw className={loading ? 'animate-spin' : ''} />
                Refresh
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-3 py-1.5 text-white rounded-lg flex items-center gap-1.5 text-xs font-medium transition-colors shadow-md active:scale-95"
                style={{
                  backgroundColor: 'var(--accent-color, #6e5cff)'
                }}
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
        {activeTab === 'workspace' && (
          <div className="h-[800px] rounded-xl overflow-hidden border border-slate-800 shadow-xl mb-6">
            <MultiAgentChatWorkspace />
          </div>
        )}
        {activeTab === 'templates' && <ImageTemplateRegistry />}
        {activeTab === 'brains' && <BrainsMemoryHierarchy />}
        {activeTab === 'sandboxes' && <SandboxesView />}
        {activeTab === 'escalations' && <EscalationsView />}

        {activeTab === 'teams' && (
          <div className="space-y-6">
            <HierarchyView
              organizations={organizations}
              teams={teams}
              agents={memoizedAgents}
              currentOrganization={currentOrganization}
              onSelectOrganization={handleSelectOrganization}
              onSelectTeam={handleSelectTeam}
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
          </div>
        )}

        {activeTab === 'overview' && (
          <>
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
              <div 
                className="rounded-xl border p-4 mb-6 shadow-sm flex items-center justify-between"
                style={{
                  backgroundColor: 'var(--bg-tertiary, #141a26)',
                  borderColor: 'var(--border-color, #232c3d)',
                  color: 'var(--text-primary, #e7ecf5)'
                }}
              >
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                    Current Scope: <strong className="text-indigo-400 font-semibold">{currentOrganization.name}</strong> → <strong className="text-emerald-400 font-semibold">{currentTeam.name}</strong>
                  </p>
                </div>
                <button
                  onClick={() => setShowCreateModal(true)}
                  disabled={!currentTeam}
                  className="px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-xs font-medium text-white shadow transition-all disabled:opacity-50"
                  style={{ backgroundColor: 'var(--accent-color, #6e5cff)' }}
                >
                  <FiPlus />
                  Add Agent to Squad
                </button>
              </div>
            )}

            {/* Show message if no team selected */}
            {!currentTeam ? (
              <div 
                className="rounded-xl border p-8 text-center shadow-sm"
                style={{
                  backgroundColor: 'var(--bg-tertiary, #141a26)',
                  borderColor: 'var(--border-color, #232c3d)',
                  color: 'var(--text-primary, #e7ecf5)'
                }}
              >
                <FiUsers className="mx-auto h-10 w-10 mb-3 opacity-40 text-emerald-400" />
                <h3 className="text-sm font-semibold mb-1 text-white">Select a Squad</h3>
                <p className="text-xs" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                  {!currentOrganization 
                    ? "Operating in Personal context. Select an organization or squad to view provisioned agents." 
                    : "Please select or create a squad in this organization to view agent activity."}
                </p>
              </div>
            ) : (
              <>
                {/* Statistics */}
                <StatsCards agents={memoizedAgents} tasks={memoizedTasks} />

                {/* Agents Grid */}
                <div 
                  className="rounded-xl border shadow-sm mb-6"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)'
                  }}
                >
                  <div className="p-5 border-b flex items-center justify-between" style={{ borderColor: 'var(--border-color, #232c3d)' }}>
                    <div>
                      <h2 className="text-base font-bold flex items-center gap-2 text-white">
                        <FiActivity className="text-indigo-400" />
                        AI Agents
                        <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ backgroundColor: 'rgba(52, 211, 153, 0.15)', color: '#34d399' }}>
                          {currentTeam.name}
                        </span>
                      </h2>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>Autonomous agent workforce & assigned tools</p>
                    </div>
                  </div>
                  <div className="p-5">
                    <AgentDashboard 
                      agents={memoizedAgents} 
                      tasks={memoizedTasks}
                      onAssignTask={handleAssignTask}
                    />
                  </div>
                </div>

                {/* Tasks Section */}
                <div 
                  className="rounded-xl border shadow-sm"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)'
                  }}
                >
                  <div className="p-5 border-b" style={{ borderColor: 'var(--border-color, #232c3d)' }}>
                    <h2 className="text-base font-bold flex items-center gap-2 text-white">
                      <FiCheckCircle className="text-emerald-400" />
                      Recent Tasks
                    </h2>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>Track autonomous execution progress and outputs</p>
                  </div>
                  <div className="p-5">
                    <TasksView tasks={memoizedTasks} agents={memoizedAgents} />
                  </div>
                </div>
              </>
            )}
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

export default function App() {
  return (
    <OrgProvider>
      <FuzeAgentDashboard />
    </OrgProvider>
  )
}

