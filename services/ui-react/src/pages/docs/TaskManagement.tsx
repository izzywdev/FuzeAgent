import { FiCheckCircle, FiClock, FiUser, FiZap } from 'react-icons/fi'

export default function TaskManagement() {
  return (
    <div className="prose prose-gray max-w-none">
      <h1>Task Management</h1>
      
      <p className="lead">
        Learn how to create, assign, and monitor tasks across your AI agent teams. 
        FuzeAgent provides comprehensive task orchestration capabilities.
      </p>

      <h2>Task Lifecycle</h2>
      
      <div className="not-prose mb-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg">
            <FiClock className="w-8 h-8 text-blue-600 mx-auto mb-2" />
            <h3 className="font-semibold text-blue-900">Created</h3>
            <p className="text-sm text-blue-700">Task is created and queued</p>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <FiUser className="w-8 h-8 text-yellow-600 mx-auto mb-2" />
            <h3 className="font-semibold text-yellow-900">Assigned</h3>
            <p className="text-sm text-yellow-700">Assigned to appropriate agent</p>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <FiZap className="w-8 h-8 text-purple-600 mx-auto mb-2" />
            <h3 className="font-semibold text-purple-900">In Progress</h3>
            <p className="text-sm text-purple-700">Agent is working on task</p>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <FiCheckCircle className="w-8 h-8 text-green-600 mx-auto mb-2" />
            <h3 className="font-semibold text-green-900">Completed</h3>
            <p className="text-sm text-green-700">Task finished successfully</p>
          </div>
        </div>
      </div>

      <h2>Creating Tasks</h2>

      <p>Tasks can be created through the API or management interface:</p>

      <pre><code>{`// Create a new task
const taskData = {
  title: "Implement user authentication",
  description: "Add JWT-based authentication with login/logout",
  priority: 8,
  tags: ["authentication", "security", "backend"],
  requirements: [
    "Use JWT tokens",
    "Implement password hashing",
    "Add rate limiting",
    "Include unit tests"
  ]
}

const response = await fetch('/api/agents/agent_123/tasks', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(taskData)
})`}</code></pre>

      <h2>Task Assignment</h2>

      <p>FuzeAgent automatically assigns tasks based on:</p>

      <ul>
        <li><strong>Agent Skills</strong>: Matching required skills to agent capabilities</li>
        <li><strong>Workload</strong>: Current task queue and availability</li>
        <li><strong>Priority</strong>: High-priority tasks get preference</li>
        <li><strong>Specialization</strong>: Task type matches agent specialization</li>
      </ul>

      <h2>Monitoring Progress</h2>

      <p>Track task progress in real-time:</p>

      <pre><code>{`// Get task status
const task = await fetch('/api/tasks/task_456');
const taskData = await task.json();

console.log(taskData);
// {
//   "id": "task_456",
//   "status": "in_progress",
//   "progress": 0.65,
//   "agent_id": "agent_123",
//   "estimated_completion": "2024-01-15T16:30:00Z",
//   "updates": [
//     {
//       "timestamp": "2024-01-15T14:00:00Z",
//       "message": "Started authentication implementation"
//     },
//     {
//       "timestamp": "2024-01-15T15:15:00Z", 
//       "message": "JWT token generation completed"
//     }
//   ]
// }`}</code></pre>

      <h2>Task Types</h2>

      <div className="not-prose mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Development Tasks</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Feature implementation</li>
              <li>• Bug fixes</li>
              <li>• Code refactoring</li>
              <li>• API development</li>
            </ul>
          </div>
          
          <div className="border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Quality Assurance</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Test case writing</li>
              <li>• Code review</li>
              <li>• Performance optimization</li>
              <li>• Security audits</li>
            </ul>
          </div>

          <div className="border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Documentation</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• API documentation</li>
              <li>• User guides</li>
              <li>• Code comments</li>
              <li>• Architecture diagrams</li>
            </ul>
          </div>

          <div className="border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">DevOps</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Deployment automation</li>
              <li>• Infrastructure setup</li>
              <li>• Monitoring configuration</li>
              <li>• CI/CD pipelines</li>
            </ul>
          </div>
        </div>
      </div>

      <h2>Best Practices</h2>

      <h3>Clear Task Descriptions</h3>

      <p>Write specific, actionable task descriptions:</p>

      <div className="not-prose mb-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
          <h4 className="text-green-800 font-semibold mb-2">✅ Good Example</h4>
          <p className="text-green-700 text-sm">
            "Implement JWT-based authentication for the user login endpoint. Include password hashing with bcrypt, 
            rate limiting (5 attempts per minute), and comprehensive unit tests. Return 401 for invalid credentials 
            and 200 with token for successful login."
          </p>
        </div>

        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="text-red-800 font-semibold mb-2">❌ Poor Example</h4>
          <p className="text-red-700 text-sm">
            "Add login functionality"
          </p>
        </div>
      </div>

      <h3>Priority Guidelines</h3>

      <ul>
        <li><strong>1-3 (Low)</strong>: Nice-to-have features, documentation updates</li>
        <li><strong>4-6 (Medium)</strong>: Regular features, minor bug fixes</li>
        <li><strong>7-8 (High)</strong>: Important features, security fixes</li>
        <li><strong>9-10 (Critical)</strong>: Production issues, blocking bugs</li>
      </ul>

      <h2>Advanced Features</h2>

      <h3>Task Dependencies</h3>

      <pre><code>{`const taskWithDependencies = {
  title: "Deploy user service",
  description: "Deploy the user authentication service to production",
  dependencies: ["task_123", "task_124"], // Must complete first
  priority: 7
}`}</code></pre>

      <h3>Recurring Tasks</h3>

      <pre><code>{`const recurringTask = {
  title: "Security audit",
  schedule: "0 0 * * 1", // Every Monday at midnight
  template: {
    description: "Weekly security audit of all endpoints",
    priority: 6,
    tags: ["security", "audit"]
  }
}`}</code></pre>

      <h3>Task Templates</h3>

      <p>Create reusable task templates for common activities:</p>

      <pre><code>{`const templates = {
  "feature_implementation": {
    title: "Implement [FEATURE_NAME]",
    description: "Implement [FEATURE_NAME] with full test coverage",
    requirements: [
      "Follow coding standards",
      "Write unit tests",
      "Update documentation",
      "Add error handling"
    ],
    tags: ["feature", "development"]
  }
}`}</code></pre>
    </div>
  )
}