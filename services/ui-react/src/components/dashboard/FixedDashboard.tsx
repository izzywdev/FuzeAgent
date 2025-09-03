/**
 * FixedDashboard - Main dashboard component for the FuzeAgent application
 * 
 * This component provides a comprehensive overview of the AI agent ecosystem including:
 * - Key performance metrics and statistics
 * - Active agent status and task information
 * - Recent activity feed
 * - Quick action buttons for common tasks
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useOrganization } from '../../contexts/OrganizationContext'
import { useApiService } from '../../hooks/useApiService'

// ============================================================================
// TYPES AND INTERFACES
// ============================================================================

/**
 * Represents an AI agent in the system
 */
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

/**
 * Dashboard metrics data
 */
interface DashboardMetrics {
  totalAgents: number
  activeAgents: number
  tasksCompleted: number
  teamsCount: number
}

// ============================================================================
// CONSTANTS
// ============================================================================

/**
 * Default organization name - will be loaded from API
 */
const DEFAULT_ORG_NAME = 'Loading...'

/**
 * API endpoints for data fetching
 */
const API_ENDPOINTS = {
  agents: '/agents',
  teams: '/teams'
} as const

// ============================================================================
// COMPONENT
// ============================================================================

/**
 * Main dashboard component that displays system overview and metrics
 * 
 * @returns JSX.Element - The rendered dashboard
 */
