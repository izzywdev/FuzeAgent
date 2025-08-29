import React from 'react'
import type { Task } from './types'

interface TasksTabProps {
  tasks: Task[]
  teamId?: string
  onOpenAssign: () => void
}

export function TasksTab({ tasks, onOpenAssign }: TasksTabProps): JSX.Element {
  return (
    <div>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
        <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Agent Tasks</h3>
        <button onClick={onOpenAssign} style={{padding: '0.5rem 1rem', backgroundColor: '#2563eb', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}>+ Assign Task</button>
      </div>
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem'}}>
        {tasks.map((task: Task) => (
          <div key={task.id} style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem'}}>
              <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: 0}}>{task.title}</h4>
              <div style={{padding: '0.25rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem', fontWeight: '500', backgroundColor: task.status === 'completed' ? '#dcfce7' : task.status === 'in_progress' ? '#dbeafe' : '#f3f4f6', color: task.status === 'completed' ? '#15803d' : task.status === 'in_progress' ? '#1d4ed8' : '#374151'}}>
                {task.status}
              </div>
            </div>
            <p style={{fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem', lineHeight: '1.5'}}>
              {task.description}
            </p>
            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#9ca3af'}}>
              <span>Priority: {task.priority}</span>
              <span>{new Date(task.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


