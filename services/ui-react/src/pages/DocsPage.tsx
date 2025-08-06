import { Routes, Route } from 'react-router-dom'
import { useState } from 'react'
import DocumentationLayout from '../components/DocumentationLayout'
import DocsOverview from './docs/DocsOverview'
import GettingStarted from './docs/GettingStarted'
import ApiReference from './docs/ApiReference'
import CreatingAgents from './docs/CreatingAgents'
import TaskManagement from './docs/TaskManagement'
import OrganizationsTeams from './docs/OrganizationsTeams'
import Examples from './docs/Examples'
import Monitoring from './docs/Monitoring'

export default function DocsPage() {
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <DocumentationLayout 
      searchQuery={searchQuery} 
      onSearchChange={setSearchQuery}
    >
      <Routes>
        <Route index element={<DocsOverview />} />
        <Route path="getting-started" element={<GettingStarted />} />
        <Route path="api-reference" element={<ApiReference />} />
        <Route path="creating-agents" element={<CreatingAgents />} />
        <Route path="task-management" element={<TaskManagement />} />
        <Route path="organizations-teams" element={<OrganizationsTeams />} />
        <Route path="examples/*" element={<Examples />} />
        <Route path="monitoring" element={<Monitoring />} />
      </Routes>
    </DocumentationLayout>
  )
}