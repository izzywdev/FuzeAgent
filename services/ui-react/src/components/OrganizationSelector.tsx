import React, { useState, useCallback } from 'react'
import { FiHome, FiPlus, FiSettings, FiUsers } from 'react-icons/fi'
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
      <div className="bg-white rounded-lg shadow p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-3"></div>
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
              <FiHome className="text-blue-600" />
              Organization
            </h2>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 flex items-center gap-1"
            >
              <FiPlus className="w-3 h-3" />
              New
            </button>
          </div>
        </div>
        
        <div className="p-4">
          {organizations.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FiHome className="mx-auto h-8 w-8 mb-2" />
              <p>No organizations found</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-2 text-blue-600 hover:text-blue-700 text-sm"
              >
                Create your first organization
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {organizations.map((org) => (
                <div
                  key={org.id}
                  onClick={() => onSelectOrganization(org)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
                    currentOrganization?.id === org.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium text-gray-900">{org.name}</h3>
                      {org.description && (
                        <p className="text-sm text-gray-600 mt-1">{org.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
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
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg max-w-md w-full mx-4">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <FiHome className="text-blue-600" />
                Create Organization
              </h2>
            </div>
            
            <form onSubmit={handleCreateSubmit} className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Organization Name *
                  </label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Enter organization name"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description (Optional)
                  </label>
                  <textarea
                    value={createForm.description}
                    onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 h-20 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Describe your organization"
                  />
                </div>
              </div>

              <div className="flex space-x-3 mt-6">
                <button
                  type="submit"
                  disabled={createLoading || !createForm.name.trim()}
                  className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {createLoading ? 'Creating...' : 'Create Organization'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setCreateForm({ name: '', description: '' })
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

export default OrganizationSelector