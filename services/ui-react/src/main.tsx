import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import AppRouter from './components/AppRouter.tsx'

// Global error handler to suppress browser extension errors
window.addEventListener('error', (event) => {
  // Suppress common browser extension errors that don't affect the application
  if (event.message && (
    event.message.includes('A listener indicated an asynchronous response') ||
    event.message.includes('message channel closed') ||
    event.message.includes('Extension context invalidated')
  )) {
    event.preventDefault()
    console.debug('Suppressed browser extension error:', event.message)
    return false
  }
})

// Global unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
  // Suppress common browser extension promise rejections
  if (event.reason && (
    event.reason.message?.includes('A listener indicated an asynchronous response') ||
    event.reason.message?.includes('message channel closed') ||
    event.reason.message?.includes('Extension context invalidated')
  )) {
    event.preventDefault()
    console.debug('Suppressed browser extension promise rejection:', event.reason)
    return false
  }
})

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
