import React, { useState, useCallback } from 'react'
import { FiHome, FiPlus, FiSettings, FiUsers, FiLock, FiUser } from 'react-icons/fi'
import { useOrgContext } from '../context/OrgContext'
import type { Organization, OrganizationCreate } from '../types'

interface OrganizationSelectorProps {
  organizations: Organization[]
  currentOrganization: Organization | null
  loading: boolean
  onSelectOrganization: (org: Organization) => void
  onCreateOrganization: (orgData: OrganizationCreate) => Promise<void>
}

const OrganizationSelector: React.FC<OrganizationSelectorProps> = React.memo(({
  organizations,
  currentOrganization,
  loading,
  onSelectOrganization,
  onCreateOrganization
}) => {
  const { allowInAppOrgManagement, isPersonal, user: orgUser, activeOrg } = useOrgContext()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({
    name: '',
    description: ''
  })
  const [createLoading, setCreateLoading] = useState(false)

  const handleCreateSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createForm.name.trim()) return

    try {
      setCreateLoading(true)
      await onCreateOrganization({
        name: createForm.name.trim(),
        description: createForm.description.trim() || undefined
      })
      
      setCreateForm({ name: '', description: '' })
      setShowCreateModal(false)
    } catch (error) {
      console.error('Failed to create organization:', error)
    } finally {
      setCreateLoading(false)
    }
  }, [createForm, onCreateOrganization])

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
          <div className="h-4 rounded w-1/3 mb-3" style={{ backgroundColor: 'var(--border-color, #232c3d)' }}></div>
          <div className="h-8 rounded" style={{ backgroundColor: 'var(--border-color, #232c3d)' }}></div>
        </div>
      </div>
    )
  }

  // Platform mode: in-app org creation and switcher are killed via Unleash kill switch
  if (!allowInAppOrgManagement) {
    return (
      <div 
        className="rounded-xl border shadow-sm p-5 space-y-3"
        style={{
          backgroundColor: 'var(--bg-tertiary, #141a26)',
          borderColor: 'var(--border-color, #232c3d)',
          color: 'var(--text-primary, #e7ecf5)'
        }}
      >
        <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: 'var(--border-color, #232c3d)' }}>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg border text-indigo-400" style={{ backgroundColor: 'rgba(110, 92, 255, 0.15)', borderColor: 'rgba(110, 92, 255, 0.3)' }}>
              <FiHome />
            </span>
            <h2 className="text-sm font-bold tracking-tight">Active Organization Context</h2>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded-full border" style={{ backgroundColor: 'var(--bg-secondary, #0b0e15)', borderColor: 'var(--border-color, #232c3d)', color: 'var(--text-secondary, #9fa9bc)' }}>
            <FiLock className="w-3 h-3 text-amber-400" />
            <span>Portal Controlled</span>
          </div>
        </div>

        <div className="p-3.5 rounded-lg border" style={{ backgroundColor: 'var(--bg-secondary, #0b0e15)', borderColor: 'var(--border-color, #232c3d)' }}>
          {isPersonal || !activeOrg ? (
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 font-bold text-cyan-400 text-sm">
                  <FiUser />
                  <span>Personal Account Context</span>
                </div>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                  {orgUser?.email || 'Individual user workspace'}. Operating in personal developer sandbox.
                </p>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded" style={{ backgroundColor: 'rgba(41, 211, 230, 0.15)', color: '#29d3e6' }}>
                Personal
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2 font-bold text-indigo-300 text-sm">
                  <FiHome />
                  <span>{activeOrg.name}</span>
                </div>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                  Organization ID: <span className="font-mono">{activeOrg.id}</span>
                </p>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded" style={{ backgroundColor: 'rgba(110, 92, 255, 0.2)', color: '#a78bfa' }}>
                {activeOrg.tier || 'Enterprise'}
              </span>
            </div>
          )}
        </div>

        <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-tertiary, #66718a)' }}>
          🔒 Organization switching and creation are centralized in the FuzeFront portal shell (Unleash kill switch <code>fuzeagent.in-app-org-management: false</code>).
        </p>
      </div>
    )
  }

  // Standalone dev mode: allow in-app org management
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
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <FiHome className="text-indigo-400" />
            Organization
          </h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-1 rounded text-xs font-medium text-white flex items-center gap-1 transition-all"
            style={{ backgroundColor: 'var(--accent-color, #6e5cff)' }}
          >
            <FiPlus className="w-3 h-3" />
            New
          </button>
        </div>
        
        <div className="p-4">
          {organizations.length === 0 ? (
            <div className="text-center py-6" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
              <FiHome className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p className="text-xs">No organizations found</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-2 text-indigo-400 hover:underline text-xs"
              >
                Create your first organization
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {organizations.map((org) => {
                const isSelected = currentOrganization?.id === org.id
                return (
                  <div
                    key={org.id}
                    onClick={() => onSelectOrganization(org)}
                    className="p-3 rounded-lg border cursor-pointer transition-all"
                    style={{
                      backgroundColor: isSelected ? 'rgba(110, 92, 255, 0.15)' : 'var(--bg-secondary, #0b0e15)',
                      borderColor: isSelected ? 'var(--accent-color, #6e5cff)' : 'var(--border-color, #232c3d)'
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium text-xs text-white">{org.name}</h3>
                        {org.description && (
                          <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>{org.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-[11px]" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>
                        <div className="flex items-center gap-1">
                          <FiUsers className="w-3 h-3" />
                          <span>{org.team_count || 0} teams</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <FiSettings className="w-3 h-3" />
                          <span>{org.agent_count || 0} agents</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

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
            <h3 className="text-base font-bold">Create Organization</h3>
            <form onSubmit={handleCreateSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>Organization Name</label>
                <input
                  type="text"
                  required
                  value={createForm.name}
                  onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border text-xs"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)',
                    color: 'var(--text-primary, #e7ecf5)'
                  }}
                  placeholder="e.g. Acme Corp"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary, #9fa9bc)' }}>Description</label>
                <textarea
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border text-xs"
                  style={{
                    backgroundColor: 'var(--bg-tertiary, #141a26)',
                    borderColor: 'var(--border-color, #232c3d)',
                    color: 'var(--text-primary, #e7ecf5)'
                  }}
                  placeholder="Optional description"
                  rows={3}
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
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
                  disabled={createLoading}
                  className="px-4 py-1.5 rounded-lg text-xs font-medium text-white shadow"
                  style={{ backgroundColor: 'var(--accent-color, #6e5cff)' }}
                >
                  {createLoading ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
})

export default OrganizationSelector