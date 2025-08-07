// API Configuration for FuzeAgent Frontend

// Environment-based API endpoints
const getAPIEndpoints = () => {
  const protocol = window.location.protocol
  const hostname = window.location.hostname
  
  // Development vs Production configuration
  const isDevelopment = process.env.NODE_ENV === 'development' || hostname === 'localhost'
  
  if (isDevelopment) {
    return {
      // Core orchestrator API (for agent management, tasks, etc.)
      ORCHESTRATOR_API_BASE: `${protocol}//${hostname}:8000`,
      
      // Hierarchy API (for organizations, teams, agents structure)
      HIERARCHY_API_BASE: `${protocol}//${hostname}:8006`,
      
      // WebSocket endpoints
      WEBSOCKET_BASE: `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}:8000`
    }
  } else {
    // Production endpoints (through nginx proxy)
    return {
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