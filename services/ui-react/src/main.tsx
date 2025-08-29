import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import AppRouter from './components/AppRouter.tsx'
import { enableMockApi, enableMockWs } from './mocks/server'

// Always enable mock API for now to avoid any runtime backend dependency
enableMockApi()
enableMockWs()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppRouter />
  </StrictMode>,
)
