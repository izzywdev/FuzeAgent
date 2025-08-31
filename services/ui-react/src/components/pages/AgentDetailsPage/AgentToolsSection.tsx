import React, { useEffect, useState } from 'react'
import type { Agent } from './types'

interface Props {
  agent: Agent
  setAgent: (updater: (prev: Agent) => Agent) => void
}

type EffectiveTool = {
  tool_id: string
  key: string
  name: string
  enabled: boolean
  config: Record<string, any>
}

export function AgentToolsSection({ agent, setAgent }: Props): JSX.Element {
  const [tools, setTools] = useState<EffectiveTool[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!agent?.id) return
    setLoading(true)
    fetch(`/agents/${agent.id}/tools`).then(r => r.json()).then((list) => {
      if (Array.isArray(list)) setTools(list)
    }).finally(() => setLoading(false))
  }, [agent?.id])

  const toggle = async (tool: EffectiveTool, next: boolean) => {
    await fetch(`/agents/${agent.id}/tools/${tool.tool_id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: next })
    })
    setTools(prev => prev.map(t => t.tool_id === tool.tool_id ? { ...t, enabled: next } : t))
    // keep agent.config.tools in sync for legacy code paths
    setAgent(prev => {
      const current = prev.config?.tools || []
      const updated = next ? Array.from(new Set([...current, tool.key])) : current.filter((k: string) => k !== tool.key)
      return { ...prev, config: { ...prev.config, tools: updated } }
    })
  }

  return (
    <div>
      <label style={{display: 'block', fontSize: '0.875rem', fontWeight: '500', color: '#374151', marginBottom: '0.5rem'}}>Available Tools</label>
      {loading ? (
        <div style={{color: '#6b7280', fontSize: '0.875rem'}}>Loading tools...</div>
      ) : (
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.5rem', maxHeight: '260px', overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: '0.375rem', padding: '1rem'}}>
          {tools.map(tool => (
            <label key={tool.tool_id} style={{display: 'flex', alignItems: 'center', fontSize: '0.875rem', justifyContent: 'space-between'}}>
              <span style={{display: 'flex', alignItems: 'center'}}>
                <input
                  type="checkbox"
                  checked={tool.enabled}
                  onChange={(e) => toggle(tool, e.target.checked)}
                  style={{marginRight: '0.5rem'}}
                />
                <span title={tool.key}>{tool.name || tool.key}</span>
              </span>
              <span style={{fontSize: '0.75rem', color: '#9ca3af'}}>cfg: {Object.keys(tool.config || {}).length}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}


