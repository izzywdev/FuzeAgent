import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ErrorBoundary from '../ErrorBoundary'

interface Team {
  id: string
  name: string
  description: string
  members: string[]
  status: string
  color: string
  team_type?: string
}

interface ApiTeamsResponse {
  teams?: Team[]
}

// Type guard to check if a team object is valid
const isValidTeam = (team: any): team is Team => {
  return (
    team &&
    typeof team.id === 'string' &&
    typeof team.name === 'string' &&
    typeof team.description === 'string' &&
    Array.isArray(team.members) &&
    typeof team.status === 'string' &&
    typeof team.color === 'string'
  )
}

// Normalize team data to ensure consistent structure
const normalizeTeam = (team: any): Team => {
  return {
    id: team?.id || '',
    name: team?.name || 'Unknown Team',
    description: team?.description || 'No description available',
    members: Array.isArray(team?.members) ? team.members : [],
    status: team?.status || 'inactive',
    color: team?.color || '#6b7280',
    team_type: team?.team_type || 'general'
  }
}

const mockTeams: Team[] = [
  {
    id: '1',
    name: 'Executive Team',
    description: 'Strategic leadership and decision making',
    members: ['IzzyAI CEO', 'Alex CTO', 'Sarah CPO'],
    status: 'active',
    color: '#7c3aed',
    team_type: 'executive'
  },
  {
    id: '2', 
    name: 'Development Team',
    description: 'Frontend, backend, and full-stack development',
    members: ['React Developer', 'Python Developer', 'TypeScript Developer'],
    status: 'active',
    color: '#2563eb',
    team_type: 'development'
  },
  {
    id: '3',
    name: 'Quality Assurance',
    description: 'Testing, quality control, and bug detection',
    members: ['QA Engineer'],
    status: 'active',
    color: '#16a34a',
    team_type: 'qa'
  },
  {
    id: '4',
    name: 'DevOps Team',
    description: 'Infrastructure, deployment, and system operations',
    members: ['DevOps Engineer'],
    status: 'active',
    color: '#ea580c',
    team_type: 'devops'
  },
  {
    id: '5',
    name: 'Business Team',
    description: 'Marketing, sales, and customer relations',
    members: ['Marketing Agent', 'Sales Agent'],
    status: 'active',
    color: '#dc2626',
    team_type: 'business'
  }
]

