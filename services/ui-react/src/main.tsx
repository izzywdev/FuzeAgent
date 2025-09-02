import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import AppRouter from './components/AppRouter.tsx'

// Check if user has a selected organization, if not redirect to landing page
const selectedOrgId = localStorage.getItem('selectedOrganizationId')
if (!selectedOrgId) {
  // If no organization is selected, redirect to landing page
  window.history.replaceState(null, '', '/landing')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>,
)
