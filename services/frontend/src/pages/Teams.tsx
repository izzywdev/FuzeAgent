import { useState, useEffect } from 'react'
import { 
  Users, 
  Plus, 
  Search, 
  Filter,
  Edit,
  Trash2,
  Activity,
  UserPlus
} from 'lucide-react'

interface Team {
  id: string
  name: string
  description: string
  memberCount: number
  status: 'active' | 'inactive'
  createdAt: string
  agents: string[]
  projects: string[]
}

export function Teams() {
  const [teams, setTeams] = useState<Team[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  useEffect(() => {
    fetchTeams()
  }, [])

  const fetchTeams = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch('http://localhost:8000/teams')
      if (response.ok) {
        const data = await response.json()
        setTeams(data)
      } else {
        throw new Error('Failed to fetch teams')
      }
    } catch (error) {
      console.error('Error fetching teams:', error)
      setError('Failed to load teams')
    } finally {
      setIsLoading(false)
    }
  }

  const handleTeamAction = async (teamId: string, action: 'activate' | 'deactivate' | 'delete') => {
    try {
      const response = await fetch(`http://localhost:8000/teams/${teamId}/${action}`, {
        method: 'POST'
      })
      
      if (response.ok) {
        // Refresh teams list
        await fetchTeams()
      } else {
        throw new Error(`Failed to ${action} team`)
      }
    } catch (error) {
      console.error(`Error ${action}ing team:`, error)
      setError(`Failed to ${action} team`)
    }
  }

  const filteredTeams = teams.filter(team => {
    const matchesSearch = team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         team.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = statusFilter === 'all' || team.status === statusFilter
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
          <h1 className="text-2xl font-bold text-gray-900">Teams</h1>
          <p className="text-gray-600">Organize your AI agents into collaborative teams</p>
        </div>
        <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
          <Plus className="h-4 w-4 mr-2" />
          New Team
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
                placeholder="Search teams..."
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
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </div>
      </div>

      {/* Teams Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredTeams.map((team) => (
          <div key={team.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
            <div className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-green-100 rounded-lg">
                      <Users className="h-6 w-6 text-green-600" />
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-gray-900">{team.name}</h3>
                      <p className="text-sm text-gray-500">{team.memberCount} members</p>
                    </div>
                  </div>
                  
                  <p className="mt-3 text-sm text-gray-600">{team.description}</p>
                  
                  <div className="mt-4 flex items-center space-x-4 text-sm text-gray-500">
                    <span>Created: {team.createdAt}</span>
                    <span>Agents: {team.agents.length}</span>
                  </div>

                  {team.projects && team.projects.length > 0 && (
                    <div className="mt-3">
                      <p className="text-xs font-medium text-gray-500 mb-2">Active Projects</p>
                      <div className="flex flex-wrap gap-1">
                        {team.projects.slice(0, 2).map((project, index) => (
                          <span
                            key={index}
                            className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                          >
                            {project}
                          </span>
                        ))}
                        {team.projects.length > 2 && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            +{team.projects.length - 2} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  team.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}>
                  {team.status}
                </span>
              </div>

              <div className="mt-6 flex items-center justify-between">
                <div className="flex space-x-2">
                  {team.status === 'active' ? (
                    <button
                      onClick={() => handleTeamAction(team.id, 'deactivate')}
                      className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Deactivate
                    </button>
                  ) : (
                    <button
                      onClick={() => handleTeamAction(team.id, 'activate')}
                      className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Activate
                    </button>
                  )}
                  
                  <button className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    <UserPlus className="h-4 w-4 mr-1" />
                    Add Member
                  </button>
                  
                  <button className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    <Edit className="h-4 w-4 mr-1" />
                    Edit
                  </button>
                </div>

                <button
                  onClick={() => handleTeamAction(team.id, 'delete')}
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

      {filteredTeams.length === 0 && (
        <div className="text-center py-12">
          <Users className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No teams found</h3>
          <p className="mt-1 text-sm text-gray-500">
            {teams.length === 0 ? 'Get started by creating your first team.' : 'Try adjusting your search or filters.'}
          </p>
        </div>
      )}
    </div>
  )
}