export function FixedDashboard(): JSX.Element {
  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================
  
  const { currentOrganization } = useOrganization()
  const apiService = useApiService()
  const [agents, setAgents] = useState<Agent[]>([])
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    totalAgents: 0,
    activeAgents: 0,
    tasksCompleted: 0,
    teamsCount: 0
  })
  const [orgName, setOrgName] = useState<string>(DEFAULT_ORG_NAME)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  
  const navigate = useNavigate()

  // ============================================================================
  // EFFECTS AND DATA FETCHING
  // ============================================================================

  /**
   * Fetch dashboard data on component mount
   */
  useEffect(() => {
    fetchDashboardData()
  }, [])

  // Update organization name when current organization changes
  useEffect(() => {
    if (currentOrganization) {
      setOrgName(currentOrganization.name)
    } else {
      setOrgName('No Organization Selected')
    }
  }, [currentOrganization])

  /**
   * Fetch all required data for the dashboard
   */
  const fetchDashboardData = async (): Promise<void> => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Fetch all dashboard data using the API service
      if (!currentOrganization) {
        throw new Error('No organization selected')
      }
      const { agents: agentsData, teams: teamsData, organizations: orgsData } = await apiService.getDashboardData(currentOrganization.id)

      // Update state with fetched data
      setAgents(agentsData)
      setMetrics({
        totalAgents: agentsData.length,
        activeAgents: agentsData.filter(agent => agent.status === 'active').length,
        tasksCompleted: agentsData.reduce((total, agent) => total + (agent?.tasks?.completed ?? 0), 0),
        teamsCount: Array.isArray(teamsData) ? teamsData.length : 0
      })
      
      // Set organization name from current organization context
      if (currentOrganization) {
        setOrgName(currentOrganization.name)
      } else {
        setOrgName('No Organization Selected')
      }
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error fetching dashboard data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================

  /**
   * Handle navigation to create agent page
   */
  const handleCreateAgent = (): void => {
    navigate('/agents/create')
  }

  /**
   * Handle navigation to create team page
   */
  const handleCreateTeam = (): void => {
    navigate('/teams/create')
  }

  /**
   * Handle navigation to organization profile
   */
  const handleViewOrganization = (): void => {
    navigate('/organization/profile')
  }

  /**
   * Handle navigation to goals page
   */
  const handleViewGoals = (): void => {
    navigate('/goals')
  }

  // ============================================================================
  // RENDER HELPERS
  // ============================================================================

  /**
   * Get status color based on agent status
   */
  const getStatusColor = (status: Agent['status']): string => {
    switch (status) {
      case 'active':
        return 'bg-green-500'
      case 'idle':
        return 'bg-yellow-500'
      case 'error':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  /**
   * Get status text color based on agent status
   */
  const getStatusTextColor = (status: Agent['status']): string => {
    switch (status) {
      case 'active':
        return 'text-green-700'
      case 'idle':
        return 'text-yellow-700'
      case 'error':
        return 'text-red-700'
      default:
        return 'text-gray-700'
    }
  }

  // ============================================================================
  // RENDER
  // ============================================================================

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">Error Loading Dashboard</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={fetchDashboardData}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            {/* Logo and Brand */}
            <div className="flex items-center">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
                  <span className="text-white font-bold text-lg">F</span>
                </div>
                <h1 className="text-xl font-bold text-gray-900">FuzeAgent</h1>
              </div>
              
              {/* Navigation Links */}
              <div className="hidden md:ml-6 md:flex md:space-x-8">
                <Link 
                  to="/" 
                  className="text-blue-600 border-b-2 border-blue-600 px-1 pt-1 pb-4 text-sm font-medium"
                >
                  Dashboard
                </Link>
                <Link 
                  to="/agents" 
                  className="text-gray-500 hover:text-gray-700 px-1 pt-1 pb-4 text-sm font-medium"
                >
                  Agents
                </Link>
                <Link 
                  to="/teams" 
                  className="text-gray-500 hover:text-gray-700 px-1 pt-1 pb-4 text-sm font-medium"
                >
                  Teams
                </Link>
                <Link 
                  to="/goals" 
                  className="text-gray-500 hover:text-gray-700 px-1 pt-1 pb-4 text-sm font-medium"
                >
                  Goals
                </Link>
                <Link 
                  to="/organization-chart" 
                  className="text-gray-500 hover:text-gray-700 px-1 pt-1 pb-4 text-sm font-medium"
                >
                  Organization Chart
                </Link>
              </div>
            </div>

            {/* Search and User */}
            <div className="flex items-center space-x-4">
              {/* Search Input */}
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search..."
                  className="w-64 pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center">
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
              </div>
              
              {/* User Avatar */}
              <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                <span className="text-gray-600 font-semibold text-sm">U</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
              <p className="mt-2 text-gray-600">
                Monitor your AI agents and team performance
              </p>
            </div>
            
            {/* Organization Info Card */}
            <Link 
              to="/organization/profile"
              className="bg-white p-4 rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all duration-200"
            >
              <div className="text-sm text-gray-600">Organization</div>
              <div className="text-lg font-semibold text-gray-900 mt-1">{orgName}</div>
            </Link>
          </div>
        </div>

        {/* Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Agents */}
          <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-blue-600 text-xl">👥</span>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-600">Total Agents</div>
                <div className="text-2xl font-semibold text-gray-900">{metrics.totalAgents}</div>
              </div>
            </div>
          </div>

          {/* Active Agents */}
          <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-green-600 text-xl">⚡</span>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-600">Active Agents</div>
                <div className="text-2xl font-semibold text-gray-900">{metrics.activeAgents}</div>
              </div>
            </div>
          </div>

          {/* Tasks Completed */}
          <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-purple-600 text-xl">✅</span>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-600">Tasks Completed</div>
                <div className="text-2xl font-semibold text-gray-900">{metrics.tasksCompleted}</div>
              </div>
            </div>
          </div>

          {/* Teams */}
          <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-orange-600 text-xl">👥</span>
              </div>
              <div>
                <div className="text-sm font-medium text-gray-600">Teams</div>
                <div className="text-2xl font-semibold text-gray-900">{metrics.teamsCount}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Active Agents Section */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold text-gray-900">Active Agents</h3>
                  <button 
                    onClick={handleCreateAgent}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    + Create Agent
                  </button>
                </div>
              </div>
              
              <div className="p-6">
                {agents.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-4xl mb-2">🤖</div>
                    <p>No agents found</p>
                    <button
                      onClick={handleCreateAgent}
                      className="mt-2 text-blue-600 hover:text-blue-700 text-sm"
                    >
                      Create your first agent
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {agents.map((agent) => (
                      <div key={agent.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-center mb-3">
                          <div className="flex items-center">
                            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mr-3">
                              <span className="text-xl">🤖</span>
                            </div>
                            <div>
                              <h4 className="font-medium text-gray-900">{agent.name}</h4>
                              <p className="text-sm text-gray-600">{agent.type}</p>
                            </div>
                          </div>
                          <div className="flex items-center">
                            <div className={`w-2 h-2 rounded-full mr-2 ${getStatusColor(agent.status)}`}></div>
                            <span className={`text-sm font-medium ${getStatusTextColor(agent.status)} capitalize`}>
                              {agent.status}
                            </span>
                          </div>
                        </div>
                        
                        {/* Task Statistics */}
                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div>
                            <div className="text-lg font-semibold text-green-600">{agent?.tasks?.completed ?? 0}</div>
                            <div className="text-xs text-gray-600">Completed</div>
                          </div>
                          <div>
                            <div className="text-lg font-semibold text-blue-600">{agent?.tasks?.running ?? 0}</div>
                            <div className="text-xs text-gray-600">Running</div>
                          </div>
                          <div>
                            <div className="text-lg font-semibold text-gray-600">{agent?.tasks?.pending ?? 0}</div>
                            <div className="text-xs text-gray-600">Pending</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Recent Activity Section */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Recent Activity</h3>
              </div>
              
              <div className="p-6">
                <div className="space-y-4">
                  {/* Dynamic activity items based on agents */}
                  {agents.slice(0, 3).map((agent) => (
                    <div key={agent.id} className="flex items-start">
                      <div className={`w-2 h-2 rounded-full mt-2 mr-3 flex-shrink-0 ${
                        agent.status === 'active' ? 'bg-green-500' : 
                        agent.status === 'idle' ? 'bg-yellow-500' : 'bg-red-500'
                      }`}></div>
                      <div>
                        <p className="font-medium text-gray-900">{agent.name}</p>
                        <p className="text-sm text-gray-600">
                          {agent.status === 'active' ? 'Currently processing tasks' :
                           agent.status === 'idle' ? 'Standing by for new tasks' :
                           'Requires attention'}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {agent.lastActivity ? 
                            new Date(agent.lastActivity).toLocaleString() : 
                            'Recently updated'
                          }
                        </p>
                      </div>
                    </div>
                  ))}
                  {agents.length === 0 && (
                    <div className="text-center py-4 text-gray-500">
                      <p>No recent activity</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions Section */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Quick Actions</h3>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              <button 
                onClick={handleCreateAgent}
                className="flex flex-col items-center justify-center p-6 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span className="text-3xl mb-2">➕</span>
                <span className="font-medium text-gray-900">Deploy New Agent</span>
              </button>
              
              <button 
                onClick={handleCreateTeam}
                className="flex flex-col items-center justify-center p-6 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span className="text-3xl mb-2">👥</span>
                <span className="font-medium text-gray-900">Create Team</span>
              </button>
              
              <button 
                onClick={handleViewOrganization}
                className="flex flex-col items-center justify-center p-6 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span className="text-3xl mb-2">🏢</span>
                <span className="font-medium text-gray-900">Organization Profile</span>
              </button>
              
              <button 
                onClick={handleViewGoals}
                className="flex flex-col items-center justify-center p-6 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span className="text-3xl mb-2">🎯</span>
                <span className="font-medium text-gray-900">Manage Goals</span>
              </button>
              
              <button 
                onClick={() => navigate('/playground')}
                className="flex flex-col items-center justify-center p-6 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <span className="text-3xl mb-2">🔧</span>
                <span className="font-medium text-gray-900">API Playground</span>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}