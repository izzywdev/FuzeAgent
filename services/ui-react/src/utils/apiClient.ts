import { useCallback } from 'react'
import { useOrganization } from '../contexts/OrganizationContext'

/**
 * API Client utility for making organization-scoped API calls
 * 
 * This utility automatically adds the current organization ID to all API requests
 * as a header, ensuring proper data isolation between organizations.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

/**
 * Enhanced fetch function that automatically includes organization context
 * 
 * @param url - The URL to fetch
 * @param options - Fetch options
 * @param organizationId - The current organization ID
 * @returns Promise<Response>
 */
// Get API base URL from environment or default to localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export async function fetchWithOrg(
  url: string, 
  options: RequestInit = {}, 
  organizationId?: string
): Promise<Response> {
  const headers = new Headers(options.headers)
  
  // Add organization ID as Bearer token if provided
  if (organizationId) {
    headers.set('Authorization', `Bearer ${organizationId}`)
    console.log('[ApiClient] Setting Authorization Bearer token:', organizationId, 'for URL:', url)
  } else {
    console.log('[ApiClient] No organization ID provided for URL:', url)
  }
  
  // Use full URL if it starts with http, otherwise prepend API base URL
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`
  
  return fetch(fullUrl, {
    ...options,
    headers
  })
}

/**
 * Hook to get organization-scoped fetch function
 * 
 * @returns Function that automatically includes current organization ID
 */
export function useApiClient() {
  const { currentOrganization } = useOrganization()
  
  return useCallback((url: string, options: RequestInit = {}) => {
    return fetchWithOrg(url, options, currentOrganization?.id)
  }, [currentOrganization?.id])
}

/**
 * Utility function to create organization-scoped API endpoints
 * 
 * @param baseUrl - Base URL for the API
 * @param organizationId - Organization ID
 * @returns Object with common API endpoints
 */
export function createOrgApiEndpoints(baseUrl: string, organizationId: string) {
  return {
    organizations: `${baseUrl}/organizations`,
    teams: `${baseUrl}/teams`,
    agents: `${baseUrl}/agents`,
    goals: `${baseUrl}/goals`,
    tasks: `${baseUrl}/tasks`,
    knowledge: `${baseUrl}/knowledge/organizations/${organizationId}`,
    tools: `${baseUrl}/organizations/${organizationId}/tools`
  }
}
