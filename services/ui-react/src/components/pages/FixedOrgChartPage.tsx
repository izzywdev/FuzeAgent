import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'

const orgData = {
  organization: 'WCG - World Class Group',
  ceo: 'IzzyAI CEO',
  departments: [
    {
      name: 'Executive Leadership',
      head: 'IzzyAI CEO',
      color: '#7c3aed',
      teams: [
        {
          name: 'C-Suite',
          lead: 'IzzyAI CEO',
          members: ['IzzyAI CEO', 'Alex CTO', 'Sarah CPO']
        }
      ]
    },
    {
      name: 'Engineering',
      head: 'Alex CTO',
      color: '#2563eb',
      teams: [
        {
          name: 'Frontend Development',
          lead: 'React Developer',
          members: ['React Developer', 'TypeScript Developer']
        },
        {
          name: 'Backend Development', 
          lead: 'Python Developer',
          members: ['Python Developer']
        },
        {
          name: 'DevOps',
          lead: 'DevOps Engineer',
          members: ['DevOps Engineer']
        }
      ]
    },
    {
      name: 'Product & Quality',
      head: 'Sarah CPO',
      color: '#16a34a',
      teams: [
        {
          name: 'Quality Assurance',
          lead: 'QA Engineer',
          members: ['QA Engineer']
        }
      ]
    },
    {
      name: 'Business Operations',
      head: 'IzzyAI CEO',
      color: '#dc2626',
      teams: [
        {
          name: 'Marketing',
          lead: 'Marketing Agent',
          members: ['Marketing Agent']
        },
        {
          name: 'Sales',
          lead: 'Sales Agent', 
          members: ['Sales Agent']
        }
      ]
    }
  ]
}

type Org = { id: string; name: string }
type Team = { id: string; organization_id: string; name: string; description?: string }
type Agent = { id: string; team_id?: string; name: string; type?: string }

