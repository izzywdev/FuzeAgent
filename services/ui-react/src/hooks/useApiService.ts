import { useEffect } from 'react'
import { useOrganization } from '../contexts/OrganizationContext'
import { apiService } from '../services/apiService'

/**
 * React hook that provides the API service with automatic organization context
 * 
 * @returns The API service instance with organization context set
 */
export function useApiService() {
  const { currentOrganization } = useOrganization()
  
  useEffect(() => {
    apiService.setOrganizationId(currentOrganization?.id || null)
  }, [currentOrganization?.id])
  
  return apiService
}
