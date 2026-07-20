import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { API_URL } from '../../config/env'

interface Agent {
  id: string
  name: string
  role: string
  type: string
  status: string
  created_at: string
  updated_at: string
}

const TYPE_ICONS: Record<string, string> = {
  developer: '👨‍💻',
  executive: '👔',
  qa: '🔬',
  devops: '⚙️',
  specialized: '⚡',
}

export function FixedAgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const loadAgents = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_URL}/agents`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setAgents(Array.isArray(data) ? data : [])
    } catch {
      setError('Error loading agents')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadAgents()
  }, [loadAgents])

  const filteredAgents = agents.filter(agent => {
    const matchesSearch =
      !searchTerm ||
      agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      agent.role.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesStatus = !statusFilter || agent.status === statusFilter
    const matchesType = !typeFilter || agent.type === typeFilter
    return matchesSearch && matchesStatus && matchesType
  })

  const activeCount = agents.filter(a => a.status === 'active').length

  if (loading) {
    return (
      <main>
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ color: '#6b7280' }}>Loading agents...</p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main>
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>{error}</h2>
          <p style={{ color: '#6b7280', marginTop: '0.5rem' }}>Please try again later</p>
          <button
            onClick={loadAgents}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      </main>
    )
  }

  return (
    <main>
      <div style={{ maxWidth: '80rem', margin: '0 auto', padding: '1.5rem 1rem' }}>
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '2rem',
          }}
        >
          <div>
            <h2
              style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#111827', margin: 0 }}
            >
              AI Agents
            </h2>
            {agents.length > 0 && (
              <p style={{ marginTop: '0.25rem', fontSize: '0.875rem', color: '#6b7280' }}>
                {activeCount} Active Agents
              </p>
            )}
          </div>
          {agents.length > 0 && (
            <Link
              to="/agents/create"
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#2563eb',
                color: 'white',
                borderRadius: '0.375rem',
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: '500',
              }}
            >
              Create Agent
            </Link>
          )}
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
          <input
            type="search"
            placeholder="Search agents..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={{
              padding: '0.5rem 0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              width: '20rem',
            }}
          />
          <select
            aria-label="Status"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
            }}
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
          <select
            aria-label="Type"
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
            }}
          >
            <option value="">All Types</option>
            <option value="developer">Developer</option>
            <option value="executive">Executive</option>
            <option value="qa">QA</option>
            <option value="devops">DevOps</option>
            <option value="specialized">Specialized</option>
          </select>
        </div>

        {/* Content */}
        {agents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: '#111827' }}>
              No Agents Found
            </h3>
            <p style={{ color: '#6b7280', marginTop: '0.5rem' }}>
              Get started by creating your first AI agent
            </p>
            <Link
              to="/agents/create"
              style={{
                display: 'inline-block',
                marginTop: '1rem',
                padding: '0.5rem 1rem',
                backgroundColor: '#2563eb',
                color: 'white',
                borderRadius: '0.375rem',
                textDecoration: 'none',
              }}
            >
              Create Agent
            </Link>
          </div>
        ) : (
          <div
            className="grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: '1.5rem',
            }}
          >
            {filteredAgents.map(agent => (
              <Link
                key={agent.id}
                to={`/agents/${agent.id}`}
                style={{ textDecoration: 'none' }}
              >
                <div
                  style={{
                    backgroundColor: 'white',
                    borderRadius: '0.5rem',
                    border: '1px solid #e5e7eb',
                    padding: '1.5rem',
                    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: '1rem',
                    }}
                  >
                    <span style={{ fontSize: '1.5rem', marginRight: '1rem' }}>
                      {TYPE_ICONS[agent.type] || '🤖'}
                    </span>
                    <div>
                      <h3
                        style={{
                          margin: 0,
                          fontSize: '1rem',
                          fontWeight: '600',
                          color: '#111827',
                        }}
                      >
                        {agent.name}
                      </h3>
                      <p style={{ margin: 0, fontSize: '0.875rem', color: '#6b7280' }}>
                        {agent.role}
                      </p>
                    </div>
                  </div>
                  <span
                    className={
                      agent.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: '500',
                      padding: '0.25rem 0.5rem',
                      borderRadius: '0.25rem',
                    }}
                  >
                    {agent.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
