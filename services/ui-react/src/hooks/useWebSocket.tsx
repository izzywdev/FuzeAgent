import { useState, useEffect, useRef, useCallback } from 'react'

export interface WebSocketMessage {
  id: string
  type: string
  timestamp: string
  data: any
  target_id?: string
  organization_id?: string
  team_id?: string
  agent_id?: string
}

export interface WebSocketOptions {
  organizationId?: string
  teamId?: string
  agentId?: string
  userId?: string
  subscriptions?: string[]
  autoReconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

export interface WebSocketHook {
  isConnected: boolean
  connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error'
  lastMessage: WebSocketMessage | null
  messages: WebSocketMessage[]
  error: string | null
  connect: () => void
  disconnect: () => void
  sendMessage: (message: any) => void
  clearMessages: () => void
  subscribe: (subscriptions: string[]) => void
}

export function useWebSocket(url: string, options: WebSocketOptions = {}): WebSocketHook {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected')
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [error, setError] = useState<string | null>(null)
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  
  const {
    autoReconnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
    organizationId,
    teamId,
    agentId,
    userId,
    subscriptions = []
  } = options

  const buildUrl = useCallback(() => {
    const params = new URLSearchParams()
    if (organizationId) params.append('organization_id', organizationId)
    if (teamId) params.append('team_id', teamId)
    if (agentId) params.append('agent_id', agentId)
    if (userId) params.append('user_id', userId)
    if (subscriptions.length > 0) params.append('subscriptions', subscriptions.join(','))
    
    return `${url}${params.toString() ? `?${params.toString()}` : ''}`
  }, [url, organizationId, teamId, agentId, userId, subscriptions])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    setConnectionStatus('connecting')
    setError(null)

    try {
      const wsUrl = buildUrl()
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        setIsConnected(true)
        setConnectionStatus('connected')
        setError(null)
        reconnectAttemptsRef.current = 0
        
        // Start ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
        }
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send('ping')
          }
        }, 30000) // Ping every 30 seconds
      }

      wsRef.current.onmessage = (event) => {
        try {
          if (event.data === 'pong') {
            return // Handle pong response
          }
          
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
          setMessages(prev => [...prev.slice(-99), message]) // Keep last 100 messages
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      wsRef.current.onclose = (event) => {
        setIsConnected(false)
        setConnectionStatus('disconnected')
        
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }

        // Only attempt reconnect if it wasn't a clean close and auto-reconnect is enabled
        if (autoReconnect && event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1
          setConnectionStatus('connecting')
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        }
      }

      wsRef.current.onerror = (error) => {
        setError('WebSocket connection error')
        setConnectionStatus('error')
        console.error('WebSocket error:', error)
      }
    } catch (err) {
      setError('Failed to create WebSocket connection')
      setConnectionStatus('error')
    }
  }, [buildUrl, autoReconnect, reconnectInterval, maxReconnectAttempts])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect')
      wsRef.current = null
    }
    
    setIsConnected(false)
    setConnectionStatus('disconnected')
    reconnectAttemptsRef.current = 0
  }, [])

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof message === 'string' ? message : JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setLastMessage(null)
  }, [])

  const subscribe = useCallback((newSubscriptions: string[]) => {
    sendMessage({
      type: 'subscribe',
      subscriptions: newSubscriptions
    })
  }, [sendMessage])

  // Auto-connect on mount
  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current)
      }
    }
  }, [])

  return {
    isConnected,
    connectionStatus,
    lastMessage,
    messages,
    error,
    connect,
    disconnect,
    sendMessage,
    clearMessages,
    subscribe
  }
}

// Specialized hook for agent updates
export function useAgentWebSocket(agentId: string) {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/ws/agent/${agentId}/updates`
  
  return useWebSocket(wsUrl, {
    agentId,
    subscriptions: [
      'agent_status',
      'task_status',
      'task_progress',
      'container_status',
      'chat_message',
      'chat_typing'
    ]
  })
}

// Specialized hook for organization updates
export function useOrganizationWebSocket(organizationId: string) {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/ws/organization/${organizationId}/updates`
  
  return useWebSocket(wsUrl, {
    organizationId,
    subscriptions: [
      'agent_created',
      'agent_updated',
      'agent_deleted',
      'knowledge_updated',
      'knowledge_indexed',
      'system_notification'
    ]
  })
}

// General purpose hook for main dashboard
export function useDashboardWebSocket(options: WebSocketOptions = {}) {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/ws/updates`
  
  return useWebSocket(wsUrl, {
    subscriptions: [
      'agent_status',
      'agent_created',
      'agent_updated',
      'task_status',
      'task_progress',
      'container_status',
      'knowledge_updated',
      'system_notification',
      'system_error'
    ],
    ...options
  })
}