export function FixedOrgChartPage() {
  const [org, setOrg] = useState<Org | null>(null)
  const [teams, setTeams] = useState<Team[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [orgsRes, teamsRes, agentsRes] = await Promise.all([
          fetch('/organizations'),
          fetch('/teams'),
          fetch('/agents'),
        ])
        const orgs: Org[] = await orgsRes.json()
        setOrg(orgs[0] || null)
        setTeams(await teamsRes.json())
        setAgents(await agentsRes.json())
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const orgChart = useMemo(() => {
    if (!org) return orgData
    const grouped: Record<string, Agent[]> = {}
    for (const ag of agents) {
      const key = ag.team_id || 'unassigned'
      grouped[key] = grouped[key] || []
      grouped[key].push(ag)
    }
    return {
      organization: org.name,
      ceo: 'Organization',
      departments: [
        {
          name: 'Teams',
          head: 'Team Leads',
          color: '#2563eb',
          teams: teams.map(t => ({
            name: t.name,
            lead: 'Lead',
            members: (grouped[t.id] || []).map(a => a.name || 'Agent')
          }))
        }
      ]
    }
  }, [org, teams, agents])

  const view = org ? orgChart : orgData

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading organization chart…</div>
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
                <Link to="/teams" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Teams
                </Link>
                <Link to="/goals" style={{color: '#6b7280', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none'}}>
                  Goals
                </Link>
                <Link to="/organization-chart" style={{color: '#2563eb', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none', borderBottom: '2px solid #2563eb', paddingBottom: '1rem'}}>
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
        <div style={{textAlign: 'center', marginBottom: '2rem'}}>
          <h2 style={{fontSize: '2rem', fontWeight: 'bold', color: '#111827'}}>{view.organization}</h2>
          <p style={{marginTop: '0.5rem', fontSize: '0.875rem', color: '#6b7280'}}>
            AI Team Organizational Structure
          </p>
        </div>

        {/* CEO Level */}
        <div style={{textAlign: 'center', marginBottom: '3rem'}}>
          <div style={{
            display: 'inline-block',
            backgroundColor: 'white',
            padding: '1.5rem 2rem',
            borderRadius: '1rem',
            border: '2px solid #7c3aed',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
          }}>
            <div style={{
              width: '4rem',
              height: '4rem',
              backgroundColor: '#7c3aed',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1rem'
            }}>
              <span style={{fontSize: '2rem'}}>👑</span>
            </div>
            <h3 style={{fontSize: '1.125rem', fontWeight: 'bold', color: '#111827', margin: 0}}>{view.ceo}</h3>
            <p style={{fontSize: '0.875rem', color: '#6b7280', margin: '0.25rem 0 0 0'}}>Chief Executive Officer</p>
          </div>
        </div>

        {/* Departments */}
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem'}}>
          {view.departments.map((dept, deptIndex) => (
            <div key={deptIndex} style={{
              backgroundColor: 'white',
              borderRadius: '1rem',
              border: '1px solid #e5e7eb',
              padding: '1.5rem',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
            }}>
              {/* Department Header */}
              <div style={{textAlign: 'center', marginBottom: '1.5rem'}}>
                <div style={{
                  width: '3rem',
                  height: '3rem',
                  backgroundColor: dept.color + '20',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 0.75rem'
                }}>
                  <span style={{fontSize: '1.5rem', color: dept.color}}>🏢</span>
                </div>
                <h3 style={{fontSize: '1.125rem', fontWeight: 'bold', color: '#111827', margin: 0}}>{dept.name}</h3>
                <p style={{fontSize: '0.75rem', color: '#6b7280', margin: '0.25rem 0 0 0'}}>Head: {dept.head}</p>
              </div>

              {/* Teams */}
              <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                {dept.teams.map((team, teamIndex) => (
                  <div key={teamIndex} style={{
                    backgroundColor: '#f9fafb',
                    padding: '1rem',
                    borderRadius: '0.5rem',
                    border: `1px solid ${dept.color}30`
                  }}>
                    <div style={{display: 'flex', alignItems: 'center', marginBottom: '0.75rem'}}>
                      <div style={{
                        width: '2rem',
                        height: '2rem',
                        backgroundColor: dept.color + '20',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        marginRight: '0.75rem'
                      }}>
                        <span style={{fontSize: '1rem', color: dept.color}}>👥</span>
                      </div>
                      <div>
                        <h4 style={{fontSize: '0.875rem', fontWeight: '600', color: '#111827', margin: 0}}>{team.name}</h4>
                        <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>Lead: {team.lead}</p>
                      </div>
                    </div>
                    
                    {/* Team Members */}
                    <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.5rem'}}>
                      {team.members.map((member, memberIndex) => (
                        <span key={memberIndex} style={{
                          fontSize: '0.75rem',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '0.25rem',
                          backgroundColor: 'white',
                          border: `1px solid ${dept.color}40`,
                          color: dept.color
                        }}>
                          {member}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Organization Stats */}
        <div style={{marginTop: '3rem', backgroundColor: 'white', borderRadius: '1rem', padding: '2rem', border: '1px solid #e5e7eb'}}>
          <h3 style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#111827', marginBottom: '1.5rem', textAlign: 'center'}}>
            Organization Overview
          </h3>
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem'}}>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>🏢</div>
              <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827'}}>{orgData.departments.length}</div>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>Departments</div>
            </div>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>👥</div>
              <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827'}}>
                {view.departments.reduce((acc, dept) => acc + dept.teams.length, 0)}
              </div>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>Teams</div>
            </div>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>🤖</div>
              <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827'}}>
                {view.departments.reduce((acc, dept) => 
                  acc + dept.teams.reduce((teamAcc, team) => teamAcc + team.members.length, 0), 0
                )}
              </div>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>AI Agents</div>
            </div>
            <div style={{textAlign: 'center'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>⚡</div>
              <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#16a34a'}}>Active</div>
              <div style={{fontSize: '0.875rem', color: '#6b7280'}}>Status</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}