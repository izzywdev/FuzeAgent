import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

interface Agent {
  id: string
  name: string
  type: string
  status: 'active' | 'idle' | 'error'
  tasks: {
    completed: number
    running: number
    pending: number
  }
  lastActivity: string
}

const mockAgents: Agent[] = [
  {
    id: '1',
    name: 'IzzyAI CEO',
    type: 'Executive',
    status: 'active',
    tasks: { completed: 23, running: 2, pending: 1 },
    lastActivity: '2 minutes ago'
  },
  {
    id: '2',
    name: 'CTO Agent',
    type: 'Executive', 
    status: 'active',
    tasks: { completed: 18, running: 1, pending: 3 },
    lastActivity: '5 minutes ago'
  },
  {
    id: '3',
    name: 'Frontend Dev',
    type: 'Developer',
    status: 'idle',
    tasks: { completed: 42, running: 0, pending: 2 },
    lastActivity: '1 hour ago'
  }
]

export function FixedDashboard() {
  const [agents] = useState<Agent[]>(mockAgents)
  const [teamsCount, setTeamsCount] = useState<number>(5)
  const [orgName] = useState<string>('WCG - World Class Group')
  const navigate = useNavigate()

  useEffect(() => {
    // Load teams count
    fetch('http://localhost:8000/teams')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setTeamsCount(data.length)
        }
      })
      .catch(() => {
        // Keep default count
      })
  }, [])

  return (
    <div style={{minHeight: '100vh', backgroundColor: '#f9fafb'}}>
      {/* Navigation */}
      <nav style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '0 1rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '4rem'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <div style={{display: 'flex', alignItems: 'center'}}>
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
              </div>
              
              {/* Navigation Links */}
              <div style={{display: 'flex', marginLeft: '1.5rem', gap: '2rem'}}>
                <Link to="/" style={{color: '#2563eb', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none', borderBottom: '2px solid #2563eb', paddingBottom: '1rem'}}>
                  Dashboard
                </Link>
                <Link to="/agents" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
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

            <div style={{display: 'flex', alignItems: 'center', gap: '1rem'}}>
              {/* Search */}
              <input
                type="text"
                placeholder="Search..."
                style={{
                  width: '16rem',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              />
              
              {/* User Avatar */}
              <div style={{
                width: '2rem',
                height: '2rem',
                backgroundColor: '#d1d5db',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <span style={{color: '#4b5563', fontWeight: '600', fontSize: '0.875rem'}}>U</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main style={{maxWidth: '80rem', margin: '0 auto', padding: '1.5rem 1rem'}}>
        {/* Header */}
        <div style={{marginBottom: '2rem'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'start'}}>
            <div>
              <h2 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827'}}>Dashboard</h2>
              <p style={{marginTop: '0.25rem', fontSize: '0.875rem', color: '#6b7280'}}>
                Monitor your AI agents and team performance
              </p>
            </div>
            <Link to="/organization/profile" style={{
              backgroundColor: 'white', 
              padding: '1rem', 
              borderRadius: '0.5rem', 
              border: '1px solid #e5e7eb',
              textDecoration: 'none',
              display: 'block',
              transition: 'border-color 0.2s, box-shadow 0.2s',
              cursor: 'pointer'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#2563eb'
              e.currentTarget.style.boxShadow = '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#e5e7eb'
              e.currentTarget.style.boxShadow = 'none'
            }}>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>Organization</div>
              <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', marginTop: '0.25rem'}}>{orgName}</div>
            </Link>
          </div>
        </div>

        {/* Stats Cards */}
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem'}}>
          <div style={{backgroundColor: 'white', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <div style={{
                width: '2rem',
                height: '2rem',
                backgroundColor: '#dbeafe',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginRight: '1rem'
              }}>
                <span style={{color: '#2563eb', fontSize: '1rem'}}>👥</span>
              </div>
              <div>
                <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#6b7280'}}>Total Agents</div>
                <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827'}}>10</div>
              </div>
            </div>
          </div>

          <div style={{backgroundColor: 'white', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <div style={{
                width: '2rem',
                height: '2rem',
                backgroundColor: '#dcfce7',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginRight: '1rem'
              }}>
                <span style={{color: '#16a34a', fontSize: '1rem'}}>⚡</span>
              </div>
              <div>
                <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#6b7280'}}>Active Agents</div>
                <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827'}}>8</div>
              </div>
            </div>
          </div>

          <div style={{backgroundColor: 'white', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <div style={{
                width: '2rem',
                height: '2rem',
                backgroundColor: '#f3e8ff',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginRight: '1rem'
              }}>
                <span style={{color: '#9333ea', fontSize: '1rem'}}>✅</span>
              </div>
              <div>
                <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#6b7280'}}>Tasks Completed</div>
                <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827'}}>145</div>
              </div>
            </div>
          </div>

          <div style={{backgroundColor: 'white', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <div style={{
                width: '2rem',
                height: '2rem',
                backgroundColor: '#fed7aa',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginRight: '1rem'
              }}>
                <span style={{color: '#ea580c', fontSize: '1rem'}}>👥</span>
              </div>
              <div>
                <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#6b7280'}}>Teams</div>
                <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827'}}>{teamsCount}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Content Grid */}
        <div style={{display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem'}}>
          {/* Active Agents */}
          <div style={{backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
            <div style={{padding: '1.5rem 1.5rem 0 1.5rem', borderBottom: '1px solid #e5e7eb'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
                <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827'}}>Active Agents</h3>
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
            </div>
            <div style={{padding: '1.5rem'}}>
              <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                {agents.map((agent) => (
                  <div key={agent.id} style={{
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.5rem',
                    padding: '1rem',
                    transition: 'box-shadow 0.2s'
                  }}>
                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem'}}>
                      <div style={{display: 'flex', alignItems: 'center'}}>
                        <div style={{
                          width: '2.5rem',
                          height: '2.5rem',
                          backgroundColor: '#f3f4f6',
                          borderRadius: '50%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          marginRight: '0.75rem'
                        }}>
                          <span style={{fontSize: '1rem'}}>🤖</span>
                        </div>
                        <div>
                          <h4 style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: 0}}>{agent.name}</h4>
                          <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>{agent.type}</p>
                        </div>
                      </div>
                      <div style={{display: 'flex', alignItems: 'center'}}>
                        <div style={{
                          width: '0.5rem',
                          height: '0.5rem',
                          borderRadius: '50%',
                          backgroundColor: agent.status === 'active' ? '#22c55e' : agent.status === 'idle' ? '#eab308' : '#ef4444',
                          marginRight: '0.5rem'
                        }}></div>
                        <span style={{fontSize: '0.875rem', color: '#6b7280', textTransform: 'capitalize'}}>{agent.status}</span>
                      </div>
                    </div>
                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', textAlign: 'center'}}>
                      <div>
                        <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#16a34a'}}>{agent.tasks.completed}</div>
                        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Completed</div>
                      </div>
                      <div>
                        <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#2563eb'}}>{agent.tasks.running}</div>
                        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Running</div>
                      </div>
                      <div>
                        <div style={{fontSize: '1.125rem', fontWeight: '600', color: '#6b7280'}}>{agent.tasks.pending}</div>
                        <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Pending</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div style={{backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
            <div style={{padding: '1.5rem 1.5rem 0 1.5rem', borderBottom: '1px solid #e5e7eb'}}>
              <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', marginBottom: '1.5rem'}}>Recent Activity</h3>
            </div>
            <div style={{padding: '1.5rem'}}>
              <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                <div style={{display: 'flex', alignItems: 'flex-start'}}>
                  <div style={{
                    width: '0.5rem',
                    height: '0.5rem',
                    borderRadius: '50%',
                    backgroundColor: '#22c55e',
                    marginTop: '0.5rem',
                    marginRight: '0.75rem'
                  }}></div>
                  <div>
                    <p style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: 0}}>IzzyAI CEO</p>
                    <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Completed strategic planning task</p>
                    <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: '0.25rem 0 0 0'}}>2 minutes ago</p>
                  </div>
                </div>
                <div style={{display: 'flex', alignItems: 'flex-start'}}>
                  <div style={{
                    width: '0.5rem',
                    height: '0.5rem',
                    borderRadius: '50%',
                    backgroundColor: '#3b82f6',
                    marginTop: '0.5rem',
                    marginRight: '0.75rem'
                  }}></div>
                  <div>
                    <p style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: 0}}>System</p>
                    <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>New React Developer agent deployed</p>
                    <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: '0.25rem 0 0 0'}}>15 minutes ago</p>
                  </div>
                </div>
                <div style={{display: 'flex', alignItems: 'flex-start'}}>
                  <div style={{
                    width: '0.5rem',
                    height: '0.5rem',
                    borderRadius: '50%',
                    backgroundColor: '#ef4444',
                    marginTop: '0.5rem',
                    marginRight: '0.75rem'
                  }}></div>
                  <div>
                    <p style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: 0}}>Backend Dev 2</p>
                    <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Database migration task failed</p>
                    <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: '0.25rem 0 0 0'}}>1 hour ago</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div style={{marginTop: '2rem'}}>
          <div style={{backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)'}}>
            <div style={{padding: '1.5rem 1.5rem 0 1.5rem', borderBottom: '1px solid #e5e7eb'}}>
              <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', marginBottom: '1.5rem'}}>Quick Actions</h3>
            </div>
            <div style={{padding: '1.5rem'}}>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem'}}>
                <button 
                  onClick={() => navigate('/agents/create')}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '2rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                >
                  <span style={{fontSize: '2rem', marginBottom: '0.5rem'}}>➕</span>
                  <span style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827'}}>Deploy New Agent</span>
                </button>
                <button 
                  onClick={() => navigate('/teams/create')}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '2rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                >
                  <span style={{fontSize: '2rem', marginBottom: '0.5rem'}}>👥</span>
                  <span style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827'}}>Create Team</span>
                </button>
                <Link to="/organization-chart" style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '2rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  backgroundColor: 'transparent',
                  textDecoration: 'none',
                  transition: 'background-color 0.2s'
                }}>
                  <span style={{fontSize: '2rem', marginBottom: '0.5rem'}}>📊</span>
                  <span style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827'}}>View Organization Chart</span>
                </Link>
                <button 
                  onClick={() => navigate('/organization/profile')}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '2rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                >
                  <span style={{fontSize: '2rem', marginBottom: '0.5rem'}}>🏢</span>
                  <span style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827'}}>Organization Profile</span>
                </button>
                <button 
                  onClick={() => navigate('/goals')}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '2rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem',
                    backgroundColor: 'transparent',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s'
                  }}
                >
                  <span style={{fontSize: '2rem', marginBottom: '0.5rem'}}>🎯</span>
                  <span style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827'}}>Manage Goals</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}