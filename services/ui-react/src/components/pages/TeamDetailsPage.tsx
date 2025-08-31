import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../config/api'
import type { Team as HierarchyTeam, Agent } from '../../types'

export function TeamDetailsPage() {
  const { teamId } = useParams<{ teamId: string }>()
  const [team, setTeam] = useState<HierarchyTeam | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      if (!teamId) return
      setLoading(true)
      setError(null)
      try {
        const [t, a] = await Promise.all([
          api.hierarchy.get(`/teams/${teamId}`),
          api.hierarchy.get(`/agents?team_id=${teamId}`)
        ])
        setTeam(t)
        setAgents(a)
      } catch (e: any) {
        setError(e?.message || 'Failed to load team')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [teamId])

  if (loading) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>⏳</div>
          <p style={{color: '#6b7280'}}>Loading team...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>❌</div>
          <p style={{color: '#ef4444', marginBottom: '1rem'}}>{error}</p>
          <Link to="/teams" style={{color: '#2563eb', textDecoration: 'none', fontSize: '0.875rem'}}>
            ← Back to Teams
          </Link>
        </div>
      </div>
    )
  }

  if (!team) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>❌</div>
          <p style={{color: '#ef4444', marginBottom: '1rem'}}>Team not found</p>
          <Link to="/teams" style={{color: '#2563eb', textDecoration: 'none', fontSize: '0.875rem'}}>
            ← Back to Teams
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div style={{minHeight: '100vh', backgroundColor: '#f9fafb'}}>
      {/* Team Header */}
      <div style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb'}}>
        <div style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
          <div style={{display: 'flex', alignItems: 'center'}}>
            <div style={{
              width: '5rem',
              height: '5rem',
              backgroundColor: '#2563eb20',
              borderRadius: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '1.5rem'
            }}>
              <span style={{fontSize: '2.5rem', color: '#2563eb'}}>👥</span>
            </div>
            <div style={{flex: 1}}>
              <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem'}}>
                <h1 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827', margin: 0}}>{team.name}</h1>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '1rem',
                  backgroundColor: '#dcfce7',
                  fontSize: '0.75rem',
                  fontWeight: '500'
                }}>
                  <div style={{
                    width: '0.5rem',
                    height: '0.5rem',
                    borderRadius: '50%',
                    backgroundColor: '#22c55e',
                    marginRight: '0.5rem'
                  }}></div>
                  {team.team_type}
                </div>
              </div>
              {team.description && (
                <p style={{fontSize: '1.125rem', color: '#6b7280', margin: '0 0 0.5rem 0'}}>{team.description}</p>
              )}
              <div style={{display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#6b7280'}}>
                {team.organization_name && (
                  <span>Organization: <strong>{team.organization_name}</strong></span>
                )}
                <span>Created: <strong>{new Date(team.created_at).toLocaleString()}</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Members (Agents) */}
      <div style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
        <div style={{backgroundColor: 'white', borderRadius: '0.5rem', border: '1px solid #e5e7eb', padding: '1.5rem'}}>
          <h3 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem'}}>Team Members ({agents.length})</h3>
          {agents.length === 0 ? (
            <div style={{textAlign: 'center', color: '#6b7280'}}>No agents found for this team.</div>
          ) : (
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem'}}>
              {agents.map((member) => (
                <div key={member.id} style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '0.5rem',
                  padding: '1rem',
                  backgroundColor: '#fafafa'
                }}>
                  <div style={{display: 'flex', alignItems: 'center', marginBottom: '0.75rem'}}>
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
                      <h4 style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', margin: 0}}>{member.name}</h4>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>{member.role}</p>
                    </div>
                  </div>
                  <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', textAlign: 'center', fontSize: '0.75rem'}}>
                    <div>
                      <div style={{fontWeight: '600', color: '#2563eb'}}>{member.type}</div>
                      <div style={{color: '#6b7280'}}>Type</div>
                    </div>
                    <div>
                      <div style={{fontWeight: '600', color: member.status === 'active' ? '#16a34a' : '#dc2626'}}>{member.status}</div>
                      <div style={{color: '#6b7280'}}>Status</div>
                    </div>
                    <div>
                      <div style={{fontWeight: '600', color: '#6b7280'}}>{new Date(member.created_at).toLocaleDateString()}</div>
                      <div style={{color: '#6b7280'}}>Created</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}