import { useState, useEffect } from 'react'
import { API_URL } from '../../config/env'
import { Link, useNavigate } from 'react-router-dom'

interface Team {
  id: string
  name: string
}

interface AgentTemplate {
  id: string
  name: string
  description: string
  type: string
  defaultConfig: {
    model: string
    temperature: number
    tools: string[]
    goal: string
    backstory: string
  }
}

export function CreateAgentPage() {
  const navigate = useNavigate()
  const [teams, setTeams] = useState<Team[]>([])
  const [templates, setTemplates] = useState<AgentTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    name: '',
    role: '',
    type: 'developer',
    team_id: '',
    template_id: '',
    config: {
      model: 'claude-sonnet-4-20250514',
      temperature: 0.7,
      tools: [] as string[],
      goal: ' ',
      backstory: ' '
    }
  })

  useEffect(() => {
    // Load teams
    fetch(`${API_URL}/teams`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setTeams(data)
        } else {
          // Mock teams data
          setTeams([
            { id: '1', name: 'Executive Team' },
            { id: '2', name: 'Development Team' },
            { id: '3', name: 'Quality Assurance' },
            { id: '4', name: 'DevOps Team' },
            { id: '5', name: 'Business Team' }
          ])
        }
      })
      .catch(() => {
        // Mock teams data on error
        setTeams([
          { id: '1', name: 'Executive Team' },
          { id: '2', name: 'Development Team' },
          { id: '3', name: 'Quality Assurance' },
          { id: '4', name: 'DevOps Team' },
          { id: '5', name: 'Business Team' }
        ])
      })

    // Load agent templates
    fetch(`${API_URL}/agent-templates`)
      .then(res => res.json())
      .then(data => {
        if (data && data.templates && Array.isArray(data.templates)) {
          // Transform API response to match UI interface
          const transformedTemplates = data.templates.map((template: any) => ({
            id: template.template_id,
            name: template.name,
            description: template.description,
            type: template.category || 'developer',
            defaultConfig: {
              model: template.default_model || 'claude-sonnet-4-20250514',
              temperature: template.default_temperature || 0.7,
              tools: template.tools || [],
              goal: template.default_goal || '',
              backstory: template.default_backstory || ''
            }
          }))
          setTemplates(transformedTemplates)
        } else if (Array.isArray(data)) {
          setTemplates(data)
        } else {
          // Mock templates data
          setTemplates(mockTemplates)
        }
        setLoading(false)
      })
      .catch(() => {
        // Mock templates data on error
        setTemplates(mockTemplates)
        setLoading(false)
      })
  }, [])

  const mockTemplates: AgentTemplate[] = [
    {
      id: 'react_developer',
      name: 'React Developer',
      description: 'Frontend developer specialized in React and TypeScript',
      type: 'developer',
      defaultConfig: {
        model: 'claude-sonnet-4-20250514',
        temperature: 0.7,
        tools: ['code_generation', 'code_review', 'debugging', 'testing'],
        goal: 'Build responsive and performant React applications',
        backstory: 'Experienced frontend developer with deep knowledge of React ecosystem and modern development practices'
      }
    },
    {
      id: 'python_developer',
      name: 'Python Developer', 
      description: 'Backend developer specialized in Python and FastAPI',
      type: 'developer',
      defaultConfig: {
        model: 'claude-sonnet-4-20250514',
        temperature: 0.7,
        tools: ['code_generation', 'api_development', 'database_design', 'testing'],
        goal: 'Develop robust and scalable backend systems',
        backstory: 'Senior Python developer with expertise in FastAPI, databases, and system architecture'
      }
    },
    {
      id: 'qa_engineer',
      name: 'QA Engineer',
      description: 'Quality assurance engineer focused on testing and automation',
      type: 'qa',
      defaultConfig: {
        model: 'claude-sonnet-4-20250514',
        temperature: 0.6,
        tools: ['test_automation', 'bug_reporting', 'quality_analysis', 'performance_testing'],
        goal: 'Ensure high quality and reliability of software products',
        backstory: 'Experienced QA engineer with expertise in automated testing frameworks and quality processes'
      }
    },
    {
      id: 'devops_engineer',
      name: 'DevOps Engineer',
      description: 'Infrastructure and deployment specialist',
      type: 'devops',
      defaultConfig: {
        model: 'claude-sonnet-4-20250514',
        temperature: 0.5,
        tools: ['infrastructure_management', 'deployment', 'monitoring', 'security'],
        goal: 'Maintain reliable and scalable infrastructure',
        backstory: 'DevOps engineer with expertise in cloud platforms, containerization, and CI/CD pipelines'
      }
    }
  ]

  const handleTemplateSelect = (template: AgentTemplate) => {
    setFormData({
      ...formData,
      type: template.type,
      template_id: template.id,
      role: template.name,
      config: {
        ...template.defaultConfig,
        tools: [...template.defaultConfig.tools]
      }
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError(null)
    setCreating(true)

    try {
      const response = await fetch(`${API_URL}/agents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: formData.name,
          role: formData.role,
          type: formData.type,
          team_id: formData.team_id,
          config: {
            ...formData.config,
            goal: formData.config.goal.trim(),
            backstory: formData.config.backstory.trim()
          }
        })
      })

      if (response.ok) {
        const newAgent = await response.json()
        const agentId = newAgent.agent_id || newAgent.agent?.id || newAgent.id
        if (agentId) {
          navigate(`/agents/${agentId}`)
          return // component will unmount; don't reset creating state
        }
        console.error('No agent ID found in response:', newAgent)
        setSubmitError('Agent created but unable to navigate. Please check the agents list.')
      } else {
        setSubmitError('Failed to create agent. Please try again.')
      }
    } catch (error) {
      console.error('Error creating agent:', error)
      setSubmitError('Error creating agent. Please check your connection.')
    }
    setCreating(false)
  }

  const availableTools = [
    'code_generation', 'code_review', 'debugging', 'testing', 'api_development',
    'database_design', 'infrastructure_management', 'deployment', 'monitoring',
    'security', 'performance_testing', 'test_automation', 'bug_reporting',
    'quality_analysis', 'strategic_planning', 'team_management', 'resource_allocation'
  ]

  if (loading) {
    return (
      <div style={{minHeight: '100vh', backgroundColor: '#f9fafb', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div style={{fontSize: '2rem', marginBottom: '1rem'}}>🤖</div>
          <p style={{color: '#6b7280'}}>Loading agent creation form...</p>
        </div>
      </div>
    )
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
                <Link to="/agents" style={{color: '#6b7280', textDecoration: 'none'}}>Agents</Link>
                <span style={{margin: '0 0.5rem'}}>›</span>
                <span style={{color: '#111827'}}>New Agent</span>
              </div>
            </div>
            
            <div style={{display: 'flex', gap: '0.5rem'}}>
              <Link to="/agents" style={{
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
      <main style={{maxWidth: '60rem', margin: '0 auto', padding: '2rem 1rem'}}>
        {/* Header */}
        <div style={{marginBottom: '2rem'}}>
          <h2 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827'}}>Create New Agent</h2>
          <p style={{marginTop: '0.25rem', fontSize: '0.875rem', color: '#6b7280'}}>
            Deploy a new AI agent to your team
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem'}}>
            {/* Main Form */}
            <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', padding: '2rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem'}}>Agent Details</h3>
              
              <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
                <div>
                  <label htmlFor="agent-name" style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Agent Name *
                  </label>
                  <input
                    id="agent-name"
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    placeholder="e.g., Frontend Developer 1"
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
                  <label htmlFor="agent-role" style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Role *
                  </label>
                  <input
                    id="agent-role"
                    type="text"
                    required
                    value={formData.role}
                    onChange={(e) => setFormData({...formData, role: e.target.value})}
                    placeholder="e.g., Senior React Developer"
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
                  <label htmlFor="team-assignment" style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Team Assignment *
                  </label>
                  <select
                    id="team-assignment"
                    required
                    value={formData.team_id}
                    onChange={(e) => setFormData({...formData, team_id: e.target.value})}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem'
                    }}
                  >
                    <option value=""></option>
                    {teams.map(team => (
                      <option key={team.id} value={team.id}>{team.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="agent-type" style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Agent Type
                  </label>
                  <select
                    id="agent-type"
                    value={formData.type}
                    onChange={(e) => setFormData({...formData, type: e.target.value})}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontSize: '0.875rem'
                    }}
                  >
                    <option value="developer">Developer</option>
                    <option value="executive">Executive</option>
                    <option value="qa">Quality Assurance</option>
                    <option value="devops">DevOps</option>
                    <option value="business">Business</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Template Selection */}
            <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', padding: '2rem'}}>
              <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem'}}>Agent Templates</h3>
              <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem'}}>
                Choose a template to pre-configure your agent
              </p>
              
              <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                {templates.map(template => (
                  <div 
                    key={template.id}
                    onClick={() => handleTemplateSelect(template)}
                    style={{
                      padding: '1rem',
                      border: formData.template_id === template.id ? '2px solid #2563eb' : '1px solid #e5e7eb',
                      borderRadius: '0.5rem',
                      cursor: 'pointer',
                      backgroundColor: formData.template_id === template.id ? '#f0f9ff' : 'white'
                    }}
                  >
                    <span style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', marginBottom: '0.25rem', display: 'block'}}>
                      {template.name}
                    </span>
                    <div style={{fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem'}}>
                      {template.description}
                    </div>
                    <div style={{fontSize: '0.75rem', color: '#9ca3af'}}>
                      Model: {template.defaultConfig.model}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Configuration Section */}
          <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', padding: '2rem', marginTop: '2rem'}}>
            <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem'}}>Agent Configuration</h3>
            
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem'}}>
              <div>
                <label htmlFor="config-model" style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Model
                </label>
                <select
                  id="config-model"
                  value={formData.config.model}
                  onChange={(e) => setFormData({...formData, config: {...formData.config, model: e.target.value}})}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem'
                  }}
                >
                  <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
                  <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                  <option value="gpt-4">GPT-4</option>
                </select>
              </div>

              <div>
                <label htmlFor="config-temperature" style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Temperature
                </label>
                <input
                  id="config-temperature"
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  value={formData.config.temperature}
                  onChange={(e) => setFormData({...formData, config: {...formData.config, temperature: parseFloat(e.target.value)}})}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem'
                  }}
                />
              </div>
            </div>

            <div style={{marginTop: '1.5rem'}}>
              <label htmlFor="config-goal" style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                Goal
              </label>
              <textarea
                id="config-goal"
                value={formData.config.goal}
                onChange={(e) => setFormData({...formData, config: {...formData.config, goal: e.target.value}})}
                placeholder="What is this agent's primary objective?"
                rows={2}
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

            <div style={{marginTop: '1.5rem'}}>
              <label htmlFor="config-backstory" style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                Backstory
              </label>
              <textarea
                id="config-backstory"
                value={formData.config.backstory}
                onChange={(e) => setFormData({...formData, config: {...formData.config, backstory: e.target.value}})}
                placeholder="Describe the agent's background and expertise"
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

            <div style={{marginTop: '1.5rem'}}>
              <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                Available Tools
              </label>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem', maxHeight: '200px', overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: '0.375rem', padding: '1rem'}}>
                {availableTools.map(tool => (
                  <label key={tool} style={{display: 'flex', alignItems: 'center', fontSize: '0.875rem'}}>
                    <input
                      type="checkbox"
                      checked={formData.config.tools.includes(tool)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormData({...formData, config: {...formData.config, tools: [...formData.config.tools, tool]}})
                        } else {
                          setFormData({...formData, config: {...formData.config, tools: formData.config.tools.filter(t => t !== tool)}})
                        }
                      }}
                      style={{marginRight: '0.5rem'}}
                    />
                    {tool.replace(/_/g, ' ')}
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Submit Error */}
          {submitError && (
            <p role="alert" style={{marginTop: '1rem', color: '#dc2626', fontSize: '0.875rem'}}>{submitError}</p>
          )}

          {/* Submit Button */}
          <div style={{marginTop: '2rem', display: 'flex', justifyContent: 'end', gap: '0.5rem'}}>
            <Link to="/agents" style={{
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
              disabled={creating}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: creating ? '#9ca3af' : '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                fontWeight: '500',
                cursor: creating ? 'not-allowed' : 'pointer'
              }}
            >
              {creating ? 'Creating...' : 'Create Agent'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}