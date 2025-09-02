import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApiService } from '../../hooks/useApiService'

interface Agent {
  id: string
  name: string
  role: string
  type: string
  status: string
  created_at: string
  updated_at: string
}

export function FixedAgentsPage() {
  const apiService = useApiService()
  const [agents, setAgents] = useState<Agent[]>([])
  const [filteredAgents, setFilteredAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const navigate = useNavigate()

  // Filter agents based on search term and type
  useEffect(() => {
    let filtered = agents

    if (searchTerm) {
      filtered = filtered.filter(agent => 
        agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        agent.role.toLowerCase().includes(searchTerm.toLowerCase())
      )
    }

    if (typeFilter) {
      filtered = filtered.filter(agent => agent.type === typeFilter)
    }

    setFilteredAgents(filtered)
  }, [agents, searchTerm, typeFilter])

  useEffect(() => {
    const loadAgents = async () => {
      try {
        const response = await apiService.getAgents()
        
        if (response.ok) {
          const agentData = Array.isArray(response.data) ? response.data : []
          setAgents(agentData)
          setFilteredAgents(agentData)
        } else {
          console.error('Failed to load agents:', response.status)
          setAgents([])
          setFilteredAgents([])
        }
      } catch (err) {
        console.error('Failed to load agents:', err)
        setAgents([])
        setFilteredAgents([])
      } finally {
        setLoading(false)
      }
    }

    loadAgents()
  }, [])

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
                <Link to="/agents" style={{color: '#2563eb', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none', borderBottom: '2px solid #2563eb', paddingBottom: '1rem'}}>
                  Agents
                </Link>
                <Link to="/teams" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
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
          <h2 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827'}}>AI Agents</h2>
          <p style={{marginTop: '0.25rem', fontSize: '0.875rem', color: '#6b7280'}}>
            Manage your AI team members and their configurations
          </p>
        </div>

        {/* Actions Bar */}
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem'}}>
          <div style={{display: 'flex', gap: '1rem'}}>
            <input
              type="text"
              placeholder="Search agents..."
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
              <option value="developer">Developer</option>
              <option value="specialized">Specialized</option>
            </select>
          </div>
          <button 
            onClick={() => navigate('/agents/create')}
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
            + Create Agent
          </button>
        </div>

        {/* Search Results Info */}
        {!loading && (
          <div style={{marginBottom: '1rem', color: '#6b7280', fontSize: '0.875rem'}}>
            {searchTerm || typeFilter ? (
              <span>
                Found {filteredAgents.length} of {agents.length} agents
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
              <span>Showing all {agents.length} agents</span>
            )}
          </div>
        )}

        {/* Agents Grid */}
        {loading ? (
          <div style={{textAlign: 'center', padding: '3rem'}}>
            <p style={{color: '#6b7280'}}>Loading agents...</p>
          </div>
        ) : filteredAgents.length === 0 ? (
          <div style={{textAlign: 'center', padding: '3rem'}}>
            {agents.length === 0 ? (
              <p style={{color: '#6b7280'}}>No agents found</p>
            ) : (
              <div>
                <p style={{color: '#6b7280'}}>No agents match your search criteria</p>
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
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem'}}>
            {filteredAgents.map((agent) => (
              <div key={agent.id} style={{
                backgroundColor: 'white',
                borderRadius: '0.5rem',
                border: '1px solid #e5e7eb',
                padding: '1.5rem',
                boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                transition: 'transform 0.2s, box-shadow 0.2s',
                cursor: 'pointer'
              }}>
                <div style={{display: 'flex', alignItems: 'center', marginBottom: '1rem'}}>
                  <div style={{
                    width: '3rem',
                    height: '3rem',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: '1rem'
                  }}>
                    <span style={{fontSize: '1.5rem'}}>🤖</span>
                  </div>
                  <div>
                    <h3 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: 0}}>{agent.name}</h3>
                    <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>{agent.role}</p>
                  </div>
                </div>
                
                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem'}}>
                  <span style={{fontSize: '0.875rem', color: '#6b7280'}}>Type</span>
                  <span style={{
                    fontSize: '0.75rem',
                    fontWeight: '500',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '0.25rem',
                    backgroundColor: agent.type === 'executive' ? '#dbeafe' : agent.type === 'developer' ? '#dcfce7' : '#f3e8ff',
                    color: agent.type === 'executive' ? '#1d4ed8' : agent.type === 'developer' ? '#15803d' : '#7c3aed'
                  }}>
                    {agent.type}
                  </span>
                </div>

                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem'}}>
                  <span style={{fontSize: '0.875rem', color: '#6b7280'}}>Status</span>
                  <div style={{display: 'flex', alignItems: 'center'}}>
                    <div style={{
                      width: '0.5rem',
                      height: '0.5rem',
                      borderRadius: '50%',
                      backgroundColor: agent.status === 'active' ? '#22c55e' : '#eab308',
                      marginRight: '0.5rem'
                    }}></div>
                    <span style={{fontSize: '0.875rem', color: '#111827', textTransform: 'capitalize'}}>
                      {agent.status}
                    </span>
                  </div>
                </div>

                <div style={{borderTop: '1px solid #e5e7eb', paddingTop: '0.75rem', marginTop: '0.75rem'}}>
                  <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: 0}}>
                    Created: {new Date(agent.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem'}}>
                  <button 
                    onClick={() => navigate(`/agents/${agent.id}`)}
                    style={{
                      flex: 1,
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.75rem',
                      backgroundColor: 'white',
                      cursor: 'pointer'
                    }}
                  >
                    Configure
                  </button>
                  <button 
                    onClick={() => navigate(`/agents/${agent.id}?tab=tasks`)}
                    style={{
                      flex: 1,
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.75rem',
                      backgroundColor: 'white',
                      cursor: 'pointer'
                    }}
                  >
                    Tasks
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}