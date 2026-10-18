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
  { value: 'general', label: 'General', color: 'rgba(110, 92, 255, 0.15)', text: '#a78bfa' },
  { value: 'development', label: 'Development', color: 'rgba(52, 211, 153, 0.15)', text: '#34d399' },
  { value: 'qa', label: 'QA', color: 'rgba(245, 166, 35, 0.15)', text: '#f5a623' },
  { value: 'design', label: 'Design', color: 'rgba(168, 85, 247, 0.15)', text: '#c084fc' },
  { value: 'management', label: 'Management', color: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa' }
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
      <div 
        className="rounded-xl border p-5 shadow-sm text-center"
        style={{
          backgroundColor: 'var(--bg-tertiary, #141a26)',
          borderColor: 'var(--border-color, #232c3d)',
          color: 'var(--text-secondary, #9fa9bc)'
        }}
      >
        <FiUsers className="mx-auto h-8 w-8 mb-2 opacity-40 text-emerald-400" />
        <p className="text-xs font-medium">Select an organization to view and manage squads</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div 
        className="rounded-xl border p-4 shadow-sm"
        style={{
          backgroundColor: 'var(--bg-tertiary, #141a26)',
          borderColor: 'var(--border-color, #232c3d)'
        }}
      >
        <div className="animate-pulse">
          <div className="h-4 rounded w-1/4 mb-3" style={{ backgroundColor: 'var(--border-color, #232c3d)' }}></div>
          <div className="h-8 rounded" style={{ backgroundColor: 'var(--border-color, #232c3d)' }}></div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div 
        className="rounded-xl border shadow-sm"
        style={{
          backgroundColor: 'var(--bg-tertiary, #141a26)',
          borderColor: 'var(--border-color, #232c3d)',
          color: 'var(--text-primary, #e7ecf5)'
        }}
      >
        <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--border-color, #232c3d)' }}>
          <div>
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <FiUsers className="text-emerald-400" />
              Teams & Squads
            </h2>
            <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
              In {currentOrganization.name}
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-1 rounded text-xs font-medium text-white flex items-center gap-1 transition-all"
            style={{ backgroundColor: 'var(--accent-color, #6e5cff)' }}
          >
            <FiPlus className="w-3 h-3" />
            New Squad
          </button>
        </div>
        
        <div className="p-4">
          {teams.length === 0 ? (
            <div className="text-center py-6" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
              <FiUsers className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p className="text-xs">No teams configured in this organization</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-2 text-indigo-400 hover:underline text-xs"
              >
                Create your first squad
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {teams.map((team) => {
                const isSelected = currentTeam?.id === team.id
                const typeConfig = TEAM_TYPES.find(t => t.value === team.team_type) || TEAM_TYPES[0]
                return (
                  <div
                    key={team.id}
                    onClick={() => onSelectTeam(team)}
                    className="p-3 rounded-lg border cursor-pointer transition-all"
                    style={{
                      backgroundColor: isSelected ? 'rgba(52, 211, 153, 0.12)' : 'var(--bg-secondary, #0b0e15)',
                      borderColor: isSelected ? 'var(--success-color, #34d399)' : 'var(--border-color, #232c3d)'
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium text-xs text-white">{team.name}</h3>
                          <span 
                            className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                            style={{ backgroundColor: typeConfig.color, color: typeConfig.text }}
                          >
                            {typeConfig.label}
                          </span>
                        </div>
                        {team.description && (
                          <p className="text-[11px]" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>{team.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-1 text-[11px]" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                        <FiUser className="w-3 h-3 text-slate-400" />
                        <span>{team.agent_count || 0} agents</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Create Team Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div 
            className="rounded-xl border max-w-md w-full p-6 shadow-2xl space-y-4"
            style={{
              backgroundColor: 'var(--bg-secondary, #0b0e15)',
              borderColor: 'var(--border-color, #232c3d)',
              color: 'var(--text-primary, #e7ecf5)'
            }}
          >
            <div>
              <h2 className="text-base font-bold flex items-center gap-2">
                <FiUsers className="text-emerald-400" />
                Create Squad
              </h2>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                Target organization: <strong className="text-indigo-300">{currentOrganization.name}</strong>
              </p>
            </div>
            
            <form onSubmit={handleCreateSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                  Squad Name *
                </label>
                <input
                  type="text"
                  value={createForm.name}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border text-xs"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)',
                    color: 'var(--text-primary, #e7ecf5)'
                  }}
                  placeholder="e.g. Core Engineering"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                  Team Type
                </label>
                <select
                  value={createForm.team_type}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, team_type: e.target.value as any }))}
                  className="w-full px-3 py-2 rounded-lg border text-xs"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)',
                    color: 'var(--text-primary, #e7ecf5)'
                  }}
                >
                  {TEAM_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                  Description (Optional)
                </label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border text-xs"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)',
                    color: 'var(--text-primary, #e7ecf5)'
                  }}
                  placeholder="Describe this squad's responsibilities"
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setCreateForm({ name: '', description: '', team_type: 'general' })
                  }}
                  className="px-3 py-1.5 rounded-lg border text-xs"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)',
                    color: 'var(--text-secondary, #9fa9bc)'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading || !createForm.name.trim()}
                  className="px-4 py-1.5 rounded-lg text-xs font-medium text-white shadow disabled:opacity-50"
                  style={{ backgroundColor: 'var(--accent-color, #6e5cff)' }}
                >
                  {createLoading ? 'Creating...' : 'Create Squad'}
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