function FixedTeamsPageCore() {
  const [teams, setTeams] = useState<Team[]>([])
  const [filteredTeams, setFilteredTeams] = useState<Team[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const navigate = useNavigate()

  // Filter teams based on search term and type - with defensive programming
  useEffect(() => {
    // Ensure teams is always an array
    const safeTeams = Array.isArray(teams) ? teams : []
    let filtered = safeTeams

    if (searchTerm && searchTerm.trim()) {
      filtered = filtered.filter(team => {
        const name = team?.name || ''
        const description = team?.description || ''
        const searchLower = searchTerm.toLowerCase()
        return (
          name.toLowerCase().includes(searchLower) ||
          description.toLowerCase().includes(searchLower)
        )
      })
    }

    if (typeFilter && typeFilter.trim()) {
      filtered = filtered.filter(team => team?.team_type === typeFilter)
    }

    setFilteredTeams(filtered)
  }, [teams, searchTerm, typeFilter])

  useEffect(() => {
    const loadTeams = async () => {
      try {
        setLoading(true)
        setError(null)
        
        console.log('Fetching teams from API...')
        const response = await fetch('http://localhost:8006/teams')
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        
        const data = await response.json()
        console.log('API response:', data)
        
        // Handle different response structures
        let teamData: Team[]
        
        if (Array.isArray(data)) {
          // Direct array response
          teamData = data
        } else if (data && Array.isArray(data.teams)) {
          // Object with teams property
          teamData = data.teams
        } else if (data && typeof data === 'object') {
          // Single team object or other structure
          teamData = Object.values(data).filter(item => 
            item && typeof item === 'object' && 'id' in item
          ) as Team[]
        } else {
          // Unexpected format
          console.warn('Unexpected API response format:', data)
          teamData = []
        }
        
        // Validate and normalize team data
        const validatedTeams = teamData
          .map(team => {
            if (isValidTeam(team)) {
              return team
            } else {
              console.warn('Invalid team data, normalizing:', team)
              return normalizeTeam(team)
            }
          })
          .filter(team => team.id) // Remove teams without IDs
        
        console.log('Processed teams:', validatedTeams)
        setTeams(validatedTeams)
        setFilteredTeams(validatedTeams)
        
      } catch (err) {
        console.error('Failed to load teams:', err)
        setError(err instanceof Error ? err.message : 'Failed to load teams')
        
        // Use mock data as fallback
        console.log('Using mock data as fallback')
        setTeams(mockTeams)
        setFilteredTeams(mockTeams)
        
      } finally {
        setLoading(false)
      }
    }

    loadTeams()

    // Cleanup function to prevent state updates on unmounted component
    return () => {
      setLoading(false)
    }
  }, [])

  const handleCreateTeam = () => {
    navigate('/teams/create')
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
              
              {/* Navigation Links */}
              <div style={{display: 'flex', marginLeft: '1.5rem', gap: '2rem'}}>
                <Link to="/" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Dashboard
                </Link>
                <Link to="/agents" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Agents
                </Link>
                <Link to="/teams" style={{color: '#2563eb', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none', borderBottom: '2px solid #2563eb', paddingBottom: '1rem'}}>
                  Teams
                </Link>
                <Link to="/goals" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Goals
                </Link>
                <Link to="/organization-chart" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Organization Chart
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main style={{maxWidth: '80rem', margin: '0 auto', padding: '1.5rem 1rem'}}>
        {/* Header */}
        <div style={{marginBottom: '2rem'}}>
          <h2 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827'}}>Teams</h2>
          <p style={{marginTop: '0.25rem', fontSize: '0.875rem', color: '#6b7280'}}>
            Organize agents into specialized teams for better collaboration
          </p>
        </div>

        {/* Actions Bar */}
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem'}}>
          <div style={{display: 'flex', gap: '1rem'}}>
            <input
              type="text"
              placeholder="Search teams..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                padding: '0.5rem 0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                width: '20rem'
              }}
            />
            <select 
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              style={{
                padding: '0.5rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem'
              }}
            >
              <option value="">All Types</option>
              <option value="executive">Executive</option>
              <option value="development">Development</option>
              <option value="qa">Quality Assurance</option>
              <option value="devops">DevOps</option>
              <option value="business">Business</option>
              <option value="design">Design</option>
            </select>
          </div>
          <button 
            onClick={handleCreateTeam}
            style={{
              backgroundColor: '#2563eb',
              color: 'white',
              padding: '0.5rem 1rem',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              fontWeight: '500',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            + Create Team
          </button>
        </div>

        {/* Search Results Info */}
        {!loading && (
          <div style={{marginBottom: '1rem', color: '#6b7280', fontSize: '0.875rem'}}>
            {searchTerm || typeFilter ? (
              <span>
                Found {(filteredTeams || []).length} of {(teams || []).length} teams
                {searchTerm && ` matching "${searchTerm}"`}
                {typeFilter && ` of type "${typeFilter}"`}
                {(searchTerm || typeFilter) && (
                  <button 
                    onClick={() => {setSearchTerm(''); setTypeFilter('')}}
                    style={{
                      marginLeft: '0.5rem',
                      color: '#2563eb',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      textDecoration: 'underline'
                    }}
                  >
                    Clear filters
                  </button>
                )}
              </span>
            ) : (
              <span>Showing all {(teams || []).length} teams</span>
            )}
          </div>
        )}
        
        {/* Error Display */}
        {error && !loading && (
          <div style={{
            marginBottom: '1rem', 
            padding: '1rem',
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '0.5rem',
            color: '#dc2626'
          }}>
            <h3 style={{margin: '0 0 0.5rem 0', fontSize: '0.875rem', fontWeight: '600'}}>
              ⚠️ Loading Error
            </h3>
            <p style={{margin: 0, fontSize: '0.75rem'}}>
              {error}. Using cached data as fallback.
            </p>
          </div>
        )}

        {/* Teams Grid */}
        {loading ? (
          <div style={{textAlign: 'center', padding: '3rem'}}>
            <p style={{color: '#6b7280'}}>Loading teams...</p>
          </div>
        ) : !Array.isArray(filteredTeams) || filteredTeams.length === 0 ? (
          <div style={{textAlign: 'center', padding: '3rem'}}>
            {!Array.isArray(teams) || teams.length === 0 ? (
              <div>
                <p style={{color: '#6b7280'}}>No teams found</p>
                {error && (
                  <p style={{color: '#dc2626', fontSize: '0.875rem', marginTop: '0.5rem'}}>
                    There was an error loading teams from the server.
                  </p>
                )}
              </div>
            ) : (
              <div>
                <p style={{color: '#6b7280'}}>No teams match your search criteria</p>
                <button 
                  onClick={() => {setSearchTerm(''); setTypeFilter('')}}
                  style={{
                    marginTop: '1rem',
                    color: '#2563eb',
                    background: 'none',
                    border: '1px solid #2563eb',
                    padding: '0.5rem 1rem',
                    borderRadius: '0.375rem',
                    cursor: 'pointer'
                  }}
                >
                  Clear all filters
                </button>
              </div>
            )}
          </div>
        ) : (
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem'}}>
            {filteredTeams.map((team) => {
              // Defensive check for team object
              if (!team || typeof team !== 'object' || !team.id) {
                console.warn('Invalid team object in render:', team)
                return null
              }
              
              return (
            <div key={team.id} style={{
              backgroundColor: 'white',
              borderRadius: '0.75rem',
              border: '1px solid #e5e7eb',
              padding: '1.5rem',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
              transition: 'transform 0.2s, box-shadow 0.2s',
              cursor: 'pointer'
            }}>
              {/* Team Header */}
              <div style={{display: 'flex', alignItems: 'center', marginBottom: '1rem'}}>
                <div style={{
                  width: '3rem',
                  height: '3rem',
                  backgroundColor: (team.color || '#6b7280') + '20',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: '1rem'
                }}>
                  <span style={{fontSize: '1.5rem', color: team.color || '#6b7280'}}>👥</span>
                </div>
                <div style={{flex: 1}}>
                  <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', margin: 0}}>
                    {team.name || 'Unknown Team'}
                  </h3>
                  <div style={{display: 'flex', alignItems: 'center', marginTop: '0.25rem'}}>
                    <div style={{
                      width: '0.5rem',
                      height: '0.5rem',
                      borderRadius: '50%',
                      backgroundColor: (team.status === 'active' || !team.status) ? '#22c55e' : '#eab308',
                      marginRight: '0.5rem'
                    }}></div>
                    <span style={{fontSize: '0.75rem', color: '#6b7280', textTransform: 'capitalize'}}>
                      {team.status || 'inactive'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Description */}
              <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem', lineHeight: '1.5'}}>
                {team.description || 'No description available'}
              </p>

              {/* Team Members */}
              <div style={{marginBottom: '1rem'}}>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem'}}>
                  <span style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827'}}>Team Members</span>
                  <span style={{
                    fontSize: '0.75rem',
                    fontWeight: '500',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '1rem',
                    backgroundColor: '#f3f4f6',
                    color: '#374151'
                  }}>
                    {Array.isArray(team.members) ? team.members.length : 0}
                  </span>
                </div>
                <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.5rem'}}>
                  {Array.isArray(team.members) && team.members.length > 0 ? (
                    team.members.map((member, index) => (
                      <span key={index} style={{
                        fontSize: '0.75rem',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '0.25rem',
                        backgroundColor: (team.color || '#6b7280') + '10',
                        color: team.color || '#6b7280',
                        border: `1px solid ${(team.color || '#6b7280')}30`
                      }}>
                        {member || 'Unknown Member'}
                      </span>
                    ))
                  ) : (
                    <span style={{
                      fontSize: '0.75rem',
                      color: '#6b7280',
                      fontStyle: 'italic'
                    }}>
                      No members assigned
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div style={{display: 'flex', gap: '0.5rem', paddingTop: '1rem', borderTop: '1px solid #f3f4f6'}}>
                <button 
                  onClick={() => navigate(`/teams/${team.id}/details`)}
                  style={{
                    flex: 1,
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.75rem',
                    backgroundColor: 'white',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                >
                  View Details
                </button>
                <button 
                  onClick={() => navigate(`/teams/${team.id}/manage`)}
                  style={{
                    flex: 1,
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.75rem',
                    backgroundColor: 'white',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                >
                  Manage
                </button>
                <button 
                  onClick={() => navigate(`/teams/${team.id}/settings`)}
                  style={{
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.75rem',
                    backgroundColor: 'white',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                >
                  ⚙️
                </button>
              </div>
            </div>
              )
            })}
          </div>
        )}

        {/* Team Stats */}
        {!loading && (
          <div style={{marginTop: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem'}}>
            <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
              <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                <div>
                  <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Total Teams</p>
                  <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                    {Array.isArray(teams) ? teams.length : 0}
                  </p>
                </div>
                <span style={{fontSize: '2rem'}}>👥</span>
              </div>
            </div>

            <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
              <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                <div>
                  <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Active Teams</p>
                  <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                    {Array.isArray(teams) ? teams.filter(t => t?.status === 'active').length : 0}
                  </p>
                </div>
                <span style={{fontSize: '2rem'}}>⚡</span>
              </div>
            </div>

            <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
              <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
                <div>
                  <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Total Members</p>
                  <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                    {Array.isArray(teams) ? teams.reduce((acc, team) => {
                      const memberCount = Array.isArray(team?.members) ? team.members.length : 0
                      return acc + memberCount
                    }, 0) : 0}
                  </p>
                </div>
                <span style={{fontSize: '2rem'}}>🤖</span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

// Export wrapped with error boundary
export function FixedTeamsPage() {
  return (
    <ErrorBoundary>
      <FixedTeamsPageCore />
    </ErrorBoundary>
  )
}