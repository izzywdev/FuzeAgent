// API Configuration for FuzeAgent Frontend

// Environment-based API endpoints
const getAPIEndpoints = () => {
  const protocol = window.location.protocol
  const hostname = window.location.hostname
  
  // Development vs Production configuration
  const isDevelopment = import.meta.env.NODE_ENV === 'development' || hostname === 'localhost'
  const sameOriginWs = `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}${window.location.port ? `:${window.location.port}` : ''}`
  
  // Backend API URL - supports environment variable override
  const BACKEND_API_URL = import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000'
  
  if (isDevelopment) {
    // Use same-origin relative paths in dev; a mock layer intercepts these
    return {
      BACKEND_API_BASE: BACKEND_API_URL,
      ORCHESTRATOR_API_BASE: '',
      HIERARCHY_API_BASE: '',
      WEBSOCKET_BASE: sameOriginWs
    }
  } else {
    // Production endpoints (through nginx proxy)
    return {
      BACKEND_API_BASE: BACKEND_API_URL,
      ORCHESTRATOR_API_BASE: `${protocol}//${hostname}/api`,
      HIERARCHY_API_BASE: `${protocol}//${hostname}/api`,
      WEBSOCKET_BASE: `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}/api`
    }
  }
}

export const API_ENDPOINTS = getAPIEndpoints()

// API utility functions
export const api = {
  // Hierarchy API calls (organizations, teams, agents structure)
  hierarchy: {
    get: async (endpoint: string) => {
      const response = await fetch(`${API_ENDPOINTS.HIERARCHY_API_BASE}${endpoint}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.json()
    },
    
    post: async (endpoint: string, data: any) => {
      const response = await fetch(`${API_ENDPOINTS.HIERARCHY_API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.json()
    },
    
    put: async (endpoint: string, data: any) => {
      const response = await fetch(`${API_ENDPOINTS.HIERARCHY_API_BASE}${endpoint}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.json()
    },
    
    delete: async (endpoint: string) => {
      const response = await fetch(`${API_ENDPOINTS.HIERARCHY_API_BASE}${endpoint}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.ok
    }
  },
  
  // Orchestrator API calls (agent management, tasks, containers, etc.)
  orchestrator: {
    get: async (endpoint: string) => {
      const response = await fetch(`${API_ENDPOINTS.ORCHESTRATOR_API_BASE}${endpoint}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.json()
    },
    
    post: async (endpoint: string, data: any) => {
      const response = await fetch(`${API_ENDPOINTS.ORCHESTRATOR_API_BASE}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.json()
    },
    
    put: async (endpoint: string, data: any) => {
      const response = await fetch(`${API_ENDPOINTS.ORCHESTRATOR_API_BASE}${endpoint}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.json()
    },
    
    delete: async (endpoint: string) => {
      const response = await fetch(`${API_ENDPOINTS.ORCHESTRATOR_API_BASE}${endpoint}`, {
        method: 'DELETE',
      })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      return response.ok
    }
  },
  
  // File upload utility
  upload: async (endpoint: string, formData: FormData) => {
    const response = await fetch(`${API_ENDPOINTS.ORCHESTRATOR_API_BASE}${endpoint}`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }
}

// WebSocket utility
export const createWebSocket = (endpoint: string) => {
  return new WebSocket(`${API_ENDPOINTS.WEBSOCKET_BASE}${endpoint}`)
}

export default API_ENDPOINTS