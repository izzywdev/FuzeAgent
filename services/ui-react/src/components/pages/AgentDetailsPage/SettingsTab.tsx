import React from 'react'
import type { Agent } from './types'

interface SettingsTabProps {
  agent: Agent
  saving: boolean
  setAgent: (updater: (prev: Agent) => Agent) => void
  onSave: () => Promise<void>
}

export function SettingsTab({ agent, saving, setAgent, onSave }: SettingsTabProps): JSX.Element {
  return (
    <div style={{maxWidth: '50rem'}}>
      <div style={{backgroundColor: 'white', padding: '2rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
        <h3 style={{fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem'}}>Agent Configuration</h3>
        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          <div>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Agent Name</label>
            <input type="text" value={agent.name} readOnly style={{width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem'}} />
          </div>
          <div>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Role</label>
            <input type="text" value={agent.role} readOnly style={{width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem'}} />
          </div>
          <div>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Goal</label>
            <textarea value={agent.config.goal || ''} readOnly rows={3} style={{width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem', resize: 'vertical'}} />
          </div>
          <div>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Backstory</label>
            <textarea value={agent.config.backstory || ''} readOnly rows={3} style={{width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem', resize: 'vertical'}} />
          </div>
          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
            <div>
              <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Model</label>
              <select style={{width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem'}}>
                <option value={agent.config?.model || 'claude-sonnet-4-20250514'}>{agent.config?.model || 'claude-sonnet-4-20250514'}</option>
                <option value="claude-3-opus-20240229">claude-3-opus-20240229</option>
                <option value="gpt-4">gpt-4</option>
              </select>
            </div>
            <div>
              <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Temperature</label>
              <input type="number" value={agent.config?.temperature ?? 0.7} readOnly min="0" max="2" step="0.1" style={{width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem'}} />
            </div>
          </div>
          <div>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Docker Image</label>
            <select
              value={agent.container_image || 'node:20-bullseye'}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                const value = e.target.value
                setAgent(prev => ({ ...prev, container_image: value }))
              }}
              style={{width: '100%', padding: '0.75rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem'}}
            >
              <option value="node:20-bullseye">node:20-bullseye</option>
              <option value="node:20-alpine">node:20-alpine</option>
              <option value="python:3.11-slim">python:3.11-slim</option>
              <option value="python:3.11-alpine">python:3.11-alpine</option>
            </select>
          </div>
          <div>
            <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Available Tools</label>
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem', maxHeight: '220px', overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: '0.375rem', padding: '1rem'}}>
              {[
                'code_generation','code_review','debugging','testing','api_development',
                'database_design','infrastructure_management','deployment','monitoring',
                'security','performance_testing','test_automation','bug_reporting',
                'quality_analysis','strategic_planning','team_management','resource_allocation'
              ].map(tool => (
                <label key={tool} style={{display: 'flex', alignItems: 'center', fontSize: '0.875rem'}}>
                  <input
                    type="checkbox"
                    checked={(agent.config?.tools || []).includes(tool)}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                      const current = agent.config?.tools || []
                      const updated = e.target.checked ? [...current, tool] : current.filter((t: string) => t !== tool)
                      setAgent(prev => ({ ...prev, config: { ...prev.config, tools: updated } }))
                    }}
                    style={{marginRight: '0.5rem'}}
                  />
                  {tool.replace(/_/g, ' ')}
                </label>
              ))}
            </div>
          </div>
          <div style={{display: 'flex', gap: '0.5rem', paddingTop: '1rem'}}>
            <button disabled={saving} onClick={onSave} style={{padding: '0.75rem 1.5rem', backgroundColor: saving ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', fontWeight: '500', cursor: saving ? 'not-allowed' : 'pointer'}}>
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button style={{padding: '0.75rem 1.5rem', border: '1px solid #d1d5db', backgroundColor: 'white', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}>
              Reset
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}


