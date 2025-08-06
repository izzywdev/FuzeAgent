export default function OrganizationsTeams() {
  return (
    <div className="prose prose-gray max-w-none">
      <h1>Organizations & Teams</h1>
      
      <p className="lead">
        FuzeAgent uses a hierarchical structure to organize AI agents. 
        Learn how to create and manage organizations and teams effectively.
      </p>

      <div className="not-prose mb-8">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-blue-900 font-semibold mb-2">Hierarchy Overview</h3>
          <div className="text-blue-800 font-mono text-sm">
            Organization (e.g., "ACME Corp")<br />
            └── Teams (e.g., "Frontend Team", "Backend Team")<br />
            &nbsp;&nbsp;&nbsp;&nbsp;└── Agents (e.g., "React Developer", "API Developer")
          </div>
        </div>
      </div>

      <h2>Organizations</h2>

      <p>Organizations are the top-level containers that group related teams and projects:</p>

      <h3>Creating Organizations</h3>

      <pre><code>{`// Create a new organization
const orgData = {
  name: "ACME Corporation",
  description: "Main development organization for ACME products"
}

const response = await fetch('/api/organizations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(orgData)
})

const organization = await response.json()
console.log(organization.id) // org_123`}</code></pre>

      <h3>Organization Management</h3>

      <pre><code>{`// List all organizations
const orgs = await fetch('/api/organizations')
const organizations = await orgs.json()

// Update organization
const updates = {
  name: "ACME Corporation Ltd",
  description: "Updated description"
}

await fetch('/api/organizations/org_123', {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(updates)
})`}</code></pre>

      <h2>Teams</h2>

      <p>Teams group agents with similar roles or working on related projects:</p>

      <h3>Creating Teams</h3>

      <pre><code>{`// Create teams within an organization
const teams = [
  {
    name: "Frontend Team",
    description: "React and TypeScript development",
    organization_id: "org_123"
  },
  {
    name: "Backend Team", 
    description: "API and database development",
    organization_id: "org_123"
  },
  {
    name: "DevOps Team",
    description: "Infrastructure and deployment",
    organization_id: "org_123"
  }
]

for (const team of teams) {
  await fetch('/api/teams', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(team)
  })
}`}</code></pre>

      <h3>Team Specializations</h3>

      <div className="not-prose mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="border border-gray-200 rounded-lg p-6">
            <h4 className="font-semibold text-gray-900 mb-3">Frontend Teams</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• React specialists</li>
              <li>• UI/UX designers</li>
              <li>• Mobile developers</li>
              <li>• CSS experts</li>
            </ul>
          </div>

          <div className="border border-gray-200 rounded-lg p-6">
            <h4 className="font-semibold text-gray-900 mb-3">Backend Teams</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• API developers</li>
              <li>• Database architects</li>
              <li>• Security specialists</li>
              <li>• Microservices experts</li>
            </ul>
          </div>

          <div className="border border-gray-200 rounded-lg p-6">
            <h4 className="font-semibold text-gray-900 mb-3">Operations Teams</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• DevOps engineers</li>
              <li>• QA specialists</li>
              <li>• Security auditors</li>
              <li>• Performance experts</li>
            </ul>
          </div>
        </div>
      </div>

      <h2>Team Hierarchy View</h2>

      <p>Get a complete view of your organizational structure:</p>

      <pre><code>{`// Get hierarchical view
const hierarchy = await fetch('/api/hierarchy?organization_id=org_123')
const orgStructure = await hierarchy.json()

console.log(orgStructure)
// {
//   "organization": {
//     "id": "org_123",
//     "name": "ACME Corporation",
//     "teams": [
//       {
//         "id": "team_456",
//         "name": "Frontend Team",
//         "agents": [
//           {
//             "id": "agent_789",
//             "name": "React Developer",
//             "status": "active"
//           }
//         ]
//       }
//     ]
//   }
// }`}</code></pre>

      <h2>Best Practices</h2>

      <h3>Organization Structure</h3>

      <div className="not-prose mb-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
          <h4 className="text-green-800 font-semibold mb-2">✅ Recommended Structure</h4>
          <div className="text-green-700 text-sm space-y-1">
            <div>📁 ACME Corporation</div>
            <div>&nbsp;&nbsp;├── 👥 Frontend Team (React, Vue, Angular)</div>
            <div>&nbsp;&nbsp;├── 👥 Backend Team (APIs, Databases)</div>
            <div>&nbsp;&nbsp;├── 👥 Mobile Team (iOS, Android)</div>
            <div>&nbsp;&nbsp;└── 👥 DevOps Team (Infrastructure, CI/CD)</div>
          </div>
        </div>

        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="text-red-800 font-semibold mb-2">❌ Avoid</h4>
          <div className="text-red-700 text-sm space-y-1">
            <div>📁 Mixed Organization</div>
            <div>&nbsp;&nbsp;├── 👥 Everything Team (All technologies)</div>
            <div>&nbsp;&nbsp;└── 👥 Random Team (No clear focus)</div>
          </div>
        </div>
      </div>

      <h3>Naming Conventions</h3>

      <ul>
        <li><strong>Organizations</strong>: Company or department names (e.g., "ACME Corp", "Engineering")</li>
        <li><strong>Teams</strong>: Functional or technology-based (e.g., "Frontend Team", "Python Developers")</li>
        <li><strong>Descriptive</strong>: Include purpose and technology stack in descriptions</li>
      </ul>

      <h3>Team Size Guidelines</h3>

      <div className="not-prose mb-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="text-yellow-800 font-semibold mb-2">💡 Recommended Team Sizes</h4>
          <ul className="text-yellow-700 text-sm space-y-1">
            <li><strong>Small Teams (2-5 agents)</strong>: Focused specialization, quick coordination</li>
            <li><strong>Medium Teams (6-10 agents)</strong>: Balanced capabilities, good for most projects</li>
            <li><strong>Large Teams (11+ agents)</strong>: Complex projects, consider sub-teams</li>
          </ul>
        </div>
      </div>

      <h2>Advanced Management</h2>

      <h3>Cross-Team Collaboration</h3>

      <pre><code>{`// Assign task requiring multiple teams
const crossTeamTask = {
  title: "Full-stack feature implementation",
  description: "New user dashboard with API and frontend",
  teams: ["team_frontend", "team_backend"],
  coordination_agent: "agent_project_manager"
}`}</code></pre>

      <h3>Team Metrics</h3>

      <pre><code>{`// Get team performance metrics
const metrics = await fetch('/api/teams/team_456/metrics')
const teamStats = await metrics.json()

console.log(teamStats)
// {
//   "agents_count": 5,
//   "active_tasks": 12,
//   "completed_tasks": 48,
//   "success_rate": 0.94,
//   "average_task_time": "3.2 hours",
//   "specialties": ["react", "typescript", "tailwind"]
// }`}</code></pre>

      <h3>Resource Management</h3>

      <ul>
        <li><strong>Load Balancing</strong>: Distribute tasks evenly across team members</li>
        <li><strong>Skill Matching</strong>: Assign tasks based on agent expertise</li>
        <li><strong>Capacity Planning</strong>: Monitor team workload and scale accordingly</li>
        <li><strong>Cross-Training</strong>: Develop agents with overlapping skills</li>
      </ul>

      <h2>Migration and Reorganization</h2>

      <h3>Moving Agents Between Teams</h3>

      <pre><code>{`// Transfer agent to different team
const transfer = {
  agent_id: "agent_789",
  from_team: "team_456", 
  to_team: "team_789",
  effective_date: "2024-01-20T00:00:00Z"
}

await fetch('/api/agents/transfer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(transfer)
})`}</code></pre>

      <h3>Team Restructuring</h3>

      <p>When reorganizing teams, consider:</p>

      <ul>
        <li>Completing existing tasks before moving agents</li>
        <li>Updating team skills and capabilities</li>
        <li>Rebalancing workloads across new structure</li>
        <li>Communicating changes to stakeholders</li>
      </ul>
    </div>
  )
}