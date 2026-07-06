// Environment configuration for API base URLs

// Single base URL for all API calls
export const API_URL: string = (import.meta as any).env?.VITE_API_URL
  || `${window.location.protocol}//${window.location.hostname}:8006`

// Derived WebSocket base from API_URL
export const WS_URL_BASE: string = (() => {
  try {
    const base = new URL(API_URL)
    const wsScheme = base.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsScheme}//${base.host}`
  } catch {
    const wsScheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsScheme}//${window.location.host}`
  }
})()


