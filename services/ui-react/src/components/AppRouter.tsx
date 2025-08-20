/**
 * AppRouter - Main routing configuration for the FuzeAgent application
 * 
 * This component defines all the application routes and their corresponding components.
 * Routes are organized by feature area for better maintainability.
 * 
 * @author FuzeAgent Team
 * @version 1.0.0
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

// Core layout component
import { Layout } from './layout/Layout'

// Dashboard components
import { FixedDashboard } from './dashboard/FixedDashboard'
import { DashboardPage } from '../pages/DashboardPage'

// Agent management pages
import { FixedAgentsPage } from './pages/FixedAgentsPage'
import { AgentDetailsPage } from './pages/AgentDetailsPage'
import { CreateAgentPage } from './pages/CreateAgentPage'

// Team management pages
import { FixedTeamsPage } from './pages/FixedTeamsPage'
import { CreateTeamPage } from './pages/CreateTeamPage'
import { TeamDetailsPage } from './pages/TeamDetailsPage'

// Organization and goals pages
import { OrganizationProfilePage } from './pages/OrganizationProfilePage'
import { GoalsPage } from './pages/GoalsPage'
import { FixedOrgChartPage } from './pages/FixedOrgChartPage'

// Documentation and tools
import DocsPage from '../pages/DocsPage'
import ApiPlayground from './ApiPlayground'

/**
 * Main application router component
 * 
 * Provides routing for all major application features including:
 * - Dashboard and analytics
 * - Agent and team management
 * - Organization settings
 * - Documentation and API playground
 * 
 * @returns JSX.Element - The configured router with all application routes
 */
export default function AppRouter() {
  return (
    <Router>
      <Routes>
        {/* Main Dashboard Routes */}
        <Route path="/" element={<FixedDashboard />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        
        {/* Agent Management Routes */}
        <Route path="/agents" element={<FixedAgentsPage />} />
        <Route path="/agents/create" element={<CreateAgentPage />} />
        <Route path="/agents/:agentId" element={<AgentDetailsPage />} />
        
        {/* Team Management Routes */}
        <Route path="/teams" element={<FixedTeamsPage />} />
        <Route path="/teams/create" element={<CreateTeamPage />} />
        <Route path="/teams/:teamId/details" element={<TeamDetailsPage />} />
        <Route path="/teams/:teamId/manage" element={<TeamDetailsPage />} />
        <Route path="/teams/:teamId/settings" element={<TeamDetailsPage />} />
        
        {/* Organization and Goals Routes */}
        <Route path="/goals" element={<GoalsPage />} />
        <Route path="/goals/:goalId" element={<GoalsPage />} />
        <Route path="/organization/profile" element={<OrganizationProfilePage />} />
        <Route path="/organization-chart" element={<FixedOrgChartPage />} />
        
        {/* Analytics and Monitoring Routes */}
        <Route 
          path="/analytics" 
          element={
            <Layout title="Analytics" subtitle="Performance insights and metrics">
              <div className="text-center py-12">
                <h2 className="text-2xl font-semibold mb-4">Analytics Dashboard</h2>
                <p className="text-muted-foreground">Analytics interface coming soon...</p>
              </div>
            </Layout>
          } 
        />
        
        {/* Activity and Notifications Routes */}
        <Route 
          path="/activity" 
          element={
            <Layout title="Activity Feed" subtitle="Real-time updates and notifications">
              <div className="text-center py-12">
                <h2 className="text-2xl font-semibold mb-4">Activity Feed</h2>
                <p className="text-muted-foreground">Activity feed coming soon...</p>
              </div>
            </Layout>
          } 
        />
        
        {/* Development and Documentation Routes */}
        <Route 
          path="/playground" 
          element={
            <Layout title="API Playground" subtitle="Test and explore the FuzeAgent API">
              <ApiPlayground />
            </Layout>
          } 
        />
        
        <Route 
          path="/docs/*" 
          element={
            <Layout title="Documentation" subtitle="Learn how to use FuzeAgent">
              <DocsPage />
            </Layout>
          } 
        />
        
        {/* Configuration Routes */}
        <Route 
          path="/settings" 
          element={
            <Layout title="Settings" subtitle="Configure your FuzeAgent environment">
              <div className="text-center py-12">
                <h2 className="text-2xl font-semibold mb-4">Settings</h2>
                <p className="text-muted-foreground">Settings interface coming soon...</p>
              </div>
            </Layout>
          } 
        />
      </Routes>
    </Router>
  )
}