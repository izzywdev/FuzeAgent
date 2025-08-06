import { Link, useNavigate } from 'react-router-dom'

const teams = [
  {
    id: '1',
    name: 'Executive Team',
    description: 'Strategic leadership and decision making',
    members: ['IzzyAI CEO', 'Alex CTO', 'Sarah CPO'],
    status: 'active',
    color: '#7c3aed'
  },
  {
    id: '2', 
    name: 'Development Team',
    description: 'Frontend, backend, and full-stack development',
    members: ['React Developer', 'Python Developer', 'TypeScript Developer'],
    status: 'active',
    color: '#2563eb'
  },
  {
    id: '3',
    name: 'Quality Assurance',
    description: 'Testing, quality control, and bug detection',
    members: ['QA Engineer'],
    status: 'active',
    color: '#16a34a'
  },
  {
    id: '4',
    name: 'DevOps Team',
    description: 'Infrastructure, deployment, and system operations',
    members: ['DevOps Engineer'],
    status: 'active',
    color: '#ea580c'
  },
  {
    id: '5',
    name: 'Business Team',
    description: 'Marketing, sales, and customer relations',
    members: ['Marketing Agent', 'Sales Agent'],
    status: 'active',
    color: '#dc2626'
  }
]

export function FixedTeamsPage() {
  const navigate = useNavigate()
  
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
              style={{
                padding: '0.5rem 0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                width: '20rem'
              }}
            />
          </div>
          <button style={{
            backgroundColor: '#2563eb',
            color: 'white',
            padding: '0.5rem 1rem',
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            fontWeight: '500',
            border: 'none',
            cursor: 'pointer'
          }}>
            + Create Team
          </button>
        </div>

        {/* Teams Grid */}
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem'}}>
          {teams.map((team) => (
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
                  backgroundColor: team.color + '20',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: '1rem'
                }}>
                  <span style={{fontSize: '1.5rem', color: team.color}}>👥</span>
                </div>
                <div style={{flex: 1}}>
                  <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', margin: 0}}>{team.name}</h3>
                  <div style={{display: 'flex', alignItems: 'center', marginTop: '0.25rem'}}>
                    <div style={{
                      width: '0.5rem',
                      height: '0.5rem',
                      borderRadius: '50%',
                      backgroundColor: team.status === 'active' ? '#22c55e' : '#eab308',
                      marginRight: '0.5rem'
                    }}></div>
                    <span style={{fontSize: '0.75rem', color: '#6b7280', textTransform: 'capitalize'}}>
                      {team.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* Description */}
              <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem', lineHeight: '1.5'}}>
                {team.description}
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
                    {team.members.length}
                  </span>
                </div>
                <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.5rem'}}>
                  {team.members.map((member, index) => (
                    <span key={index} style={{
                      fontSize: '0.75rem',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '0.25rem',
                      backgroundColor: team.color + '10',
                      color: team.color,
                      border: `1px solid ${team.color}30`
                    }}>
                      {member}
                    </span>
                  ))}
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
          ))}
        </div>

        {/* Team Stats */}
        <div style={{marginTop: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem'}}>
          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
              <div>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Total Teams</p>
                <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>{teams.length}</p>
              </div>
              <span style={{fontSize: '2rem'}}>👥</span>
            </div>
          </div>

          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
              <div>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Active Teams</p>
                <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                  {teams.filter(t => t.status === 'active').length}
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
                  {teams.reduce((acc, team) => acc + team.members.length, 0)}
                </p>
              </div>
              <span style={{fontSize: '2rem'}}>🤖</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}