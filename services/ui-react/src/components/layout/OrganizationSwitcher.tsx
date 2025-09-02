import { useState, useRef, useEffect } from 'react'
import { Building2, ChevronDown, Plus, LogOut, Check } from 'lucide-react'
import { useOrganization } from '../../contexts/OrganizationContext'
import { useNavigate } from 'react-router-dom'
import { useApiService } from '../../hooks/useApiService'

/**
 * OrganizationSwitcher - Component for switching between organizations
 * 
 * Provides a dropdown interface in the sidebar to switch between organizations
 * or create new ones. Shows the current organization and allows quick switching.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */
export function OrganizationSwitcher() {
  const { currentOrganization, organizations, selectOrganization, clearOrganization } = useOrganization()
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createData, setCreateData] = useState({ 
    name: '', 
    description: '', 
    industry: '', 
    size: '', 
    founded: '', 
    website: '' 
  })
  const [error, setError] = useState<string>('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const handleCreateOrganization = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!createData.name.trim()) {
      setError('Organization name is required')
      return
    }

    setCreating(true)
    setError('')

    try {
      const response = await apiService.createOrganization({
        name: createData.name.trim(),
        description: createData.description.trim() || undefined,
        industry: createData.industry.trim() || undefined,
        size: createData.size.trim() || undefined,
        founded: createData.founded.trim() || undefined,
        website: createData.website.trim() || undefined
      })

      if (response.ok) {
        selectOrganization(response.data.id)
        setShowCreateModal(false)
        setCreateData({ name: '', description: '', industry: '', size: '', founded: '', website: '' })
        setIsOpen(false)
      } else {
        setError(`Failed to create organization: HTTP ${response.status}`)
      }
    } catch (error) {
      console.error('Error creating organization:', error)
      setError('Network error. Please try again.')
    } finally {
      setCreating(false)
    }
  }

  const handleSwitchOrganization = (orgId: string) => {
    selectOrganization(orgId)
    setIsOpen(false)
  }

  const handleLogout = () => {
    clearOrganization()
    setIsOpen(false)
    navigate('/landing')
  }

  if (!currentOrganization) {
    return null
  }

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50 rounded-lg transition-colors"
        >
          <div className="flex items-center space-x-3 min-w-0 flex-1">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center flex-shrink-0">
              <Building2 className="w-4 h-4 text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-gray-900 truncate">
                {currentOrganization.name}
              </div>
              <div className="text-xs text-gray-500 truncate">
                {currentOrganization.team_count || 0} teams • {currentOrganization.agent_count || 0} agents
              </div>
            </div>
          </div>
          <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto">
            <div className="p-2">
              <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Organizations
              </div>
              
              {organizations.map((org) => (
                <button
                  key={org.id}
                  onClick={() => handleSwitchOrganization(org.id)}
                  className={`w-full flex items-center space-x-3 p-2 rounded-md hover:bg-gray-50 transition-colors ${
                    org.id === currentOrganization.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="w-6 h-6 bg-gradient-to-r from-blue-500 to-purple-500 rounded flex items-center justify-center flex-shrink-0">
                    <Building2 className="w-3 h-3 text-white" />
                  </div>
                  <div className="min-w-0 flex-1 text-left">
                    <div className="text-sm font-medium text-gray-900 truncate">
                      {org.name}
                    </div>
                    <div className="text-xs text-gray-500 truncate">
                      {org.team_count || 0} teams • {org.agent_count || 0} agents
                    </div>
                  </div>
                  {org.id === currentOrganization.id && (
                    <Check className="w-4 h-4 text-blue-600 flex-shrink-0" />
                  )}
                </button>
              ))}

              <div className="border-t border-gray-200 my-2"></div>

              <button
                onClick={() => setShowCreateModal(true)}
                className="w-full flex items-center space-x-3 p-2 rounded-md hover:bg-gray-50 transition-colors"
              >
                <div className="w-6 h-6 bg-gray-100 rounded flex items-center justify-center flex-shrink-0">
                  <Plus className="w-3 h-3 text-gray-600" />
                </div>
                <span className="text-sm font-medium text-gray-700">Create Organization</span>
              </button>

              <button
                onClick={handleLogout}
                className="w-full flex items-center space-x-3 p-2 rounded-md hover:bg-gray-50 transition-colors"
              >
                <div className="w-6 h-6 bg-gray-100 rounded flex items-center justify-center flex-shrink-0">
                  <LogOut className="w-3 h-3 text-gray-600" />
                </div>
                <span className="text-sm font-medium text-gray-700">Switch Organization</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Organization Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900">
                Create New Organization
              </h3>
              <button
                onClick={() => {
                  setShowCreateModal(false)
                  setError('')
                  setCreateData({ name: '', description: '', industry: '', size: '', founded: '', website: '' })
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <span className="sr-only">Close</span>
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreateOrganization}>
              <div className="space-y-4">
                <div>
                  <label htmlFor="org-name" className="block text-sm font-medium text-gray-700 mb-2">
                    Organization Name *
                  </label>
                  <input
                    type="text"
                    id="org-name"
                    value={createData.name}
                    onChange={(e) => setCreateData({ ...createData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter organization name"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="org-description" className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <textarea
                    id="org-description"
                    value={createData.description}
                    onChange={(e) => setCreateData({ ...createData, description: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Describe your organization (optional)"
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="org-industry" className="block text-sm font-medium text-gray-700 mb-2">
                      Industry
                    </label>
                    <input
                      type="text"
                      id="org-industry"
                      value={createData.industry}
                      onChange={(e) => setCreateData({ ...createData, industry: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="e.g., Technology, Healthcare"
                    />
                  </div>
                  <div>
                    <label htmlFor="org-size" className="block text-sm font-medium text-gray-700 mb-2">
                      Company Size
                    </label>
                    <select
                      id="org-size"
                      value={createData.size}
                      onChange={(e) => setCreateData({ ...createData, size: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      <option value="">Select size</option>
                      <option value="1-10 employees">1-10 employees</option>
                      <option value="10-50 employees">10-50 employees</option>
                      <option value="50-200 employees">50-200 employees</option>
                      <option value="200+ employees">200+ employees</option>
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="org-founded" className="block text-sm font-medium text-gray-700 mb-2">
                      Founded Year
                    </label>
                    <input
                      type="text"
                      id="org-founded"
                      value={createData.founded}
                      onChange={(e) => setCreateData({ ...createData, founded: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="e.g., 2020"
                    />
                  </div>
                  <div>
                    <label htmlFor="org-website" className="block text-sm font-medium text-gray-700 mb-2">
                      Website
                    </label>
                    <input
                      type="url"
                      id="org-website"
                      value={createData.website}
                      onChange={(e) => setCreateData({ ...createData, website: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="https://yourcompany.com"
                    />
                  </div>
                </div>
              </div>

              {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className="flex space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setError('')
                    setCreateData({ name: '', description: '', industry: '', size: '', founded: '', website: '' })
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating || !createData.name.trim()}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center space-x-2"
                >
                  {creating ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Creating...</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      <span>Create</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
