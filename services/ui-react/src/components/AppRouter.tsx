import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { SimpleApp } from './simple/SimpleApp'
import { FixedDashboard } from './dashboard/FixedDashboard'
import { FixedAgentsPage } from './pages/FixedAgentsPage'
import { FixedTeamsPage } from './pages/FixedTeamsPage'
import { FixedOrgChartPage } from './pages/FixedOrgChartPage'
import { AgentDetailsPage } from './pages/AgentDetailsPage'
import { OrganizationProfilePage } from './pages/OrganizationProfilePage'
import { TeamDetailsPage } from './pages/TeamDetailsPage'
import { GoalsPage } from './pages/GoalsPage'
import { CreateAgentPage } from './pages/CreateAgentPage'
import { CreateTeamPage } from './pages/CreateTeamPage'
import { DashboardPage } from '../pages/DashboardPage'
import DocsPage from '../pages/DocsPage'
import ApiPlayground from './ApiPlayground'
import { Layout } from './layout/Layout'

export default function AppRouter() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<FixedDashboard />} />
        <Route path="/simple" element={<SimpleApp />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/agents" element={<FixedAgentsPage />} />
        <Route path="/agents/create" element={<CreateAgentPage />} />
        <Route path="/agents/:agentId" element={<AgentDetailsPage />} />
        <Route path="/teams" element={<FixedTeamsPage />} />
        <Route path="/teams/create" element={<CreateTeamPage />} />
        <Route path="/teams/:teamId/details" element={<TeamDetailsPage />} />
        <Route path="/teams/:teamId/manage" element={<TeamDetailsPage />} />
        <Route path="/teams/:teamId/settings" element={<TeamDetailsPage />} />
        <Route path="/goals" element={<GoalsPage />} />
        <Route path="/organization-chart" element={<FixedOrgChartPage />} />
        <Route path="/organization/profile" element={<OrganizationProfilePage />} />
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