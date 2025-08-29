import React from 'react'
import { Link } from 'react-router-dom'
import type { Agent } from './types'

interface TopNavProps {
  agent: Agent
}

export function TopNav({ agent }: TopNavProps): JSX.Element {
  return (
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
            <div style={{display: 'flex', alignItems: 'center', marginLeft: '1.5rem', color: '#6b7280', fontSize: '0.875rem'}}>
              <Link to="/agents" style={{color: '#6b7280', textDecoration: 'none'}}>Agents</Link>
              <span style={{margin: '0 0.5rem'}}>›</span>
              <span style={{color: '#111827'}}>{agent.name}</span>
            </div>
          </div>
          <div style={{display: 'flex', gap: '0.5rem'}}>
            <button style={{
              padding: '0.5rem 1rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              backgroundColor: 'white',
              cursor: 'pointer'
            }}>
              Edit Agent
            </button>
            <button style={{
              padding: '0.5rem 1rem',
              backgroundColor: agent.status === 'active' ? '#dc2626' : '#16a34a',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              cursor: 'pointer'
            }}>
              {agent.status === 'active' ? 'Deactivate' : 'Activate'}
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}


