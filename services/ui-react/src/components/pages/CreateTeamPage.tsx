import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../config/api'

export function CreateTeamPage() {
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)
  const [organizations, setOrganizations] = useState<any[]>([])
  const [selectedOrgId, setSelectedOrgId] = useState<string>('')
  const [error, setError] = useState<string>('')
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    type: 'development',
    color: '#2563eb'
  })

  useEffect(() => {
    loadOrganizations()
  }, [])

  const loadOrganizations = async () => {
    try {
      const orgs = await api.hierarchy.get('/organizations')
      setOrganizations(orgs)
      // Auto-select first organization if available
      if (orgs.length > 0) {
        setSelectedOrgId(orgs[0].id)
      }
    } catch (error) {
      console.error('Error loading organizations:', error)
      setError('Failed to load organizations')
    }
  }

  const teamTypes = [
    { id: 'executive', name: 'Executive', description: 'Leadership and strategic planning' },
    { id: 'development', name: 'Development', description: 'Software engineering and coding' },
    { id: 'qa', name: 'Quality Assurance', description: 'Testing and quality control' },
    { id: 'devops', name: 'DevOps', description: 'Infrastructure and deployment' },
    { id: 'business', name: 'Business', description: 'Marketing, sales, and operations' },
    { id: 'design', name: 'Design', description: 'UI/UX and creative work' },
    { id: 'data', name: 'Data', description: 'Analytics and data science' },
    { id: 'security', name: 'Security', description: 'Cybersecurity and compliance' }
  ]

  const teamColors = [
    '#2563eb', '#16a34a', '#dc2626', '#ea580c', '#7c3aed', '#0891b2', '#be123c', '#059669'
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError('')

    if (!selectedOrgId) {
      setError('Please select an organization')
      setCreating(false)
      return
    }

    try {
      // Create team data matching the backend API expectations
      const teamData = {
        organization_id: selectedOrgId,
        name: formData.name,
        description: formData.description,
        team_type: formData.type,
        settings: {
          mission: formData.description,
          category: formData.type,
          color: formData.color,
          // Add additional team settings based on type
          planned_agents: [],
          success_metrics: {},
          technical_stack: {},
          communication_channels: [`${formData.name.toLowerCase().replace(/\s+/g, '-')}-general`]
        }
      }

      const newTeam = await api.hierarchy.post('/teams', teamData)
      
      // Navigate to team details page with success message
      navigate(`/teams/${newTeam.id}?created=true`)
      
    } catch (error) {
      console.error('Error creating team:', error)
      setError(error instanceof Error ? error.message : 'Failed to create team. Please check your input and try again.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div style={{minHeight: '100vh', backgroundColor: '#f9fafb'}}>
      {/* Navigation */}
      <nav style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '0 1rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '4rem'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <Link to="/" style={{display: 'flex', alignItems: 'center', textDecoration: 'none'}}>
                <div style={{
                  width: '2rem', 
                  height: '2rem', 
                  backgroundColor: '#2563eb', 
                  borderRadius: '0.5rem', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  marginRight: '0.75rem'
                }}>
                  <span style={{color: 'white', fontWeight: 'bold'}}>F</span>
                </div>
                <h1 style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#111827'}}>FuzeAgent</h1>
              </Link>
              
              {/* Breadcrumbs */}
              <div style={{display: 'flex', alignItems: 'center', marginLeft: '1.5rem', color: '#6b7280', fontSize: '0.875rem'}}>
                <Link to="/teams" style={{color: '#6b7280', textDecoration: 'none'}}>Teams</Link>
                <span style={{margin: '0 0.5rem'}}>›</span>
                <span style={{color: '#111827'}}>Create Team</span>
              </div>
            </div>
            
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <Link to="/teams" style={{
                padding: '0.5rem 1rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                backgroundColor: 'white',
                textDecoration: 'none',
                color: '#374151'
              }}>
                Cancel
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main style={{maxWidth: '50rem', margin: '0 auto', padding: '2rem 1rem'}}>
        {/* Header */}
        <div style={{marginBottom: '2rem'}}>
          <h2 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827'}}>Create New Team</h2>
          <p style={{marginTop: '0.25rem', fontSize: '0.875rem', color: '#6b7280'}}>
            Organize agents into specialized teams for better collaboration
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', padding: '2rem'}}>
            <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem'}}>Team Information</h3>
            
            {/* Error Message */}
            {error && (
              <div style={{
                padding: '1rem',
                marginBottom: '1.5rem',
                backgroundColor: '#fee2e2',
                border: '1px solid #dc2626',
                borderRadius: '0.5rem',
                color: '#dc2626',
                fontSize: '0.875rem'
              }}>
                ❌ {error}
              </div>
            )}
            
            <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
              {/* Organization Selector */}
              <div>
                <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Organization *
                </label>
                <select
                  required
                  value={selectedOrgId}
                  onChange={(e) => setSelectedOrgId(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    backgroundColor: 'white'
                  }}
                >
                  <option value="">Select an organization</option>
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Team Name *
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  placeholder="e.g., Frontend Development Team"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem'
                  }}
                />
              </div>

              <div>
                <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Description *
                </label>
                <textarea
                  required
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  placeholder="Describe the team's purpose and responsibilities"
                  rows={3}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    resize: 'vertical'
                  }}
                />
              </div>

              <div>
                <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Team Type *
                </label>
                <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '0.75rem'}}>
                  {teamTypes.map(type => (
                    <label 
                      key={type.id}
                      style={{
                        display: 'flex',
                        alignItems: 'start',
                        padding: '1rem',
                        border: formData.type === type.id ? '2px solid #2563eb' : '1px solid #d1d5db',
                        borderRadius: '0.5rem',
                        cursor: 'pointer',
                        backgroundColor: formData.type === type.id ? '#f0f9ff' : 'white'
                      }}
                    >
                      <input
                        type="radio"
                        name="type"
                        value={type.id}
                        checked={formData.type === type.id}
                        onChange={(e) => setFormData({...formData, type: e.target.value})}
                        style={{marginRight: '0.75rem', marginTop: '0.125rem'}}
                      />
                      <div>
                        <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', marginBottom: '0.25rem'}}>
                          {type.name}
                        </div>
                        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>
                          {type.description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Team Color
                </label>
                <div style={{display: 'flex', gap: '0.5rem', marginBottom: '0.5rem'}}>
                  {teamColors.map(color => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => setFormData({...formData, color})}
                      style={{
                        width: '2.5rem',
                        height: '2.5rem',
                        backgroundColor: color,
                        borderRadius: '50%',
                        border: formData.color === color ? '3px solid #111827' : '2px solid #e5e7eb',
                        cursor: 'pointer'
                      }}
                    />
                  ))}
                </div>
                <input
                  type="color"
                  value={formData.color}
                  onChange={(e) => setFormData({...formData, color: e.target.value})}
                  style={{
                    width: '3rem',
                    height: '2rem',
                    border: 'none',
                    borderRadius: '0.25rem',
                    cursor: 'pointer'
                  }}
                />
              </div>
            </div>

            {/* Preview */}
            <div style={{marginTop: '2rem', padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem'}}>
              <h4 style={{fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.75rem'}}>
                Preview
              </h4>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: '1rem',
                backgroundColor: 'white',
                borderRadius: '0.5rem',
                border: '1px solid #e5e7eb'
              }}>
                <div style={{
                  width: '3rem',
                  height: '3rem',
                  backgroundColor: formData.color + '20',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: '1rem'
                }}>
                  <span style={{fontSize: '1.5rem', color: formData.color}}>👥</span>
                </div>
                <div>
                  <div style={{fontSize: '1rem', fontWeight: '600', color: '#111827'}}>
                    {formData.name || 'Team Name'}
                  </div>
                  <div style={{fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem'}}>
                    {formData.description || 'Team description will appear here'}
                  </div>
                  <div style={{
                    fontSize: '0.75rem',
                    fontWeight: '500',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '0.25rem',
                    backgroundColor: formData.color + '20',
                    color: formData.color,
                    display: 'inline-block',
                    marginTop: '0.5rem'
                  }}>
                    {teamTypes.find(t => t.id === formData.type)?.name || 'Development'}
                  </div>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <div style={{marginTop: '2rem', display: 'flex', justifyContent: 'end', gap: '0.5rem'}}>
              <Link to="/teams" style={{
                padding: '0.75rem 1.5rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                backgroundColor: 'white',
                textDecoration: 'none',
                color: '#374151'
              }}>
                Cancel
              </Link>
              <button
                type="submit"
                disabled={creating || !formData.name || !formData.description || !selectedOrgId}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: creating || !formData.name || !formData.description || !selectedOrgId ? '#9ca3af' : '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  cursor: creating || !formData.name || !formData.description || !selectedOrgId ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                {creating && <span style={{animation: 'spin 1s linear infinite'}}>⏳</span>}
                {creating ? 'Creating Team...' : 'Create Team'}
              </button>
            </div>
          </div>
        </form>
      </main>

      {/* CSS Animations */}
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  )
}