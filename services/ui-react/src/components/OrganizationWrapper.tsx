import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useOrganization } from '../contexts/OrganizationContext'

/**
 * OrganizationWrapper - Handles navigation logic for organization context
 * 
 * This component manages the navigation logic that was previously in OrganizationProvider.
 * It ensures that navigation only happens when the Router context is available.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */
export function OrganizationWrapper() {
  const navigate = useNavigate()
  const { currentOrganization, organizations, loading } = useOrganization()

  useEffect(() => {
    // Only handle navigation if we're not loading and have organization data
    if (!loading && organizations.length >= 0) {
      const selectedOrgId = localStorage.getItem('selectedOrganizationId')
      
      if (!selectedOrgId) {
        // No organization selected, redirect to landing page
        navigate('/landing')
      } else if (organizations.length > 0) {
        // Check if selected organization still exists
        const selectedOrg = organizations.find(org => org.id === selectedOrgId)
        if (!selectedOrg) {
          // Selected organization no longer exists, clear selection and redirect
          localStorage.removeItem('selectedOrganizationId')
          navigate('/landing')
        }
      } else if (organizations.length === 0) {
        // No organizations exist, redirect to landing page
        navigate('/landing')
      }
    }
  }, [loading, organizations, navigate])

  // This component doesn't render anything, it just handles navigation logic
  return null
}
