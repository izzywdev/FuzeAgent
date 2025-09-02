import React, { useState, useEffect } from 'react'
import { useApiService } from '../../hooks/useApiService'

interface Props {
  teamId: string
  onToolsChange: () => void
}

type TeamTool = {
  tool: {
    id: string
    key: string
    name: string
    description?: string
    default_config: Record<string, any>
  }
  setting: {
    enabled: boolean
    config_override?: Record<string, any>
  }
}

export function TeamToolsSection({ teamId, onToolsChange }: Props): JSX.Element {
  const apiService = useApiService()
  const [tools, setTools] = useState<TeamTool[]>([])
  const [loading, setLoading] = useState(false)
  const [editingTool, setEditingTool] = useState<TeamTool | null>(null)
  const [configOverride, setConfigOverride] = useState('{}')

  useEffect(() => {
    if (teamId) {
      loadTeamTools()
    }
  }, [teamId])

  const loadTeamTools = async () => {
    setLoading(true)
    try {
      const response = await apiService.getTeamTools(teamId)
      if (response.ok) {
        setTools(response.data)
      } else {
        console.error('Error loading team tools:', response.status)
      }
    } catch (error) {
      console.error('Error loading team tools:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleTool = async (tool: TeamTool, enabled: boolean) => {
    try {
      const response = await apiService.updateTeamTool(teamId, tool.tool.id, { 
        enabled,
        config_override: tool.setting.config_override
      })
      if (response.ok) {
        await loadTeamTools()
        onToolsChange()
      } else {
        console.error('Error updating tool setting:', response.status)
      }
    } catch (error) {
      console.error('Error updating tool setting:', error)
    }
  }

  const updateConfigOverride = async (tool: TeamTool) => {
    if (!editingTool) return
    try {
      const parsedConfig = JSON.parse(configOverride)
      const response = await apiService.updateTeamTool(teamId, tool.tool.id, { 
        enabled: tool.setting.enabled,
        config_override: parsedConfig
      })
      if (response.ok) {
        setEditingTool(null)
        setConfigOverride('{}')
        await loadTeamTools()
        onToolsChange()
      } else {
        console.error('Error updating tool config:', response.status)
      }
    } catch (error) {
      console.error('Error updating tool config:', error)
      alert('Invalid JSON configuration')
    }
  }

  const startEditConfig = (tool: TeamTool) => {
    setEditingTool(tool)
    setConfigOverride(JSON.stringify(tool.setting.config_override || {}, null, 2))
  }

  const cancelEdit = () => {
    setEditingTool(null)
    setConfigOverride('{}')
  }

  if (loading) {
    return (
      <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', marginTop: '2rem', padding: '2rem'}}>
        <div style={{textAlign: 'center', color: '#6b7280'}}>Loading team tools...</div>
      </div>
    )
  }

  return (
    <div style={{backgroundColor: 'white', borderRadius: '0.75rem', border: '1px solid #e5e7eb', marginTop: '2rem', padding: '2rem'}}>
      <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem'}}>Team Tools</h3>
      
      <div style={{display: 'grid', gap: '1rem'}}>
        {tools.map(tool => (
          <div key={tool.tool.id} style={{
            border: '1px solid #e5e7eb',
            borderRadius: '0.5rem',
            padding: '1rem',
            backgroundColor: tool.setting.enabled ? 'white' : '#f9fafb'
          }}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
              <div style={{flex: 1}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem'}}>
                  <h4 style={{fontSize: '1rem', fontWeight: '600', margin: 0}}>{tool.tool.name}</h4>
                  <span style={{
                    fontSize: '0.75rem',
                    padding: '0.25rem 0.5rem',
                    backgroundColor: tool.setting.enabled ? '#dcfce7' : '#fee2e2',
                    color: tool.setting.enabled ? '#15803d' : '#dc2626',
                    borderRadius: '0.25rem'
                  }}>
                    {tool.setting.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: '0 0 0.5rem 0'}}>
                  <strong>Key:</strong> {tool.tool.key}
                </p>
                {tool.tool.description && (
                  <p style={{fontSize: '0.875rem', color: '#6b7280', margin: '0 0 0.5rem 0'}}>
                    {tool.tool.description}
                  </p>
                )}
                <div style={{fontSize: '0.75rem', color: '#9ca3af'}}>
                  <strong>Default Config:</strong> {Object.keys(tool.tool.default_config || {}).length} properties
                  {tool.setting.config_override && (
                    <span style={{marginLeft: '1rem'}}>
                      <strong>Override:</strong> {Object.keys(tool.setting.config_override).length} properties
                    </span>
                  )}
                </div>
              </div>
              <div style={{display: 'flex', gap: '0.5rem', alignItems: 'center'}}>
                <label style={{display: 'flex', alignItems: 'center', fontSize: '0.875rem'}}>
                  <input
                    type="checkbox"
                    checked={tool.setting.enabled}
                    onChange={(e) => toggleTool(tool, e.target.checked)}
                    style={{marginRight: '0.5rem'}}
                  />
                  Enable
                </label>
                <button
                  onClick={() => startEditConfig(tool)}
                  style={{
                    padding: '0.25rem 0.5rem',
                    backgroundColor: 'white',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.25rem',
                    fontSize: '0.75rem',
                    cursor: 'pointer'
                  }}
                >
                  ⚙️ Config
                </button>
              </div>
            </div>

            {/* Config Override Editor */}
            {editingTool?.tool.id === tool.tool.id && (
              <div style={{
                marginTop: '1rem',
                padding: '1rem',
                backgroundColor: '#f9fafb',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem'
              }}>
                <h5 style={{fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem'}}>
                  Configuration Override (JSON)
                </h5>
                <p style={{fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem'}}>
                  Leave empty to use organization default, or specify custom configuration
                </p>
                <textarea
                  value={configOverride}
                  onChange={(e) => setConfigOverride(e.target.value)}
                  placeholder='{"model": "custom-model", "temperature": 0.8}'
                  rows={4}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    fontFamily: 'monospace',
                    resize: 'vertical',
                    marginBottom: '0.5rem'
                  }}
                />
                <div style={{display: 'flex', gap: '0.5rem'}}>
                  <button
                    onClick={() => updateConfigOverride(tool)}
                    style={{
                      padding: '0.25rem 0.5rem',
                      backgroundColor: '#2563eb',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}
                  >
                    Save Override
                  </button>
                  <button
                    onClick={cancelEdit}
                    style={{
                      padding: '0.25rem 0.5rem',
                      backgroundColor: 'white',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        
        {tools.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '2rem',
            color: '#6b7280',
            fontSize: '0.875rem'
          }}>
            No tools available for this team. Tools are configured at the organization level.
          </div>
        )}
      </div>
    </div>
  )
}
