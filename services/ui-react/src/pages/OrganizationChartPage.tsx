import React, { useState, useEffect } from 'react'
import { FiRefreshCw, FiSearch, FiFilter, FiDownload, FiUsers } from 'react-icons/fi'
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

interface HierarchyData {
  nodes: Node[]
  edges: Edge[]
  metadata: {
    total_organizations: number
    total_teams: number
    total_agents: number
    generated_at: string
  }
}

interface HierarchyStats {
  organizations: number
  teams: number
  agents: number
  by_organization: Array<{
    id: string
    name: string
    teams: number
    agents: number
    teams_by_type: Record<string, number>
    agents_by_type: Record<string, number>
  }>
  agent_types: Record<string, number>
  team_types: Record<string, number>
}

const nodeTypes = {
  organization: ({ data }: { data: any }) => (
    <div 
      className="px-4 py-3 shadow-lg rounded-lg border-2 cursor-pointer transition-all hover:shadow-xl min-w-[200px]"
      style={{
        backgroundColor: '#1e40af',
        color: 'white',
        border: '2px solid #1e3a8a',
      }}
    >
      <div className="text-center">
        <div className="font-bold text-lg">{data.label}</div>
        {data.description && (
          <div className="text-xs opacity-90 mt-1">{data.description}</div>
        )}
        <div className="text-xs mt-2 opacity-75">
          {data.settings?.type || 'Organization'}
        </div>
      </div>
    </div>
  ),
  team: ({ data }: { data: any }) => (
    <div 
      className="px-3 py-2 shadow-md rounded-lg border cursor-pointer transition-all hover:shadow-lg min-w-[180px]"
      style={{
        backgroundColor: '#059669',
        color: 'white',
        border: '2px solid #047857',
      }}
    >
      <div className="text-center">
        <div className="font-semibold text-sm">{data.label}</div>
        {data.description && (
          <div className="text-xs opacity-90 mt-1 line-clamp-2">{data.description}</div>
        )}
        <div className="text-xs mt-1 opacity-75">{data.type}</div>
      </div>
    </div>
  ),
  agent: ({ data }: { data: any }) => (
    <div 
      className="px-2 py-1 shadow-sm rounded border cursor-pointer transition-all hover:shadow-md min-w-[150px]"
      style={{
        backgroundColor: data.style?.background || '#6b7280',
        color: 'white',
        border: `2px solid ${data.style?.border || '#4b5563'}`,
      }}
    >
      <div className="text-center">
        <div className="font-medium text-xs">{data.label}</div>
        {data.role && (
          <div className="text-xs opacity-90 mt-1">{data.role}</div>
        )}
        <div className="text-xs mt-1 opacity-75">{data.type}</div>
        <div className="text-xs mt-1 opacity-75 bg-black bg-opacity-20 rounded px-1">
          {data.status}
        </div>
      </div>
    </div>
  ),
}

