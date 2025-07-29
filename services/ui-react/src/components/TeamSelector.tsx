import React, { useState, useCallback } from 'react'
import { FiUsers, FiPlus, FiUser } from 'react-icons/fi'
import type { Team, TeamCreate, Organization } from '../types'

interface TeamSelectorProps {
  teams: Team[]
  currentTeam: Team | null
  currentOrganization: Organization | null
  loading: boolean
  onSelectTeam: (team: Team) => void
  onCreateTeam: (teamData: TeamCreate) => Promise<void>
}

const TEAM_TYPES = [
  { value: 'general', label: 'General', color: 'bg-gray-100 text-gray-800' },
  { value: 'development', label: 'Development', color: 'bg-green-100 text-green-800' },
  { value: 'qa', label: 'QA', color: 'bg-yellow-100 text-yellow-800' },
  { value: 'design', label: 'Design', color: 'bg-purple-100 text-purple-800' },
  { value: 'management', label: 'Management', color: 'bg-blue-100 text-blue-800' }
] as const

const TeamSelector: React.FC<TeamSelectorProps> = React.memo(({
  teams,
  currentTeam,
  currentOrganization,
  loading,
  onSelectTeam,
  onCreateTeam
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    team_type: 'general' as const
  })
  const [createLoading, setCreateLoading] = useState(false)

  const getTeamTypeStyle = useCallback((teamType: string) => {
    const type = TEAM_TYPES.find(t => t.value === teamType)
    return type?.color || 'bg-gray-100 text-gray-800'
  }, [])

  const handleCreateSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createForm.name.trim() || !currentOrganization) return

    try {
      setCreateLoading(true)
      await onCreateTeam({
        organization_id: currentOrganization.id,
        name: createForm.name.trim(),
        description: createForm.description.trim() || undefined,
        team_type: createForm.team_type
      })
      
      setCreateForm({ name: '', description: '', team_type: 'general' })
      setShowCreateModal(false)
    } catch (error) {
      console.error('Failed to create team:', error)
    } finally {
      setCreateLoading(false)
    }
  }, [createForm, currentOrganization, onCreateTeam])

  if (!currentOrganization) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-center py-8 text-gray-500">
          <FiUsers className="mx-auto h-8 w-8 mb-2" />
          <p>Select an organization first</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-3"></div>
          <div className="h-8 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <FiUsers className="text-green-600" />
              Teams
            </h2>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 flex items-center gap-1"
            >
              <FiPlus className="w-3 h-3" />
              New
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            {currentOrganization.name}
          </p>
        </div>
        
        <div className="p-4">
          {teams.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FiUsers className="mx-auto h-8 w-8 mb-2" />
              <p>No teams found</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-2 text-green-600 hover:text-green-700 text-sm"
              >
                Create your first team
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {teams.map((team) => (
                <div
                  key={team.id}
                  onClick={() => onSelectTeam(team)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                    currentTeam?.id === team.id
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-gray-900">{team.name}</h3>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getTeamTypeStyle(team.team_type)}`}>
                          {TEAM_TYPES.find(t => t.value === team.team_type)?.label || team.team_type}
                        </span>
                      </div>
                      {team.description && (
                        <p className="text-sm text-gray-600">{team.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 text-sm text-gray-500">
                      <FiUser className="w-3 h-3" />
                      <span>{team.agent_count || 0} agents</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Team Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <FiUsers className="text-green-600" />
                Create Team
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                in {currentOrganization.name}
              </p>
            </div>
            
            <form onSubmit={handleCreateSubmit} className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Team Name *
                  </label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Enter team name"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Team Type
                  </label>
                  <select
                    value={createForm.team_type}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, team_type: e.target.value as any }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    {TEAM_TYPES.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description (Optional)
                  </label>
                  <textarea
                    value={createForm.description}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 h-20 focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="Describe your team"
                  />
                </div>
              </div>

              <div className="flex space-x-3 mt-6">
                <button
                  type="submit"
                  disabled={createLoading || !createForm.name.trim()}
                  className="flex-1 bg-green-600 text-white py-2 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {createLoading ? 'Creating...' : 'Create Team'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setCreateForm({ name: '', description: '', team_type: 'general' })
                  }}
                  className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-md hover:bg-gray-400 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
})

export default TeamSelector