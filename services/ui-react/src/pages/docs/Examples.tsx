import { Link } from 'react-router-dom'
import { FiPlay, FiCode, FiUsers, FiArrowRight } from 'react-icons/fi'

const examples = [
  {
    title: 'Quick Start Example',
    description: 'Set up a basic AI development team in 5 minutes',
    difficulty: 'Beginner',
    time: '5 min',
    path: '/docs/examples/quick-start',
    icon: FiPlay,
    color: 'bg-green-100 text-green-700'
  },
  {
    title: 'E-commerce Platform',
    description: 'Build a full e-commerce platform with specialized agent teams',
    difficulty: 'Intermediate',
    time: '30 min',
    path: '/docs/examples/ecommerce',
    icon: FiCode,
    color: 'bg-blue-100 text-blue-700'
  },
  {
    title: 'Microservices Architecture',
    description: 'Design and implement microservices with dedicated agents',
    difficulty: 'Advanced',
    time: '45 min',
    path: '/docs/examples/microservices',
    icon: FiUsers,
    color: 'bg-purple-100 text-purple-700'
  }
]

export default function Examples() {
  return (
    <div className="prose prose-gray max-w-none">
      <h1>Examples & Use Cases</h1>
      
      <p className="lead">
        Learn FuzeAgent through practical examples. Each example includes complete code, 
        step-by-step instructions, and best practices.
      </p>

      <div className="not-prose mb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {examples.map((example) => {
            const Icon = example.icon
            return (
              <Link
                key={example.path}
                to={example.path}
                className="group block bg-white border border-gray-200 rounded-lg p-6 hover:border-gray-300 hover:shadow-md transition-all"
              >
                <div className="flex items-start gap-4 mb-4">
                  <div className={`p-3 rounded-lg ${example.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                        {example.difficulty}
                      </span>
                      <span className="text-xs text-gray-500">{example.time}</span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                      {example.title}
                    </h3>
                  </div>
                </div>
                <p className="text-gray-600 text-sm mb-4">
                  {example.description}
                </p>
                <div className="flex items-center text-blue-600 text-sm font-medium">
                  View Example
                  <FiArrowRight className="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            )
          })}
        </div>
      </div>

      <h2>Quick Start Example</h2>

      <p>The fastest way to get started with FuzeAgent:</p>

      <h3>1. Set up Infrastructure</h3>

      <pre><code>{`# Clone the repository
git clone https://github.com/yourusername/FuzeAgent.git
cd FuzeAgent

# Run the setup script
./setup.sh

# Verify services are running
docker-compose ps`}</code></pre>

      <h3>2. Create Your First Organization</h3>

      <pre><code>{`// Create organization
const org = await fetch('/api/organizations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: "My Company",
    description: "AI development team"
  })
})

const organization = await org.json()
console.log('Organization ID:', organization.id)`}</code></pre>

      <h3>3. Set up Development Teams</h3>

      <pre><code>{`// Create frontend team
const frontendTeam = await fetch('/api/teams', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: "Frontend Team",
    description: "React and TypeScript specialists",
    organization_id: organization.id
  })
})

const team = await frontendTeam.json()
console.log('Team ID:', team.id)`}</code></pre>

      <h3>4. Deploy AI Agents</h3>

      <pre><code>{`// Deploy React developer from template
const agent = await fetch('/api/agents/from-template', {
  method: 'POST',  
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    template_id: "react_developer",
    name: "Senior React Dev",
    team_id: team.id,
    overrides: {
      skills: ["react", "typescript", "tailwind", "next.js"],
      model: "claude-sonnet-4-20250514"
    }
  })
})

const reactDev = await agent.json()
console.log('Agent deployed:', reactDev.id)`}</code></pre>

      <h3>5. Assign Your First Task</h3>

      <pre><code>{`// Create a development task