const OrganizationChartPage: React.FC = () => {
  const [hierarchyData, setHierarchyData] = useState<HierarchyData | null>(null)
  const [stats, setStats] = useState<HierarchyStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedEntityType, setSelectedEntityType] = useState<string>('all')

  const [nodes, setNodes, onNodesChange] = useNodesState([] as Node[])
  const [edges, setEdges, onEdgesChange] = useEdgesState([] as Edge[])

  const fetchHierarchyData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Fetch hierarchy visualization data
      const response = await fetch('http://localhost:8000/hierarchy/visualization')
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data: HierarchyData = await response.json()
      setHierarchyData(data)
      setNodes(data.nodes)
      setEdges(data.edges)
      
      // Fetch statistics
      const statsResponse = await fetch('http://localhost:8000/hierarchy/stats')
      if (statsResponse.ok) {
        const statsData: HierarchyStats = await statsResponse.json()
        setStats(statsData)
      }
      
    } catch (err) {
      console.error('Failed to fetch hierarchy data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load hierarchy data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHierarchyData()
  }, [])

  const filteredNodes = React.useMemo(() => {
    if (!hierarchyData || (!searchTerm && selectedEntityType === 'all')) {
      return nodes
    }

    return nodes.filter((node: Node) => {
      // Type filter
      if (selectedEntityType !== 'all' && node.type !== selectedEntityType) {
        return false
      }

      // Search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase()
        const data = node.data as any
        const label = data?.label?.toLowerCase() || ''
        const description = data?.description?.toLowerCase() || ''
        const role = data?.role?.toLowerCase() || ''
        const type = data?.type?.toLowerCase() || ''
        
        return label.includes(searchLower) || 
               description.includes(searchLower) ||
               role.includes(searchLower) ||
               type.includes(searchLower)
      }

      return true
    })
  }, [nodes, searchTerm, selectedEntityType, hierarchyData])

  const exportHierarchy = () => {
    if (!hierarchyData) return
    
    const dataStr = JSON.stringify(hierarchyData, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
    
    const exportFileDefaultName = `fuzeagent-hierarchy-${new Date().toISOString().split('T')[0]}.json`
    
    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <FiRefreshCw className="animate-spin h-8 w-8 text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading organizational hierarchy...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Failed to load hierarchy</h3>
            <div className="mt-2 text-sm text-red-700">
              <p>{error}</p>
            </div>
            <div className="mt-4">
              <button
                onClick={fetchHierarchyData}
                className="bg-red-100 text-red-800 px-3 py-1 rounded text-sm hover:bg-red-200 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Actions Header */}
      <div className="flex items-center justify-end space-x-3">
        <button
          onClick={fetchHierarchyData}
          className="inline-flex items-center px-3 py-2 border border-input shadow-sm text-sm leading-4 font-medium rounded-md text-foreground bg-card hover:bg-accent focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring"
        >
          <FiRefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </button>
        <button
          onClick={exportHierarchy}
          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-primary-foreground bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring"
        >
          <FiDownload className="h-4 w-4 mr-2" />
          Export
        </button>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <FiUsers className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Organizations</dt>
                    <dd className="text-lg font-medium text-gray-900">{stats.organizations}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Teams</dt>
                    <dd className="text-lg font-medium text-gray-900">{stats.teams}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Agents</dt>
                    <dd className="text-lg font-medium text-gray-900">{stats.agents}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-6 w-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">Agent Types</dt>
                    <dd className="text-lg font-medium text-gray-900">{Object.keys(stats.agent_types).length}</dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FiSearch className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search organizations, teams, or agents..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
          <div className="sm:w-48">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FiFilter className="h-5 w-5 text-gray-400" />
              </div>
              <select
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                value={selectedEntityType}
                onChange={(e) => setSelectedEntityType(e.target.value)}
              >
                <option value="all">All Types</option>
                <option value="organization">Organizations</option>
                <option value="team">Teams</option>
                <option value="agent">Agents</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Organization Chart */}
      <div className="bg-white shadow rounded-lg p-4">
        <div style={{ height: '800px' }}>
          <ReactFlow
            nodes={filteredNodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{
              padding: 0.1,
              includeHiddenNodes: false,
              maxZoom: 1.2,
            }}
            minZoom={0.1}
            maxZoom={2}
            defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
          >
            <Controls />
            <Background />
          </ReactFlow>
        </div>
        
        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#1e40af' }}></div>
            <span>Organizations</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#059669' }}></div>
            <span>Teams</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#dc2626' }}></div>
            <span>Executive Agents</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#2563eb' }}></div>
            <span>Developer Agents</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#7c3aed' }}></div>
            <span>Marketing Agents</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#ea580c' }}></div>
            <span>Sales Agents</span>
          </div>
        </div>
      </div>

      {/* Organization Details */}
      {stats && stats.by_organization.length > 0 && (
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Organization Details</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {stats.by_organization.map((org) => (
              <div key={org.id} className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-md font-medium text-gray-900">{org.name}</h4>
                    <p className="text-sm text-gray-500">{org.teams} teams • {org.agents} agents</p>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-gray-500">
                      <div>Team Types: {Object.keys(org.teams_by_type).length}</div>
                      <div>Agent Types: {Object.keys(org.agents_by_type).length}</div>
                    </div>
                  </div>
                </div>
                
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h5 className="text-sm font-medium text-gray-700 mb-2">Teams by Type</h5>
                    <div className="space-y-1">
                      {Object.entries(org.teams_by_type).map(([type, count]) => (
                        <div key={type} className="flex justify-between text-sm">
                          <span className="text-gray-600 capitalize">{type.replace(/_/g, ' ')}</span>
                          <span className="font-medium">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <h5 className="text-sm font-medium text-gray-700 mb-2">Agents by Type</h5>
                    <div className="space-y-1">
                      {Object.entries(org.agents_by_type).map(([type, count]) => (
                        <div key={type} className="flex justify-between text-sm">
                          <span className="text-gray-600 capitalize">{type}</span>
                          <span className="font-medium">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default OrganizationChartPage