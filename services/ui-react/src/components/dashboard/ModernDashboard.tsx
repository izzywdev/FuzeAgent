import { useState } from 'react'
import { Link } from 'react-router-dom'

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

// Mock data
const mockAgents: Agent[] = [
  {
    id: '1',
    name: 'IzzyAI CEO',
    type: 'Executive',
    status: 'active',
    tasks: { completed: 23, running: 2, pending: 1 },
    lastActivity: '2 minutes ago'
  },
  {
    id: '2',
    name: 'CTO Agent',
    type: 'Executive',
    status: 'active',
    tasks: { completed: 18, running: 1, pending: 3 },
    lastActivity: '5 minutes ago'
  },
  {
    id: '3',
    name: 'Frontend Dev 1',
    type: 'Developer',
    status: 'idle',
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

export function ModernDashboard() {
  const [agents] = useState<Agent[]>(mockAgents)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center">
                  <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mr-3">
                    <span className="text-white font-bold">F</span>
                  </div>
                  <h1 className="text-xl font-bold text-gray-900">FuzeAgent</h1>
                </div>
              </div>
              
              {/* Navigation Links */}
              <div className="hidden md:ml-6 md:flex md:space-x-8">
                <Link to="/" className="text-blue-600 border-b-2 border-blue-600 px-1 pt-1 pb-4 text-sm font-medium">
                  Dashboard
                </Link>
                <Link to="/agents" className="text-gray-500 hover:text-gray-700 px-1 pt-1 pb-4 text-sm font-medium">
                  Agents
                </Link>
                <Link to="/teams" className="text-gray-500 hover:text-gray-700 px-1 pt-1 pb-4 text-sm font-medium">
                  Teams
                </Link>
                <Link to="/organization-chart" className="text-gray-500 hover:text-gray-700 px-1 pt-1 pb-4 text-sm font-medium">
                  Organization Chart
                </Link>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Search */}
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

              {/* User */}
              <div className="flex items-center">
                <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                  <span className="text-gray-600 font-semibold">U</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* Header */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
            <p className="mt-1 text-sm text-gray-600">
              Monitor your AI agents and team performance
            </p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white overflow-hidden shadow-sm rounded-lg border border-gray-200">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Total Agents</dt>
                      <dd className="text-lg font-medium text-gray-900">12</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow-sm rounded-lg border border-gray-200">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Active Agents</dt>
                      <dd className="text-lg font-medium text-gray-900">8</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow-sm rounded-lg border border-gray-200">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Tasks Completed</dt>
                      <dd className="text-lg font-medium text-gray-900">145</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow-sm rounded-lg border border-gray-200">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Avg Response</dt>
                      <dd className="text-lg font-medium text-gray-900">2.3s</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Active Agents */}
            <div className="lg:col-span-2">
              <div className="bg-white shadow-sm rounded-lg border border-gray-200">
                <div className="px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium text-gray-900">Active Agents</h3>
                    <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
                      + Create Agent
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {agents.map((agent) => (
                      <div key={agent.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center">
                            <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mr-3">
                              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                              </svg>
                            </div>
                            <div>
                              <h4 className="text-sm font-medium text-gray-900">{agent.name}</h4>
                              <p className="text-sm text-gray-500">{agent.type}</p>
                            </div>
                          </div>
                          <div className="flex items-center">
                            <div className={`w-2 h-2 rounded-full mr-2 ${
                              agent.status === 'active' ? 'bg-green-500' :
                              agent.status === 'idle' ? 'bg-yellow-500' : 'bg-red-500'
                            }`}></div>
                            <span className="text-sm text-gray-500 capitalize">{agent.status}</span>
                          </div>
                        </div>
                        <div className="mt-3 grid grid-cols-3 gap-4 text-center">
                          <div>
                            <div className="text-lg font-semibold text-green-600">{agent.tasks.completed}</div>
                            <div className="text-xs text-gray-500">Completed</div>
                          </div>
                          <div>
                            <div className="text-lg font-semibold text-blue-600">{agent.tasks.running}</div>
                            <div className="text-xs text-gray-500">Running</div>
                          </div>
                          <div>
                            <div className="text-lg font-semibold text-gray-600">{agent.tasks.pending}</div>
                            <div className="text-xs text-gray-500">Pending</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div>
              <div className="bg-white shadow-sm rounded-lg border border-gray-200">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Recent Activity</h3>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {recentActivity.map((activity) => (
                      <div key={activity.id} className="flex items-start">
                        <div className={`w-2 h-2 rounded-full mt-2 mr-3 ${
                          activity.status === 'success' ? 'bg-green-500' :
                          activity.status === 'error' ? 'bg-red-500' : 'bg-blue-500'
                        }`}></div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900">{activity.agent}</p>
                          <p className="text-sm text-gray-500">{activity.message}</p>
                          <p className="text-xs text-gray-400 mt-1">{activity.time}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="mt-8">
            <div className="bg-white shadow-sm rounded-lg border border-gray-200">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Quick Actions</h3>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button className="flex items-center justify-center px-4 py-8 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                    <div className="text-center">
                      <svg className="w-8 h-8 text-blue-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      <span className="text-sm font-medium text-gray-900">Deploy New Agent</span>
                    </div>
                  </button>
                  <button className="flex items-center justify-center px-4 py-8 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                    <div className="text-center">
                      <svg className="w-8 h-8 text-green-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                      </svg>
                      <span className="text-sm font-medium text-gray-900">Create Team</span>
                    </div>
                  </button>
                  <Link to="/organization-chart" className="flex items-center justify-center px-4 py-8 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                    <div className="text-center">
                      <svg className="w-8 h-8 text-purple-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 00-2 2z" />
                      </svg>
                      <span className="text-sm font-medium text-gray-900">View Organization Chart</span>
                    </div>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}