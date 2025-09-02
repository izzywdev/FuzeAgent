import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Building2, 
  Plus, 
  ArrowRight, 
  Users, 
  Bot, 
  BarChart3, 
  Zap,
  CheckCircle,
  Star,
  Globe
} from 'lucide-react'
import { useOrganization } from '../../contexts/OrganizationContext'
import { useApiService } from '../../hooks/useApiService'

interface Organization {
  id: string
  name: string
  description?: string
  created_at: string
  team_count?: number
  agent_count?: number
}

interface CreateOrganizationData {
  name: string
  description: string
  industry: string
  size: string
  founded: string
  website: string
}

/**
 * LandingPage - Main entry point for the FuzeAgent application
 * 
 * Provides organization selection and creation functionality with a modern,
 * welcoming interface. Users can switch between existing organizations or
 * create new ones without authentication.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */
export function LandingPage() {
  const navigate = useNavigate()
  const { selectOrganization } = useOrganization()
  const apiService = useApiService()
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createData, setCreateData] = useState<CreateOrganizationData>({
    name: '',
    description: '',
    industry: '',
    size: '',
    founded: '',
    website: ''
  })
  const [error, setError] = useState<string>('')

  // Load organizations on component mount
  useEffect(() => {
    loadOrganizations()
  }, [])

  const loadOrganizations = async () => {
    try {
      setLoading(true)
      const response = await apiService.getOrganizations()
      if (response.ok) {
        setOrganizations(Array.isArray(response.data) ? response.data : [])
      } else {
        console.error('Failed to load organizations:', response.status)
        setOrganizations([])
      }
    } catch (error) {
      console.error('Error loading organizations:', error)
      setOrganizations([])
    } finally {
      setLoading(false)
    }
  }

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
        setOrganizations(prev => [...prev, response.data])
        setShowCreateModal(false)
        setCreateData({ name: '', description: '', industry: '', size: '', founded: '', website: '' })
        
        // Navigate to the new organization
        navigateToOrganization(response.data.id)
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

  const navigateToOrganization = (orgId: string) => {
    // Select organization in context (this also updates localStorage)
    selectOrganization(orgId)
    // Navigate to dashboard
    navigate('/')
  }

  const handleSelectOrganization = (org: Organization) => {
    navigateToOrganization(org.id)
  }

  const features = [
    {
      icon: Bot,
      title: 'AI Agents',
      description: 'Deploy intelligent agents that work autonomously on your tasks'
    },
    {
      icon: Users,
      title: 'Team Management',
      description: 'Organize agents into teams with specialized roles and responsibilities'
    },
    {
      icon: BarChart3,
      title: 'Analytics',
      description: 'Track performance and get insights into your AI workforce'
    },
    {
      icon: Zap,
      title: 'Automation',
      description: 'Streamline workflows with powerful automation capabilities'
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">F</span>
              </div>
              <h1 className="text-xl font-bold text-gray-900">FuzeAgent</h1>
            </div>
            <div className="text-sm text-gray-500">
              AI Team Management Platform
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
            Welcome to{' '}
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              FuzeAgent
            </span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Manage your AI workforce with intelligent agents, organized teams, and powerful automation. 
            Choose an organization to get started or create a new one.
          </p>
        </div>

        {/* Organization Selection */}
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-8">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  Select Organization
                </h2>
                <p className="text-gray-600">
                  Choose an existing organization or create a new one to begin
                </p>
              </div>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                <Plus className="w-5 h-5" />
                <span>Create New</span>
              </button>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-3 text-gray-600">Loading organizations...</span>
              </div>
            ) : organizations.length === 0 ? (
              <div className="text-center py-12">
                <Building2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  No organizations found
                </h3>
                <p className="text-gray-600 mb-6">
                  Create your first organization to get started with FuzeAgent
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all duration-200"
                >
                  <Plus className="w-5 h-5" />
                  <span>Create Organization</span>
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {organizations.map((org) => (
                  <div
                    key={org.id}
                    onClick={() => handleSelectOrganization(org)}
                    className="group cursor-pointer bg-gray-50 hover:bg-gray-100 rounded-xl p-6 border border-gray-200 hover:border-blue-300 transition-all duration-200 hover:shadow-lg"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                        <Building2 className="w-6 h-6 text-white" />
                      </div>
                      <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                      {org.name}
                    </h3>
                    {org.description && (
                      <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                        {org.description}
                      </p>
                    )}
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <div className="flex items-center space-x-1">
                        <Users className="w-4 h-4" />
                        <span>{org.team_count || 0} teams</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Bot className="w-4 h-4" />
                        <span>{org.agent_count || 0} agents</span>
                      </div>
                    </div>
                    <div className="mt-4 text-xs text-gray-400">
                      Created {new Date(org.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Features Section */}
        <div className="mt-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Powerful AI Team Management
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Everything you need to build, manage, and scale your AI workforce
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="text-center">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <feature.icon className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 text-sm">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-20 text-center">
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-8 text-white">
            <h2 className="text-2xl font-bold mb-4">
              Ready to get started?
            </h2>
            <p className="text-blue-100 mb-6 max-w-2xl mx-auto">
              Join thousands of teams already using FuzeAgent to manage their AI workforce. 
              Create your organization and start building intelligent teams today.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center space-x-2 bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
            >
              <Plus className="w-5 h-5" />
              <span>Create Your Organization</span>
            </button>
          </div>
        </div>
      </main>

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
                      placeholder="e.g., Technology, Healthcare, Finance"
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
                      <span>Create Organization</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
