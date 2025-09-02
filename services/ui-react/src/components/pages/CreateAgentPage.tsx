import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { EnvEditor } from '../common/EnvEditor'
import { useOrganization } from '../../contexts/OrganizationContext'
import { useApiService } from '../../hooks/useApiService'

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
  defaultDockerImage?: string
}

export function CreateAgentPage() {
  const navigate = useNavigate()
  const { currentOrganization } = useOrganization()
  const apiService = useApiService()
  const [teams, setTeams] = useState<Team[]>([])
  const [templates, setTemplates] = useState<AgentTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  
  const [formData, setFormData] = useState({
    name: '',
    role: '',
    type: 'developer',
    team_id: '',
    template_id: '',
    container_image: 'node:20-bullseye',
    container_env: {} as Record<string, string>,
    config: {
      model: 'claude-sonnet-4-20250514',
      temperature: 0.7,
      tools: [] as string[],
      goal: '',
      backstory: ''
    }
  })

  useEffect(() => {
    const loadData = async () => {
      try {
        // Load teams for the current organization
        if (currentOrganization) {
          const teamsResponse = await apiService.getTeams()
          if (teamsResponse.ok && Array.isArray(teamsResponse.data)) {
            setTeams(teamsResponse.data)
          } else {
            setTeams([])
          }
        } else {
          setTeams([])
        }

        // Load agent templates
        const templatesResponse = await apiService.getAgentTemplates()
        if (templatesResponse.ok) {
          const data = templatesResponse.data
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
              },
              defaultDockerImage: template.default_docker_image || template.default_container_image || template.docker_image || template.container_image || ''
            }))
            setTemplates(transformedTemplates)
          } else if (Array.isArray(data)) {
            // Some backends (including our mock API) return a flat array of templates
            // Normalize it to the shape expected by the UI
            const normalizedTemplates = data.map((template: any) => ({
              id: template.id || template.template_id,
              name: template.name,
              description: template.description || '',
              type: template.type || template.category || 'developer',
              defaultConfig: {
                model: template.default_model || template.model || 'claude-sonnet-4-20250514',
                temperature: template.default_temperature ?? 0.7,
                tools: Array.isArray(template.tools) ? template.tools : [],
                goal: template.default_goal || '',
                backstory: template.default_backstory || ''
              },
              defaultDockerImage: template.default_docker_image || template.default_container_image || template.docker_image || template.container_image || ''
            }))
            setTemplates(normalizedTemplates)
          } else {
            // No templates available
            setTemplates([])
          }
        } else {
          console.error('Failed to load templates:', templatesResponse.status)
          setTemplates([])
        }
      } catch (err) {
        console.error('Failed to load data:', err)
        setTeams([])
        setTemplates([])
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [currentOrganization, apiService])

  // Templates will be fetched from API

  const handleTemplateSelect = (template: AgentTemplate) => {
    setFormData({
      ...formData,
      type: template.type,
      template_id: template.id,
      role: template.name,
      container_image: template.defaultDockerImage || formData.container_image || 'node:20-bullseye',
      container_env: {},
      config: {
        ...template.defaultConfig,
        tools: [...template.defaultConfig.tools]
      }
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)

    if (!currentOrganization) {
      alert('No organization selected. Please select an organization first.')
      setCreating(false)
      return
    }

    try {
      const response = await apiService.createAgent({
        name: formData.name,
        role: formData.role,
        type: formData.type,
        team_id: formData.team_id,
        container_image: formData.container_image,
        container_env: formData.container_env,
        config: formData.config
      })

      if (response.ok) {
        const newAgent = response.data
        // Handle different possible response structures
        const agentId = newAgent.agent_id || newAgent.agent?.id || newAgent.id
        if (agentId) {
          navigate(`/agents/${agentId}`)
        } else {
          console.error('No agent ID found in response:', newAgent)
          alert('Agent created but unable to navigate. Please check the agents list.')
        }
      } else {
        alert(`Failed to create agent: HTTP ${response.status}`)
      }
    } catch (error) {
      console.error('Error creating agent:', error)
      alert('Error creating agent. Please check your connection.')
    } finally {
      setCreating(false)
    }
  }

  const [teamTools, setTeamTools] = useState<Array<{ tool: { id: string, key: string, name: string }, setting: { enabled: boolean, config_override?: Record<string, any> } }>>([])

  useEffect(() => {
    const tid = formData.team_id
    if (!tid) { 
      setTeamTools([])
      return 
    }
    
    const loadTeamTools = async () => {
      try {
        const response = await apiService.getTeamTools(tid)
        if (response.ok && Array.isArray(response.data)) {
          setTeamTools(response.data)
        } else {
          setTeamTools([])
        }
      } catch (error) {
        console.error('Failed to load team tools:', error)
        setTeamTools([])
      }
    }
    
    loadTeamTools()
  }, [formData.team_id, apiService])

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
                <span style={{color: '#111827'}}>Create Agent</span>
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
                {/* Current Organization Display */}
                {currentOrganization && (
                  <div style={{padding: '1rem', backgroundColor: '#f3f4f6', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
                    <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.25rem'}}>
                      Creating agent for:
                    </div>
                    <div style={{fontSize: '1rem', fontWeight: '600', color: '#111827'}}>
                      {currentOrganization.name}
                    </div>
                  </div>
                )}
                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Agent Name *
                  </label>
                  <input
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
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Role *
                  </label>
                  <input
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
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Team Assignment *
                  </label>
                  <select
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
                    <option value="">Select a team...</option>
                    {teams.map(team => (
                      <option key={team.id} value={team.id}>{team.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                    Agent Type
                  </label>
                  <select
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
                    <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827', marginBottom: '0.25rem'}}>
                      {template.name}
                    </div>
                    <div style={{fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem'}}>
                      {template.description}
                    </div>
                    <div style={{display: 'flex', gap: '1rem', fontSize: '0.75rem', color: '#9ca3af'}}>
                      <span>Model: {template.defaultConfig?.model || 'claude-sonnet-4-20250514'}</span>
                      {template.defaultDockerImage && (
                        <span>Image: {template.defaultDockerImage}</span>
                      )}
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
                <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Model
                </label>
                <select
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
                <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                  Temperature
                </label>
                <input
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
              <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                Goal
              </label>
              <textarea
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
              <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
                Backstory
              </label>
              <textarea
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
                Available Tools (from Team Settings)
              </label>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '0.5rem', maxHeight: '220px', overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: '0.375rem', padding: '1rem'}}>
                {teamTools.map(({ tool, setting }) => (
                  <label key={tool.id} style={{display: 'flex', alignItems: 'center', fontSize: '0.875rem'}}>
                    <input
                      type="checkbox"
                      checked={formData.config.tools.includes(tool.key)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormData({...formData, config: {...formData.config, tools: [...formData.config.tools, tool.key]}})
                        } else {
                          setFormData({...formData, config: {...formData.config, tools: formData.config.tools.filter(t => t !== tool.key)}})
                        }
                      }}
                      style={{marginRight: '0.5rem'}}
                    />
                    <span title={tool.key}>{tool.name || tool.key}</span>
                    {!setting.enabled && <span style={{marginLeft: '0.5rem', fontSize: '0.75rem', color: '#9ca3af'}}>(team disabled)</span>}
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div style={{marginTop: '1.5rem'}}>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
              Docker Image
            </label>
            <select
              value={formData.container_image}
              onChange={(e) => setFormData({...formData, container_image: e.target.value})}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem'
              }}
            >
              <option value="node:20-bullseye">node:20-bullseye</option>
              <option value="node:20-alpine">node:20-alpine</option>
              <option value="python:3.11-slim">python:3.11-slim</option>
              <option value="python:3.11-alpine">python:3.11-alpine</option>
            </select>
          </div>

          <div style={{marginTop: '1.5rem'}}>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>
              Environment Variables
            </label>
            <EnvEditor
              value={formData.container_env}
              onChange={(env) => setFormData({...formData, container_env: env})}
            />
          </div>

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