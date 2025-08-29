import React from 'react'
import type { Task } from './types'

interface AssignTaskModalProps {
  open: boolean
  onClose: () => void
  teamTasks: Task[]
  selectedTeamTaskId: string
  onChangeSelected: (id: string) => void
  assigning: boolean
  error: string | null
  onAssign: () => Promise<void>
}

export function AssignTaskModal({ open, onClose, teamTasks, selectedTeamTaskId, onChangeSelected, assigning, error, onAssign }: AssignTaskModalProps): JSX.Element | null {
  if (!open) return null
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div style={{ backgroundColor: 'white', borderRadius: '0.75rem', padding: '1.5rem', width: '36rem', maxWidth: '95vw' }}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem'}}>
          <h3 style={{fontSize: '1.125rem', fontWeight: 600, margin: 0}}>Assign Task</h3>
          <button onClick={onClose} style={{ padding: '0.25rem 0.5rem', border: 'none', borderRadius: '0.375rem', backgroundColor: '#f3f4f6', cursor: 'pointer' }}>✕</button>
        </div>
        {error && (
          <div style={{ marginBottom: '0.75rem', padding: '0.5rem 0.75rem', backgroundColor: '#fee2e2', border: '1px solid #ef4444', color: '#b91c1c', borderRadius: '0.375rem', fontSize: '0.875rem' }}>{error}</div>
        )}
        <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
          <div>
            <label style={{display: 'block', fontSize: '0.875rem', color: '#374151', marginBottom: '0.25rem'}}>Select Team Task</label>
            <select value={selectedTeamTaskId} onChange={(e: React.ChangeEvent<HTMLSelectElement>) => onChangeSelected(e.target.value)} style={{width: '100%', padding: '0.5rem 0.75rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', fontSize: '0.875rem'}}>
              <option value="">-- Choose a task --</option>
              {teamTasks.map((t: Task) => (
                <option key={t.id} value={t.id}>{t.title} {(t as any).agent_id ? '(assigned)' : ''}</option>
              ))}
            </select>
            <p style={{fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem'}}>Only tasks created for this agent's team are listed.</p>
          </div>
        </div>
        <div style={{display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem'}}>
          <button onClick={onClose} style={{ padding: '0.5rem 1rem', border: '1px solid #d1d5db', borderRadius: '0.375rem', backgroundColor: 'white', cursor: 'pointer', fontSize: '0.875rem' }}>Cancel</button>
          <button onClick={onAssign} disabled={assigning} style={{ padding: '0.5rem 1rem', backgroundColor: assigning ? '#93c5fd' : '#2563eb', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: assigning ? 'not-allowed' : 'pointer' }}>{assigning ? 'Assigning...' : 'Assign Task'}</button>
        </div>
      </div>
    </div>
  )
}


