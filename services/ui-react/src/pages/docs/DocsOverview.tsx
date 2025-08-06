import { Link } from 'react-router-dom'
import { FiPlay, FiCode, FiUsers, FiZap, FiMonitor, FiArrowRight } from 'react-icons/fi'

const quickLinks = [
  {
    title: 'Getting Started',
    description: 'Set up FuzeAgent and create your first AI team',
    icon: FiPlay,
    path: '/docs/getting-started',
    color: 'bg-green-100 text-green-700'
  },
  {
    title: 'API Reference',
    description: 'Complete API documentation and examples',
    icon: FiCode,
    path: '/docs/api-reference',
    color: 'bg-blue-100 text-blue-700'
  },
  {
    title: 'Creating Agents',
    description: 'Learn how to create and configure AI agents',
    icon: FiUsers,
    path: '/docs/creating-agents',
    color: 'bg-purple-100 text-purple-700'
  },
  {
    title: 'Examples',
    description: 'Real-world examples and use cases',
    icon: FiZap,
    path: '/docs/examples',
    color: 'bg-yellow-100 text-yellow-700'
  }
]

const features = [
  {
    title: 'AI Team Orchestration',
    description: 'Coordinate multiple AI agents working together on complex projects'
  },
  {
    title: 'Claude Code Integration',
    description: 'Built-in integration with Anthropic\'s Claude Code SDK for development tasks'
  },
  {
    title: 'Hierarchical Organization',
    description: 'Organize agents into teams and organizations for better management'
  },
  {
    title: 'Real-time Monitoring',
    description: 'Track agent performance, task completion, and system metrics'
  },
  {
    title: 'Template-based Agents',
    description: 'Quick agent deployment using pre-built templates for common roles'
  },
  {
    title: 'RESTful API',
    description: 'Complete API for integration with existing tools and workflows'
  }
]

export default function DocsOverview() {
  return (
    <div className="prose prose-gray max-w-none">
      {/* Hero Section */}
      <div className="not-prose mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          FuzeAgent Documentation
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Build and manage autonomous AI development teams using Claude Code SDK. 
          Create specialized agents, assign complex tasks, and monitor progress in real-time.
        </p>
        
        <div className="flex flex-wrap gap-4">
          <Link
            to="/docs/getting-started"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            <FiPlay className="w-4 h-4" />
            Get Started
          </Link>
          <Link
            to="/docs/api-reference"
            className="inline-flex items-center gap-2 px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
          >
            <FiCode className="w-4 h-4" />
            API Reference
          </Link>
        </div>
      </div>

      {/* Quick Links */}
      <div className="not-prose mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Quick Links</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {quickLinks.map((link) => {
            const Icon = link.icon
            return (
              <Link
                key={link.path}
                to={link.path}
                className="group block p-6 bg-white rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-md transition-all"
              >
                <div className="flex items-start gap-4">
                  <div className={`p-3 rounded-lg ${link.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-blue-600 transition-colors">
                      {link.title}
                    </h3>
                    <p className="text-gray-600 text-sm">
                      {link.description}
                    </p>
                  </div>
                  <FiArrowRight className="w-5 h-5 text-gray-400 group-hover:text-blue-600 transition-colors" />
                </div>
              </Link>
            )
          })}
        </div>
      </div>

      {/* What is FuzeAgent */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">What is FuzeAgent?</h2>
        
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
          <p className="text-blue-900 leading-relaxed">
            FuzeAgent is an AI team orchestration platform that enables you to create, manage, and coordinate 
            autonomous AI agents for software development tasks. Built on top of Anthropic's Claude AI models 
            and integrated with Claude Code SDK, it provides a comprehensive solution for scaling development 
            teams with AI assistance.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {features.map((feature, index) => (
            <div key={index} className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                {feature.title}
              </h3>
              <p className="text-gray-600 text-sm">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture Overview */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Architecture Overview</h2>
        
        <div className="bg-gray-50 rounded-lg p-6 mb-6">
          <pre className="text-sm text-gray-700 overflow-x-auto">
{`┌─────────────────────────────────────────────────────────────────┐
│                         Management UI                            │
│                    (React + WebSocket + D3.js)                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                 Orchestration Service (FastAPI)                  │
│                        + CrewAI Core                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      Message Queue (RabbitMQ)                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                        Agent Containers                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  IzzyAI CEO │  │   CTO Agent │  │  CPO Agent  │  ...       │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└──────────────────────────────────────────────────────────────────┘`}
          </pre>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <FiMonitor className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Management Interface</h3>
            <p className="text-sm text-gray-600">
              Web-based UI for creating teams, managing agents, and monitoring tasks
            </p>
          </div>
          
          <div className="text-center">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <FiZap className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">Orchestration Engine</h3>
            <p className="text-sm text-gray-600">
              FastAPI service that coordinates tasks and manages agent lifecycle
            </p>
          </div>
          
          <div className="text-center">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <FiUsers className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="font-semibold text-gray-900 mb-2">AI Agents</h3>
            <p className="text-sm text-gray-600">
              Containerized agents running Claude AI models for specialized tasks
            </p>
          </div>
        </div>
      </section>

      {/* Next Steps */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Next Steps</h2>
        
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Ready to get started?</h3>
          <ol className="space-y-3 text-sm">
            <li className="flex items-center gap-3">
              <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-medium">1</span>
              <span>Follow the <Link to="/docs/getting-started" className="text-blue-600 hover:text-blue-800 font-medium">Getting Started guide</Link> to set up FuzeAgent</span>
            </li>
            <li className="flex items-center gap-3">
              <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-medium">2</span>
              <span>Create your first <Link to="/docs/organizations-teams" className="text-blue-600 hover:text-blue-800 font-medium">organization and team</Link></span>
            </li>
            <li className="flex items-center gap-3">
              <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-medium">3</span>
              <span>Deploy AI agents using our <Link to="/docs/creating-agents" className="text-blue-600 hover:text-blue-800 font-medium">agent templates</Link></span>
            </li>
            <li className="flex items-center gap-3">
              <span className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-medium">4</span>
              <span>Start assigning tasks and building your AI development team!</span>
            </li>
          </ol>
        </div>
      </section>
    </div>
  )
}