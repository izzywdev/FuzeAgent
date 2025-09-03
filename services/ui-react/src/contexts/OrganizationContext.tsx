import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiService } from '../services/apiService'

interface Organization {
  id: string
  name: string
  description?: string
  created_at: string
  team_count?: number
  agent_count?: number
  token: string
}

interface OrganizationContextType {
  currentOrganization: Organization | null
  organizations: Organization[]
  loading: boolean
  error: string | null
  selectOrganization: (orgId: string) => void
  refreshOrganizations: () => Promise<void>
  clearOrganization: () => void
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined)

interface OrganizationProviderProps {
  children: ReactNode
}

/**
 * OrganizationProvider - Context provider for organization state management
 * 
 * Manages the currently selected organization and provides methods to switch
 * between organizations. Persists the selected organization in localStorage
 * and automatically redirects to landing page when no organization is selected.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */
export function OrganizationProvider({ children }: OrganizationProviderProps) {
  const [currentOrganization, setCurrentOrganization] = useState<Organization | null>(null)
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load organizations and restore selected organization on mount
  useEffect(() => {
    initializeOrganization()
  }, [])

  const initializeOrganization = async () => {
    try {
      setLoading(true)
      setError(null)

      // Load all organizations
      const response = await apiService.getOrganizations()
      if (response.ok) {
        // Add tokens to organizations for token-based auth
        const orgsWithTokens = (Array.isArray(response.data) ? response.data : []).map((org: any) => ({
          ...org,
          token: org.token || `org-token-${org.id}` // Generate token if not provided
        }))
        setOrganizations(orgsWithTokens)

        // Restore selected organization from localStorage
        const selectedOrgId = localStorage.getItem('selectedOrganizationId')
        if (selectedOrgId && orgsWithTokens.length > 0) {
          const selectedOrg = orgsWithTokens.find((org: Organization) => org.id === selectedOrgId)
          if (selectedOrg) {
            setCurrentOrganization(selectedOrg)
            // Set organization token in API service
            apiService.setOrganizationToken(selectedOrg.token)
          } else {
            // Selected organization no longer exists, clear selection
            localStorage.removeItem('selectedOrganizationId')
            apiService.setOrganizationToken(null)
          }
        }
      } else {
        setError('Failed to load organizations')
      }
    } catch (err) {
      console.error('Error initializing organization:', err)
      setError('Network error loading organizations')
    } finally {
      setLoading(false)
    }
  }

  const selectOrganization = (orgId: string) => {
    const org = organizations.find(o => o.id === orgId)
    if (org) {
      setCurrentOrganization(org)
      localStorage.setItem('selectedOrganizationId', orgId)
      // Set organization token in API service
      apiService.setOrganizationToken(org.token)
    }
  }

  const refreshOrganizations = async () => {
    try {
      setError(null)
      const response = await apiService.getOrganizations()
      if (response.ok) {
        setOrganizations(Array.isArray(response.data) ? response.data : [])
        
        // Update current organization if it still exists
        if (currentOrganization) {
          const updatedOrg = response.data.find((org: Organization) => org.id === currentOrganization.id)
          if (updatedOrg) {
            setCurrentOrganization(updatedOrg)
          }
        }
      } else {
        setError('Failed to refresh organizations')
      }
    } catch (err) {
      console.error('Error refreshing organizations:', err)
      setError('Network error refreshing organizations')
    }
  }

  const clearOrganization = () => {
    setCurrentOrganization(null)
    localStorage.removeItem('selectedOrganizationId')
    // Clear organization token in API service
    apiService.setOrganizationToken(null)
  }

  const value: OrganizationContextType = {
    currentOrganization,
    organizations,
    loading,
    error,
    selectOrganization,
    refreshOrganizations,
    clearOrganization
  }

  return (
    <OrganizationContext.Provider value={value}>
      {children}
    </OrganizationContext.Provider>
  )
}

/**
 * Hook to use the organization context
 * 
 * @returns OrganizationContextType - The organization context value
 * @throws Error if used outside of OrganizationProvider
 */
export function useOrganization(): OrganizationContextType {
  const context = useContext(OrganizationContext)
  if (context === undefined) {
    throw new Error('useOrganization must be used within an OrganizationProvider')
  }
  return context
}
