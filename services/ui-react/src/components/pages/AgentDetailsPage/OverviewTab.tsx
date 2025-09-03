import React from 'react'
import type { Agent, Task, ContainerInfo, ChatMessage } from './types'

interface OverviewTabProps {
  agent: Agent
  tasks: Task[]
  chatMessages: ChatMessage[]
  containerInfo: ContainerInfo | null
  containerLoading: boolean
  handleCreateContainer: () => Promise<void>
  handleStartContainer: () => Promise<void>
  handleStopContainer: () => Promise<void>
  handleRestartContainer: () => Promise<void>
}

export function OverviewTab({ agent, tasks, chatMessages, containerInfo, containerLoading, handleCreateContainer, handleStartContainer, handleStopContainer, handleRestartContainer }: OverviewTabProps): JSX.Element {
  const completedTasks = tasks.filter((t: Task) => t.status === 'completed')
  const activeTasks = tasks.filter((t: Task) => t.status === 'in_progress')

  return (
    <div style={{display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem'}}>
      <div>
        <h3 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem'}}>Performance Overview</h3>
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem'}}>
          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{fontSize: '2rem', color: '#16a34a', textAlign: 'center', marginBottom: '0.5rem'}}>
              {completedTasks.length}
            </div>
            <div style={{fontSize: '0.875rem', color: '#6b7280', textAlign: 'center'}}>Tasks Completed</div>
          </div>
          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{fontSize: '2rem', color: '#2563eb', textAlign: 'center', marginBottom: '0.5rem'}}>
              {activeTasks.length}
            </div>
            <div style={{fontSize: '0.875rem', color: '#6b7280', textAlign: 'center'}}>Active Tasks</div>
          </div>
          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <div style={{fontSize: '2rem', color: '#ea580c', textAlign: 'center', marginBottom: '0.5rem'}}>
              {chatMessages.length}
            </div>
            <div style={{fontSize: '0.875rem', color: '#6b7280', textAlign: 'center'}}>Messages</div>
          </div>
        </div>

        <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
          <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Recent Activity</h4>
          <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
            {tasks.slice(0, 3).map((task: Task) => (
              <div key={task.id} style={{display: 'flex', alignItems: 'center', padding: '0.75rem', backgroundColor: '#f9fafb', borderRadius: '0.375rem'}}>
                <div style={{
                  width: '0.5rem',
                  height: '0.5rem',
                  borderRadius: '50%',
                  backgroundColor: task.status === 'completed' ? '#22c55e' : task.status === 'in_progress' ? '#2563eb' : '#6b7280',
                  marginRight: '0.75rem'
                }}></div>
                <div style={{flex: 1}}>
                  <div style={{fontSize: '0.875rem', fontWeight: '500', color: '#111827'}}>{task.title}</div>
                  <div style={{fontSize: '0.75rem', color: '#6b7280'}}>
                    {task.status} • {new Date(task.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb', marginBottom: '1rem'}}>
          <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Agent Information</h4>
          <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem'}}>
            <div style={{display: 'flex', justifyContent: 'space-between'}}>
              <span style={{color: '#6b7280'}}>Created:</span>
              <span>{new Date(agent.created_at).toLocaleDateString()}</span>
            </div>
            <div style={{display: 'flex', justifyContent: 'space-between'}}>
              <span style={{color: '#6b7280'}}>Last Updated:</span>
              <span>{new Date(agent.updated_at).toLocaleDateString()}</span>
            </div>
            <div style={{display: 'flex', justifyContent: 'space-between'}}>
              <span style={{color: '#6b7280'}}>Temperature:</span>
              <span>{agent.config?.temperature ?? 0.7}</span>
            </div>
            <div style={{display: 'flex', justifyContent: 'space-between'}}>
              <span style={{color: '#6b7280'}}>Tools:</span>
              <span>{agent.config?.tools?.length ?? 0}</span>
            </div>
          </div>
        </div>

        {containerInfo ? (
          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Container Status</h4>
            <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem'}}>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Status:</span>
                <span style={{
                  color: containerInfo.status === 'running' ? '#16a34a' : 
                        containerInfo.status === 'exited' ? '#dc2626' : '#ea580c'
                }}>
                  {containerInfo.status}
                </span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>CPU:</span>
                <span>{containerInfo.cpu_usage && typeof containerInfo.cpu_usage === 'number' ? `${containerInfo.cpu_usage.toFixed(1)}%` : 'N/A'}</span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Memory:</span>
                <span>
                  {containerInfo.memory_usage ? 
                    `${Math.round(containerInfo.memory_usage / (1024 * 1024))}MB` : 'N/A'}
                </span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Restarts:</span>
                <span>{containerInfo.restart_count}</span>
              </div>
            </div>

            <div style={{display: 'flex', gap: '0.5rem', marginTop: '1rem'}}>
              {containerInfo.status === 'running' ? (
                <React.Fragment>
                  <button 
                    onClick={handleStopContainer}
                    disabled={containerLoading}
                    style={{
                      flex: 1,
                      padding: '0.5rem',
                      backgroundColor: containerLoading ? '#9ca3af' : '#dc2626',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.375rem',
                      fontSize: '0.75rem',
                      cursor: containerLoading ? 'not-allowed' : 'pointer'
                    }}
                  >
                    {containerLoading ? 'Stopping...' : 'Stop'}
                  </button>
                  <button 
                    onClick={handleRestartContainer}
                    disabled={containerLoading}
                    style={{
                      flex: 1,
                      padding: '0.5rem',
                      backgroundColor: containerLoading ? '#9ca3af' : '#ea580c',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.375rem',
                      fontSize: '0.75rem',
                      cursor: containerLoading ? 'not-allowed' : 'pointer'
                    }}
                  >
                    {containerLoading ? 'Restarting...' : 'Restart'}
                  </button>
                </React.Fragment>
              ) : (
                <button 
                  onClick={handleStartContainer}
                  disabled={containerLoading}
                  style={{
                    flex: 1,
                    padding: '0.5rem',
                    backgroundColor: containerLoading ? '#9ca3af' : '#16a34a',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    fontSize: '0.75rem',
                    cursor: containerLoading ? 'not-allowed' : 'pointer'
                  }}
                >
                  {containerLoading ? 'Starting...' : 'Start'}
                </button>
              )}
            </div>
          </div>
        ) : (
          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Container Status</h4>
            <div style={{textAlign: 'center', padding: '1rem'}}>
              <div style={{fontSize: '2rem', marginBottom: '0.5rem'}}>📦</div>
              <p style={{color: '#6b7280', marginBottom: '1rem', fontSize: '0.875rem'}}>
                No container found for this agent
              </p>
              <button 
                onClick={handleCreateContainer}
                disabled={containerLoading}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: containerLoading ? '#9ca3af' : '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem',
                  cursor: containerLoading ? 'not-allowed' : 'pointer'
                }}
              >
                {containerLoading ? 'Creating...' : 'Create Container'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


