import { useState, useEffect } from 'react'
import { useDashboardWebSocket, type WebSocketMessage } from '../hooks/useWebSocket'

export interface Notification {
  id: string
  type: 'success' | 'info' | 'warning' | 'error'
  title: string
  message: string
  timestamp: Date
  autoHide?: boolean
  duration?: number
  actionLabel?: string
  onAction?: () => void
}

interface NotificationSystemProps {
  organizationId?: string
  teamId?: string
  maxNotifications?: number
}

export function NotificationSystem({ 
  organizationId, 
  teamId, 
  maxNotifications = 5 
}: NotificationSystemProps) {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isVisible] = useState(true)
  
  const { isConnected, lastMessage, connectionStatus } = useDashboardWebSocket({
    organizationId,
    teamId
  })

  // Process WebSocket messages into notifications
  useEffect(() => {
    if (!lastMessage) return

    const notification = createNotificationFromMessage(lastMessage)
    if (notification) {
      addNotification(notification)
    }
  }, [lastMessage])

  const createNotificationFromMessage = (message: WebSocketMessage): Notification | null => {
    const { type, data, timestamp } = message

    switch (type) {
      case 'agent_status':
        if (data.status === 'active') {
          return {
            id: `agent-${message.agent_id}-${Date.now()}`,
            type: 'success',
            title: 'Agent Activated',
            message: `Agent is now active and ready to work`,
            timestamp: new Date(timestamp),
            autoHide: true,
            duration: 5000
          }
        } else if (data.status === 'error') {
          return {
            id: `agent-${message.agent_id}-${Date.now()}`,
            type: 'error',
            title: 'Agent Error',
            message: data.message || 'An error occurred with the agent',
            timestamp: new Date(timestamp),
            autoHide: false
          }
        }
        break

      case 'agent_created':
        return {
          id: `agent-created-${message.target_id}-${Date.now()}`,
          type: 'success',
          title: 'New Agent Created',
          message: `Agent "${data.name}" has been created successfully`,
          timestamp: new Date(timestamp),
          autoHide: true,
          duration: 5000
        }

      case 'task_completed':
        return {
          id: `task-${message.target_id}-${Date.now()}`,
          type: 'success',
          title: 'Task Completed',
          message: data.title || 'A task has been completed',
          timestamp: new Date(timestamp),
          autoHide: true,
          duration: 7000
        }

      case 'container_status':
        if (data.container_status === 'started') {
          return {
            id: `container-${message.agent_id}-${Date.now()}`,
            type: 'info',
            title: 'Container Started',
            message: 'Agent container is now running',
            timestamp: new Date(timestamp),
            autoHide: true,
            duration: 4000
          }
        } else if (data.container_status === 'stopped') {
          return {
            id: `container-${message.agent_id}-${Date.now()}`,
            type: 'warning',
            title: 'Container Stopped',
            message: 'Agent container has been stopped',
            timestamp: new Date(timestamp),
            autoHide: true,
            duration: 5000
          }
        }
        break

      case 'knowledge_updated':
        return {
          id: `knowledge-${Date.now()}`,
          type: 'info',
          title: 'Knowledge Base Updated',
          message: data.document_title ? 
            `Document "${data.document_title}" has been added to the knowledge base` :
            'Knowledge base has been updated',
          timestamp: new Date(timestamp),
          autoHide: true,
          duration: 5000
        }

      case 'system_notification':
        return {
          id: `system-${Date.now()}`,
          type: 'info',
          title: 'System Notification',
          message: data.message || 'System notification received',
          timestamp: new Date(timestamp),
          autoHide: true,
          duration: 5000
        }

      case 'system_error':
        return {
          id: `error-${Date.now()}`,
          type: 'error',
          title: 'System Error',
          message: data.error || 'A system error occurred',
          timestamp: new Date(timestamp),
          autoHide: false
        }

      default:
        return null
    }

    return null
  }

  const addNotification = (notification: Notification) => {
    setNotifications(prev => {
      const updated = [notification, ...prev].slice(0, maxNotifications)
      
      // Auto-hide if configured
      if (notification.autoHide) {
        setTimeout(() => {
          removeNotification(notification.id)
        }, notification.duration || 5000)
      }
      
      return updated
    })
  }

  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const clearAllNotifications = () => {
    setNotifications([])
  }

  const getNotificationIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success': return '✅'
      case 'info': return 'ℹ️'
      case 'warning': return '⚠️'
      case 'error': return '❌'
      default: return 'ℹ️'
    }
  }

  const getNotificationColor = (type: Notification['type']) => {
    switch (type) {
      case 'success': return { bg: '#dcfce7', border: '#16a34a', text: '#15803d' }
      case 'info': return { bg: '#dbeafe', border: '#2563eb', text: '#1d4ed8' }
      case 'warning': return { bg: '#fef3c7', border: '#d97706', text: '#92400e' }
      case 'error': return { bg: '#fee2e2', border: '#dc2626', text: '#dc2626' }
      default: return { bg: '#f3f4f6', border: '#6b7280', text: '#374151' }
    }
  }

  if (!isVisible || notifications.length === 0) {
    return (
      // Connection status indicator
      <div style={{
        position: 'fixed',
        top: '1rem',
        right: '1rem',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.5rem 1rem',
        backgroundColor: 'white',
        border: `1px solid ${isConnected ? '#16a34a' : '#dc2626'}`,
        borderRadius: '0.5rem',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        fontSize: '0.875rem'
      }}>
        <div style={{
          width: '0.5rem',
          height: '0.5rem',
          borderRadius: '50%',
          backgroundColor: isConnected ? '#16a34a' : '#dc2626'
        }}></div>
        <span style={{color: isConnected ? '#16a34a' : '#dc2626'}}>
          {isConnected ? 'Connected' : connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
        </span>
      </div>
    )
  }

  return (
    <div style={{
      position: 'fixed',
      top: '1rem',
      right: '1rem',
      zIndex: 1000,
      maxWidth: '400px'
    }}>
      {/* Connection Status */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '0.5rem',
        padding: '0.5rem 1rem',
        backgroundColor: 'white',
        border: `1px solid ${isConnected ? '#16a34a' : '#dc2626'}`,
        borderRadius: '0.5rem 0.5rem 0 0',
        fontSize: '0.875rem',
        borderBottom: 'none'
      }}>
        <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
          <div style={{
            width: '0.5rem',
            height: '0.5rem',
            borderRadius: '50%',
            backgroundColor: isConnected ? '#16a34a' : '#dc2626'
          }}></div>
          <span style={{color: isConnected ? '#16a34a' : '#dc2626'}}>
            {isConnected ? 'Live Updates' : 'Disconnected'}
          </span>
        </div>
        
        {notifications.length > 0 && (
          <button
            onClick={clearAllNotifications}
            style={{
              padding: '0.25rem 0.5rem',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '0.25rem',
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            Clear All
          </button>
        )}
      </div>

      {/* Notifications */}
      <div style={{
        maxHeight: '600px',
        overflowY: 'auto',
        backgroundColor: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '0 0 0.5rem 0.5rem',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
      }}>
        {notifications.map((notification) => {
          const colors = getNotificationColor(notification.type)
          
          return (
            <div
              key={notification.id}
              style={{
                padding: '1rem',
                borderBottom: '1px solid #f3f4f6',
                backgroundColor: colors.bg,
                borderLeft: `4px solid ${colors.border}`,
                animation: 'slideInRight 0.3s ease-out'
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '0.5rem'
              }}>
                <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
                  <span>{getNotificationIcon(notification.type)}</span>
                  <h4 style={{
                    fontSize: '0.875rem',
                    fontWeight: '600',
                    margin: 0,
                    color: colors.text
                  }}>
                    {notification.title}
                  </h4>
                </div>
                
                <button
                  onClick={() => removeNotification(notification.id)}
                  style={{
                    padding: '0.25rem',
                    backgroundColor: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    color: '#6b7280'
                  }}
                >
                  ×
                </button>
              </div>
              
              <p style={{
                fontSize: '0.875rem',
                color: colors.text,
                margin: '0 0 0.5rem 0',
                opacity: 0.8
              }}>
                {notification.message}
              </p>
              
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '0.75rem',
                color: '#6b7280'
              }}>
                <span>{notification.timestamp.toLocaleTimeString()}</span>
                
                {notification.actionLabel && notification.onAction && (
                  <button
                    onClick={notification.onAction}
                    style={{
                      padding: '0.25rem 0.5rem',
                      backgroundColor: colors.border,
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      cursor: 'pointer'
                    }}
                  >
                    {notification.actionLabel}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* CSS Animation */}
      <style>
        {`
          @keyframes slideInRight {
            from {
              opacity: 0;
              transform: translateX(100%);
            }
            to {
              opacity: 1;
              transform: translateX(0);
            }
          }
        `}
      </style>
    </div>
  )
}