import React from 'react'
import type { Agent } from './types'

interface HeaderProps {
  agent: Agent
}

export function Header({ agent }: HeaderProps): JSX.Element {
  return (
    <div style={{backgroundColor: 'white', borderBottom: '1px solid #e5e7eb'}}>
      <div style={{maxWidth: '80rem', margin: '0 auto', padding: '2rem 1rem'}}>
        <div style={{display: 'flex', alignItems: 'center'}}>
          <div style={{
            width: '5rem',
            height: '5rem',
            backgroundColor: '#f3f4f6',
            borderRadius: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: '1.5rem'
          }}>
            <span style={{fontSize: '2.5rem'}}>🤖</span>
          </div>
          <div style={{flex: 1}}>
            <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem'}}>
              <h1 style={{fontSize: '1.875rem', fontWeight: 'bold', color: '#111827', margin: 0}}>{agent.name}</h1>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: '0.25rem 0.75rem',
                borderRadius: '1rem',
                backgroundColor: agent.status === 'active' ? '#dcfce7' : '#fef3c7',
                fontSize: '0.75rem',
                fontWeight: '500'
              }}>
                <div style={{
                  width: '0.5rem',
                  height: '0.5rem',
                  borderRadius: '50%',
                  backgroundColor: agent.status === 'active' ? '#22c55e' : '#eab308',
                  marginRight: '0.5rem'
                }}></div>
                {agent.status}
              </div>
            </div>
            <p style={{fontSize: '1.125rem', color: '#6b7280', margin: '0 0 0.5rem 0'}}>{agent.role}</p>
            <div style={{display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#6b7280'}}>
              <span>Type: <strong>{agent.type}</strong></span>
              <span>Team: <strong>{agent.team_name || 'Unassigned'}</strong></span>
              <span>Model: <strong>{agent.config?.model || 'claude-sonnet-4-20250514'}</strong></span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


