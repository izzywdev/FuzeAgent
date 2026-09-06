// API Configuration for FuzeAgent Frontend
//
// Every call carries the FuzeFront session token. Before this, the UI sent NO
// credentials at all, so it could only ever talk to an unauthenticated backend —
// the orchestrator fails closed (401) on every non-public route. `authHeader()`
// reads the token the FuzeFront shell provides when embedded, or the one
// `/v1/security/session/exchange` stored when standalone.

import { authHeader, getToken } from '../lib/security/client'

// Environment-based API endpoints
const getAPIEndpoints = () => {
  const protocol = window.location.protocol
  const hostname = window.location.hostname
  
  // Allow explicit overrides via env vars
  const envHierarchy = (import.meta as any).env?.VITE_HIERARCHY_API_BASE as string | undefined
  const envOrchestrator = (import.meta as any).env?.VITE_ORCHESTRATOR_API_BASE as string | undefined
  const envWebSocket = (import.meta as any).env?.VITE_WEBSOCKET_BASE as string | undefined
  
  // Development vs Production configuration
  const isDevelopment = (import.meta as any).env?.NODE_ENV === 'development' || hostname === 'localhost'
  
  if (isDevelopment) {
    return {
      // Core orchestrator API (for agent management, tasks, etc.)
      ORCHESTRATOR_API_BASE: envOrchestrator || `${protocol}//${hostname}:8000`,
      
      // Hierarchy API (for organizations, teams, agents structure)
      HIERARCHY_API_BASE: envHierarchy || `${protocol}//${hostname}:8006`,
      
      // WebSocket endpoints
      WEBSOCKET_BASE: envWebSocket || `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}:8000`
    }
  } else {
    // Production endpoints (through nginx proxy) with optional overrides
    return {
      ORCHESTRATOR_API_BASE: envOrchestrator || `${protocol}//${hostname}/api`,
      HIERARCHY_API_BASE: envHierarchy || `${protocol}//${hostname}/api`,
      WEBSOCKET_BASE: envWebSocket || `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}/api`
    }
  }
}

export const API_ENDPOINTS = getAPIEndpoints()

// API utility functions
export const api = {
  // Hierarchy API calls (organizations, teams, agents structure)
  hierarchy: {
    get: async (endpoint: string) => {
      const response = await fetch(`${API_ENDPOINTS.HIERARCHY_API_BASE}${endpoint}`, {
        headers: { ...authHeader() },
      })
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
          ...authHeader(),
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
          ...authHeader(),
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
        headers: { ...authHeader() },
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
      const response = await fetch(`${API_ENDPOINTS.ORCHESTRATOR_API_BASE}${endpoint}`, {
        headers: { ...authHeader() },
      })
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
          ...authHeader(),
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
          ...authHeader(),
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
        headers: { ...authHeader() },
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
      headers: { ...authHeader() },
      body: formData,
    })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }
}

// WebSocket utility.
//
// A browser cannot set an `Authorization` header on a WS handshake, so the session
// token rides the `Sec-WebSocket-Protocol` subprotocol as `bearer, <token>` — the
// browser-friendly form the orchestrator's `authenticate_websocket` accepts (it also
// takes a `?token=` query param, but that leaks the token into access logs and
// referrers, so we do not use it). Without a token we connect unauthenticated and the
// server closes with 1008, which is the correct fail-closed outcome.
export const createWebSocket = (endpoint: string) => {
  const url = `${API_ENDPOINTS.WEBSOCKET_BASE}${endpoint}`
  const token = getToken()
  return token ? new WebSocket(url, ['bearer', token]) : new WebSocket(url)
}

export default API_ENDPOINTS