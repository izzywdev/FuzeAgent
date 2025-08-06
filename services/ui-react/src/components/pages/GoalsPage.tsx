import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

interface Goal {
  id: string
  title: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'planning' | 'active' | 'completed' | 'on_hold'
  target_completion_date: string
  progress_percentage: number
  assigned_teams: string[]
  milestones: {
    id: string
    title: string
    status: string
    due_date: string
  }[]
  created_at: string
  updated_at: string
}

export function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    // Try to fetch goals from API
    fetch('http://localhost:8000/organizations/1/goals')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setGoals(data)
        } else {
          // Use mock data if API returns non-array
          setGoals(mockGoals)
        }
        setLoading(false)
      })
      .catch(() => {
        // Use mock data on error
        setGoals(mockGoals)
        setLoading(false)
      })
  }, [])

  const mockGoals: Goal[] = [
    {
      id: '1',
      title: 'Expand AI Agent Capabilities',
      description: 'Develop advanced AI agents with enhanced reasoning and task execution capabilities across multiple domains.',
      priority: 'high',
      status: 'active',
      target_completion_date: '2025-12-31',
      progress_percentage: 75,
      assigned_teams: ['Development Team', 'Executive Team'],
      milestones: [
        { id: '1', title: 'Deploy 10 specialized agents', status: 'completed', due_date: '2025-08-15' },
        { id: '2', title: 'Implement cross-team coordination', status: 'active', due_date: '2025-09-30' },
        { id: '3', title: 'Launch advanced reasoning system', status: 'planning', due_date: '2025-11-15' }
      ],
      created_at: '2025-08-01T10:00:00Z',
      updated_at: '2025-08-06T14:30:00Z'
    },
    {
      id: '2',
      title: 'Establish Market Leadership',
      description: 'Position WCG as the leading AI-powered software development organization in the market.',
      priority: 'critical',
      status: 'active',
      target_completion_date: '2025-10-31',
      progress_percentage: 45,
      assigned_teams: ['Business Team', 'Executive Team'],
      milestones: [
        { id: '4', title: 'Complete market analysis', status: 'completed', due_date: '2025-08-10' },
        { id: '5', title: 'Launch marketing campaign', status: 'active', due_date: '2025-09-01' },
        { id: '6', title: 'Secure 5 enterprise clients', status: 'planning', due_date: '2025-10-15' }
      ],
      created_at: '2025-08-01T10:00:00Z',
      updated_at: '2025-08-06T12:00:00Z'
    },
    {
      id: '3',
      title: 'Optimize Development Workflow',
      description: 'Implement automated CI/CD pipelines and development tools to increase team productivity by 40%.',
      priority: 'medium',
      status: 'active',
      target_completion_date: '2025-09-30',
      progress_percentage: 60,
      assigned_teams: ['Development Team', 'DevOps Team'],
      milestones: [
        { id: '7', title: 'Set up automated testing', status: 'completed', due_date: '2025-08-20' },
        { id: '8', title: 'Deploy CI/CD pipeline', status: 'active', due_date: '2025-09-05' },
        { id: '9', title: 'Integrate monitoring tools', status: 'planning', due_date: '2025-09-20' }
      ],
      created_at: '2025-08-01T10:00:00Z',
      updated_at: '2025-08-06T09:15:00Z'
    },
    {
      id: '4',
      title: 'Quality Assurance Excellence',
      description: 'Achieve 99.9% uptime and zero-defect releases through advanced QA processes and automation.',
      priority: 'high',
      status: 'planning',
      target_completion_date: '2025-11-30',
      progress_percentage: 25,
      assigned_teams: ['Quality Assurance', 'Development Team'],
      milestones: [
        { id: '10', title: 'Implement automated testing suite', status: 'planning', due_date: '2025-09-15' },
        { id: '11', title: 'Set up performance monitoring', status: 'planning', due_date: '2025-10-01' },
        { id: '12', title: 'Establish quality gates', status: 'planning', due_date: '2025-10-30' }
      ],
      created_at: '2025-08-01T10:00:00Z',
      updated_at: '2025-08-05T16:45:00Z'
    }
  ]

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return '#dc2626'
      case 'high': return '#ea580c'
      case 'medium': return '#ca8a04'
      case 'low': return '#16a34a'
      default: return '#6b7280'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#16a34a'
      case 'active': return '#2563eb'
      case 'planning': return '#ca8a04'
      case 'on_hold': return '#dc2626'
      default: return '#6b7280'
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
                <Link to="/goals" style={{color: '#2563eb', fontWeight: '500', fontSize: '0.875rem', textDecoration: 'none', borderBottom: '2px solid #2563eb', paddingBottom: '1rem'}}>
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
          <h2 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827'}}>Organizational Goals</h2>
          <p style={{marginTop: '0.25rem', fontSize: '0.875rem', color: '#6b7280'}}>
            Track and manage strategic objectives and milestones
          </p>
        </div>

        {/* Stats Overview */}
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '2rem'}}>
          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
              <div>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Total Goals</p>
                <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                  {goals.length}
                </p>
              </div>
              <span style={{fontSize: '2rem'}}>🎯</span>
            </div>
          </div>

          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
              <div>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Active Goals</p>
                <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                  {goals.filter(g => g.status === 'active').length}
                </p>
              </div>
              <span style={{fontSize: '2rem'}}>🚀</span>
            </div>
          </div>

          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
              <div>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Completed</p>
                <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                  {goals.filter(g => g.status === 'completed').length}
                </p>
              </div>
              <span style={{fontSize: '2rem'}}>✅</span>
            </div>
          </div>

          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between'}}>
              <div>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Avg Progress</p>
                <p style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827', margin: '0.25rem 0 0 0'}}>
                  {Math.round(goals.reduce((acc, g) => acc + g.progress_percentage, 0) / goals.length)}%
                </p>
              </div>
              <span style={{fontSize: '2rem'}}>📊</span>
            </div>
          </div>
        </div>

        {/* Actions Bar */}
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem'}}>
          <div style={{display: 'flex', gap: '1rem'}}>
            <input
              type="text"
              placeholder="Search goals..."
              style={{
                padding: '0.5rem 0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                width: '20rem'
              }}
            />
            <select style={{
              padding: '0.5rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem'
            }}>
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="planning">Planning</option>
              <option value="completed">Completed</option>
              <option value="on_hold">On Hold</option>
            </select>
          </div>
          <button 
            onClick={() => setShowCreateForm(true)}
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
            + Create Goal
          </button>
        </div>

        {/* Goals Grid */}
        {loading ? (
          <div style={{textAlign: 'center', padding: '3rem'}}>
            <p style={{color: '#6b7280'}}>Loading goals...</p>
          </div>
        ) : goals.length === 0 ? (
          <div style={{textAlign: 'center', padding: '3rem'}}>
            <div style={{fontSize: '3rem', marginBottom: '1rem'}}>🎯</div>
            <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem'}}>No Goals Found</h3>
            <p style={{color: '#6b7280', marginBottom: '1.5rem'}}>
              Create your first organizational goal to get started
            </p>
            <button 
              onClick={() => setShowCreateForm(true)}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}
            >
              Create First Goal
            </button>
          </div>
        ) : (
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '1.5rem'}}>
            {goals.map((goal) => (
              <div key={goal.id} style={{
                backgroundColor: 'white',
                borderRadius: '0.75rem',
                border: '1px solid #e5e7eb',
                padding: '1.5rem',
                boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
                cursor: 'pointer'
              }}
              onClick={() => navigate(`/goals/${goal.id}`)}
              >
                {/* Goal Header */}
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem'}}>
                  <div style={{flex: 1}}>
                    <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', margin: '0 0 0.5rem 0'}}>
                      {goal.title}
                    </h3>
                    <div style={{display: 'flex', gap: '0.5rem', marginBottom: '0.5rem'}}>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: '500',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '0.25rem',
                        backgroundColor: getPriorityColor(goal.priority) + '20',
                        color: getPriorityColor(goal.priority)
                      }}>
                        {goal.priority.toUpperCase()}
                      </span>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: '500',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '0.25rem',
                        backgroundColor: getStatusColor(goal.status) + '20',
                        color: getStatusColor(goal.status)
                      }}>
                        {goal.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div style={{textAlign: 'right'}}>
                    <div style={{fontSize: '1.5rem', fontWeight: 'bold', color: '#111827'}}>
                      {goal.progress_percentage}%
                    </div>
                    <div style={{fontSize: '0.75rem', color: '#6b7280'}}>Progress</div>
                  </div>
                </div>

                {/* Description */}
                <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem', lineHeight: '1.5'}}>
                  {goal.description}
                </p>

                {/* Progress Bar */}
                <div style={{marginBottom: '1rem'}}>
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem'}}>
                    <span style={{fontSize: '0.75rem', color: '#6b7280'}}>Progress</span>
                    <span style={{fontSize: '0.75rem', color: '#6b7280'}}>{goal.progress_percentage}%</span>
                  </div>
                  <div style={{width: '100%', height: '0.5rem', backgroundColor: '#f3f4f6', borderRadius: '0.25rem', overflow: 'hidden'}}>
                    <div style={{
                      width: `${goal.progress_percentage}%`, 
                      height: '100%', 
                      backgroundColor: '#2563eb',
                      transition: 'width 0.3s ease'
                    }}></div>
                  </div>
                </div>

                {/* Milestones */}
                <div style={{marginBottom: '1rem'}}>
                  <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', marginBottom: '0.5rem'}}>
                    Milestones ({goal.milestones.length})
                  </div>
                  <div style={{display: 'flex', flexDirection: 'column', gap: '0.25rem'}}>
                    {goal.milestones.slice(0, 2).map((milestone) => (
                      <div key={milestone.id} style={{display: 'flex', alignItems: 'center', fontSize: '0.75rem'}}>
                        <div style={{
                          width: '0.5rem',
                          height: '0.5rem',
                          borderRadius: '50%',
                          backgroundColor: getStatusColor(milestone.status),
                          marginRight: '0.5rem'
                        }}></div>
                        <span style={{color: '#6b7280', flex: 1}}>{milestone.title}</span>
                        <span style={{color: '#9ca3af'}}>{new Date(milestone.due_date).toLocaleDateString()}</span>
                      </div>
                    ))}
                    {goal.milestones.length > 2 && (
                      <div style={{fontSize: '0.75rem', color: '#9ca3af', marginLeft: '1rem'}}>
                        +{goal.milestones.length - 2} more
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer */}
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: '#9ca3af', paddingTop: '1rem', borderTop: '1px solid #f3f4f6'}}>
                  <span>Due: {new Date(goal.target_completion_date).toLocaleDateString()}</span>
                  <span>{goal.assigned_teams.length} teams</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create Goal Modal (placeholder) */}
        {showCreateForm && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}>
            <div style={{
              backgroundColor: 'white',
              borderRadius: '0.5rem',
              padding: '2rem',
              maxWidth: '500px',
              width: '90%'
            }}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem'}}>Create New Goal</h3>
              <p style={{color: '#6b7280', marginBottom: '1.5rem'}}>
                Goal creation interface coming soon...
              </p>
              <div style={{display: 'flex', gap: '0.5rem', justifyContent: 'end'}}>
                <button 
                  onClick={() => setShowCreateForm(false)}
                  style={{
                    padding: '0.5rem 1rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    backgroundColor: 'white',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer'
                }}>
                  Create Goal
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}