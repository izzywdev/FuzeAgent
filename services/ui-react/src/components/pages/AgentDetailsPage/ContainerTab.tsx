import React from 'react'
import type { ContainerInfo } from './types'

interface ContainerTabProps {
  containerInfo: ContainerInfo | null
  containerLoading: boolean
  onCreate: () => Promise<void>
  onStart: () => Promise<void>
  onStop: () => Promise<void>
  onRestart: () => Promise<void>
  onRefresh: () => Promise<void>
  onViewLogs: () => Promise<void>
}

export function ContainerTab(props: ContainerTabProps): JSX.Element {
  const { containerInfo, containerLoading, onCreate, onStart, onStop, onRestart, onRefresh, onViewLogs } = props

  return (
    <div>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
        <h3 style={{fontSize: '1.25rem', fontWeight: '600'}}>Container Management</h3>
        <div style={{display: 'flex', gap: '0.5rem'}}>
          {containerInfo ? (
            <>
              <button onClick={onViewLogs} style={{padding: '0.5rem 1rem', border: '1px solid #d1d5db', backgroundColor: 'white', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}>View Live Logs</button>
              <button onClick={onRefresh} style={{padding: '0.5rem 1rem', border: '1px solid #d1d5db', backgroundColor: 'white', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: 'pointer'}}>Refresh</button>
            </>
          ) : (
            <button onClick={onCreate} disabled={containerLoading} style={{padding: '0.5rem 1rem', backgroundColor: containerLoading ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: containerLoading ? 'not-allowed' : 'pointer'}}>
              {containerLoading ? 'Creating...' : 'Create Container'}
            </button>
          )}
        </div>
      </div>

      {containerInfo ? (
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem'}}>
          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Container Details</h4>
            <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.875rem'}}>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Container ID:</span>
                <span style={{fontFamily: 'monospace', fontSize: '0.75rem'}}>{containerInfo.id}</span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Name:</span>
                <span>{containerInfo.name}</span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Image:</span>
                <span>{containerInfo.image}</span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Status:</span>
                <span style={{color: containerInfo.status === 'running' ? '#16a34a' : containerInfo.status === 'exited' ? '#dc2626' : '#ea580c'}}>{containerInfo.status}</span>
              </div>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Created:</span>
                <span>{new Date(containerInfo.created).toLocaleString()}</span>
              </div>
              {containerInfo.started && (
                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                  <span style={{color: '#6b7280'}}>Started:</span>
                  <span>{new Date(containerInfo.started).toLocaleString()}</span>
                </div>
              )}
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <span style={{color: '#6b7280'}}>Restart Count:</span>
                <span>{containerInfo.restart_count}</span>
              </div>
              {containerInfo.health && (
                <div style={{display: 'flex', justifyContent: 'space-between'}}>
                  <span style={{color: '#6b7280'}}>Health:</span>
                  <span style={{color: containerInfo.health === 'healthy' ? '#16a34a' : containerInfo.health === 'unhealthy' ? '#dc2626' : '#ea580c'}}>{containerInfo.health}</span>
                </div>
              )}
            </div>

            {Object.keys(containerInfo.ports).length > 0 && (
              <div style={{marginTop: '1.5rem'}}>
                <h5 style={{fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem'}}>Port Mappings</h5>
                <div style={{fontSize: '0.75rem', fontFamily: 'monospace', color: '#6b7280'}}>
                  {Object.entries(containerInfo.ports).map(([containerPort, hostPort]) => (
                    <div key={containerPort}>{hostPort} → {containerPort}</div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div style={{backgroundColor: 'white', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb'}}>
            <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>Resource Usage & Controls</h4>
            <div style={{display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem'}}>
              <div>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem'}}>
                  <span style={{fontSize: '0.875rem', color: '#6b7280'}}>CPU Usage</span>
                  <span style={{fontSize: '0.875rem'}}>{containerInfo.cpu_usage ? `${containerInfo.cpu_usage.toFixed(1)}%` : 'N/A'}</span>
                </div>
                <div style={{width: '100%', height: '0.5rem', backgroundColor: '#f3f4f6', borderRadius: '0.25rem', overflow: 'hidden'}}>
                  <div style={{width: containerInfo.cpu_usage ? `${containerInfo.cpu_usage}%` : '0%', height: '100%', backgroundColor: '#3b82f6'}}></div>
                </div>
              </div>
              <div>
                <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem'}}>
                  <span style={{fontSize: '0.875rem', color: '#6b7280'}}>Memory Usage</span>
                  <span style={{fontSize: '0.875rem'}}>
                    {containerInfo.memory_usage && containerInfo.memory_limit ? `${Math.round(containerInfo.memory_usage / (1024 * 1024))}MB / ${Math.round(containerInfo.memory_limit / (1024 * 1024))}MB` : containerInfo.memory_usage ? `${Math.round(containerInfo.memory_usage / (1024 * 1024))}MB` : 'N/A'}
                  </span>
                </div>
                <div style={{width: '100%', height: '0.5rem', backgroundColor: '#f3f4f6', borderRadius: '0.25rem', overflow: 'hidden'}}>
                  <div style={{width: containerInfo.memory_usage && containerInfo.memory_limit ? `${(containerInfo.memory_usage / containerInfo.memory_limit) * 100}%` : '0%', height: '100%', backgroundColor: '#10b981'}}></div>
                </div>
              </div>
            </div>

            <div style={{display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
              {containerInfo.status === 'running' ? (
                <>
                  <button onClick={onStop} disabled={containerLoading} style={{padding: '0.75rem', backgroundColor: containerLoading ? '#9ca3af' : '#dc2626', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: containerLoading ? 'not-allowed' : 'pointer'}}>
                    {containerLoading ? 'Stopping...' : 'Stop Container'}
                  </button>
                  <button onClick={onRestart} disabled={containerLoading} style={{padding: '0.75rem', backgroundColor: containerLoading ? '#9ca3af' : '#ea580c', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: containerLoading ? 'not-allowed' : 'pointer'}}>
                    {containerLoading ? 'Restarting...' : 'Restart Container'}
                  </button>
                </>
              ) : (
                <button onClick={onStart} disabled={containerLoading} style={{padding: '0.75rem', backgroundColor: containerLoading ? '#9ca3af' : '#16a34a', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: containerLoading ? 'not-allowed' : 'pointer'}}>
                  {containerLoading ? 'Starting...' : 'Start Container'}
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div style={{backgroundColor: 'white', padding: '3rem', borderRadius: '0.5rem', border: '1px solid #e5e7eb', textAlign: 'center'}}>
          <div style={{fontSize: '3rem', marginBottom: '1rem'}}>📦</div>
          <h4 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.5rem', color: '#111827'}}>No Container Found</h4>
          <p style={{color: '#6b7280', marginBottom: '1.5rem'}}>This agent doesn't have a container yet. Create one to enable code execution and advanced capabilities.</p>
          <button onClick={onCreate} disabled={containerLoading} style={{padding: '0.75rem 1.5rem', backgroundColor: containerLoading ? '#9ca3af' : '#2563eb', color: 'white', border: 'none', borderRadius: '0.375rem', fontSize: '0.875rem', cursor: containerLoading ? 'not-allowed' : 'pointer'}}>
            {containerLoading ? 'Creating Container...' : 'Create Container'}
          </button>
        </div>
      )}
    </div>
  )
}