const task = await fetch(\`/api/agents/\${reactDev.id}/tasks\`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: "Create landing page component",
    description: \`Create a responsive landing page component with:
    - Hero section with call-to-action
    - Features grid (3 columns)
    - Testimonials section
    - Footer with links
    
    Use TypeScript and Tailwind CSS. Include proper accessibility.\`,
    priority: 7
  })
})

console.log('Task assigned successfully!')`}</code></pre>

      <h2>Real-World Use Cases</h2>

      <h3>Startup Development Team</h3>

      <div className="not-prose mb-6">
        <div className="bg-gray-50 rounded-lg p-6">
          <h4 className="font-semibold text-gray-900 mb-3">Team Structure</h4>
          <div className="text-sm space-y-2">
            <div><strong>CEO Agent:</strong> Project coordination and strategic decisions</div>
            <div><strong>Full-Stack Developer:</strong> Core product development</div>
            <div><strong>UI/UX Designer:</strong> User interface and experience</div>
            <div><strong>QA Engineer:</strong> Testing and quality assurance</div>
          </div>
        </div>
      </div>

      <h3>Enterprise Development</h3>

      <pre><code>{`// Large-scale team setup
const enterpriseTeams = [
  {
    name: "Frontend Architecture Team",
    agents: ["Senior React Architect", "Vue.js Specialist", "Mobile Developer"]
  },
  {
    name: "Backend Services Team", 
    agents: ["API Architect", "Database Designer", "Security Specialist"]
  },
  {
    name: "Platform Team",
    agents: ["DevOps Engineer", "Site Reliability Engineer", "Monitoring Specialist"]
  },
  {
    name: "Quality Assurance",
    agents: ["Test Automation Engineer", "Performance Tester", "Security Auditor"]
  }
]`}</code></pre>

      <h3>Product Development Workflow</h3>

      <pre><code>{`// Coordinated product development
const productFeature = {
  title: "User Authentication System",
  phases: [
    {
      name: "Design Phase",
      team: "design_team",
      tasks: ["UI mockups", "User flow design", "Accessibility audit"]
    },
    {
      name: "Backend Development", 
      team: "backend_team",
      tasks: ["API endpoints", "Database schema", "Security implementation"]
    },
    {
      name: "Frontend Development",
      team: "frontend_team", 
      tasks: ["Login components", "Form validation", "State management"]
    },
    {
      name: "Testing & QA",
      team: "qa_team",
      tasks: ["Unit tests", "Integration tests", "Security testing"]
    }
  ]
}`}</code></pre>

      <h2>Advanced Patterns</h2>

      <h3>Multi-Agent Collaboration</h3>

      <pre><code>{`// Complex task requiring multiple agents
const collaborativeTask = {
  title: "Implement real-time chat feature",
  description: "Build WebSocket-based chat with React frontend",
  coordination: {
    lead_agent: "senior_full_stack",
    collaborators: [
      {
        agent: "backend_websocket_specialist",
        responsibilities: ["WebSocket server", "Message persistence"]
      },
      {
        agent: "react_specialist", 
        responsibilities: ["Chat UI components", "Real-time updates"]
      },
      {
        agent: "security_specialist",
        responsibilities: ["Message encryption", "Authentication"]
      }
    ]
  }
}`}</code></pre>

      <h3>Continuous Integration</h3>

      <pre><code>{`// Automated CI/CD with agent coordination
const cicdPipeline = {
  triggers: ["git_push", "pull_request"],
  stages: [
    {
      name: "Code Review",
      agent: "senior_code_reviewer",
      tasks: ["Review changes", "Check standards", "Security scan"]
    },
    {
      name: "Testing",
      agent: "qa_automation",
      tasks: ["Run unit tests", "Integration tests", "Performance tests"]
    },
    {
      name: "Deployment",
      agent: "devops_specialist", 
      tasks: ["Build application", "Deploy to staging", "Health checks"]
    }
  ]
}`}</code></pre>

      <div className="not-prose mt-12">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-blue-900 font-semibold mb-4">Ready to try these examples?</h3>
          <div className="space-y-3">
            <Link
              to="/docs/getting-started"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <FiPlay className="w-4 h-4" />
              Start with Setup Guide
            </Link>
            <div className="text-blue-700 text-sm">
              Or explore the <Link to="/docs/api-reference" className="underline hover:no-underline">API Reference</Link> for detailed documentation.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}