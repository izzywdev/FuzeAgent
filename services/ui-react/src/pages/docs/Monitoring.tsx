export default function Monitoring() {
  return (
    <div className="prose prose-gray max-w-none">
      <h1>Monitoring & Analytics</h1>
      
      <p className="lead">
        Monitor your AI agents, track performance metrics, and gain insights into your 
        development team's productivity with FuzeAgent's comprehensive monitoring suite.
      </p>

      <h2>Overview Dashboard</h2>

      <p>The main dashboard provides real-time insights into your AI team performance:</p>

      <div className="not-prose mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-600">24</div>
            <div className="text-sm text-blue-700">Active Agents</div>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-600">156</div>
            <div className="text-sm text-green-700">Tasks Completed</div>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-purple-600">94%</div>
            <div className="text-sm text-purple-700">Success Rate</div>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-yellow-600">2.3h</div>
            <div className="text-sm text-yellow-700">Avg Task Time</div>
          </div>
        </div>
      </div>

      <h2>Agent Performance Metrics</h2>

      <p>Track individual agent performance and productivity:</p>

      <pre><code>{`// Get agent performance data
const metrics = await fetch('/api/agents/agent_123/metrics')
const performance = await metrics.json()

console.log(performance)
// {
//   "agent_id": "agent_123",
//   "name": "React Developer",
//   "period": "last_30_days",
//   "metrics": {
//     "tasks_completed": 45,
//     "tasks_failed": 3,
//     "success_rate": 0.94,
//     "average_completion_time": "2.5 hours",
//     "total_tokens_used": 2500000,
//     "cost_per_task": 0.15,
//     "productivity_score": 8.7,
//     "skills_utilization": {
//       "react": 0.85,
//       "typescript": 0.92,
//       "tailwind": 0.78
//     }
//   }
// }`}</code></pre>

      <h3>Key Performance Indicators</h3>

      <ul>
        <li><strong>Success Rate</strong>: Percentage of tasks completed successfully</li>
        <li><strong>Average Completion Time</strong>: Mean time to complete tasks</li>
        <li><strong>Token Usage</strong>: API tokens consumed per task</li>
        <li><strong>Cost Efficiency</strong>: Cost per completed task</li>
        <li><strong>Skill Utilization</strong>: How often agent skills are used</li>
        <li><strong>Productivity Score</strong>: Overall performance rating (1-10)</li>
      </ul>

      <h2>Team Analytics</h2>

      <p>Monitor team-level performance and collaboration:</p>

      <pre><code>{`// Get team analytics
const teamStats = await fetch('/api/teams/team_456/analytics')
const analytics = await teamStats.json()

console.log(analytics)
// {
//   "team_id": "team_456",
//   "name": "Frontend Team",
//   "period": "current_month",
//   "summary": {
//     "agents_count": 5,
//     "active_tasks": 12,
//     "completed_tasks": 89,
//     "team_velocity": 18.5, // tasks per week
//     "collaboration_score": 7.8,
//     "knowledge_sharing": 0.72
//   },
//   "top_performers": [
//     {
//       "agent_id": "agent_789",
//       "name": "Senior React Dev",
//       "completion_rate": 0.98
//     }
//   ]
// }`}</code></pre>

      <h2>Real-time Monitoring</h2>

      <p>Monitor agent activities and system health in real-time:</p>

      <pre><code>{`// WebSocket connection for real-time updates
const ws = new WebSocket('ws://localhost:8006/monitoring')

ws.onmessage = (event) => {
  const update = JSON.parse(event.data)
  
  switch (update.type) {
    case 'agent_status_change':
      console.log(\`Agent \${update.agent_id} is now \${update.status}\`)
      break
      
    case 'task_completed':
      console.log(\`Task \${update.task_id} completed by \${update.agent_id}\`)
      updateDashboard(update)
      break
      
    case 'system_alert':
      if (update.severity === 'high') {
        showAlert(update.message)
      }
      break
  }
}`}</code></pre>

      <h3>System Health Monitoring</h3>

      <div className="not-prose mb-8">
        <div className="bg-gray-50 rounded-lg p-6">
          <h4 className="font-semibold text-gray-900 mb-4">Health Check Endpoints</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Orchestration Service</span>
              <span className="text-green-600">✅ Healthy</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">PostgreSQL Database</span>
              <span className="text-green-600">✅ Healthy</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">RabbitMQ Queue</span>
              <span className="text-green-600">✅ Healthy</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Redis Cache</span>
              <span className="text-yellow-600">⚠️ Warning</span>
            </div>
          </div>
        </div>
      </div>

      <h2>Cost Tracking</h2>

      <p>Monitor API usage and costs across your organization:</p>

      <pre><code>{`// Get cost breakdown
const costs = await fetch('/api/analytics/costs?period=current_month')
const costData = await costs.json()

console.log(costData)
// {
//   "period": "2024-01",
//   "total_cost": 247.85,
//   "cost_breakdown": {
//     "claude_sonnet": 189.50,
//     "claude_haiku": 45.20,
//     "claude_opus": 13.15
//   },
//   "cost_by_team": {
//     "frontend_team": 98.40,
//     "backend_team": 124.30,
//     "devops_team": 25.15
//   },
//   "tokens_used": 15500000,
//   "average_cost_per_task": 1.58
// }`}</code></pre>

      <h3>Cost Optimization</h3>

      <ul>
        <li><strong>Model Selection</strong>: Use appropriate models for task complexity</li>
        <li><strong>Token Management</strong>: Optimize prompts to reduce token usage</li>
        <li><strong>Task Batching</strong>: Group related tasks to reduce overhead</li>
        <li><strong>Caching</strong>: Implement response caching for repeated queries</li>
      </ul>

      <h2>Alerting & Notifications</h2>

      <p>Set up alerts for important events and thresholds:</p>

      <pre><code>{`// Configure alerts
const alertConfig = {
  rules: [
    {
      name: "High failure rate",
      condition: "success_rate < 0.8",
      notification: {
        channels: ["email", "slack"],
        recipients: ["team-leads@company.com"]
      }
    },
    {
      name: "Cost threshold exceeded",
      condition: "daily_cost > 100",
      notification: {
        channels: ["email"],
        recipients: ["finance@company.com"]
      }
    },
    {
      name: "Agent unavailable",
      condition: "agent_status = 'error' for > 5 minutes",
      notification: {
        channels: ["slack", "pagerduty"],
        urgency: "high"
      }
    }
  ]
}

await fetch('/api/alerts/configure', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(alertConfig)
})`}</code></pre>

      <h2>Performance Optimization</h2>

      <h3>Identifying Bottlenecks</h3>

      <pre><code>{`// Analyze performance bottlenecks
const bottlenecks = await fetch('/api/analytics/bottlenecks')
const analysis = await bottlenecks.json()

console.log(analysis)
// {
//   "slow_agents": [
//     {
//       "agent_id": "agent_456",
//       "average_time": "5.2 hours",
//       "recommended_action": "Optimize system prompt"
//     }
//   ],
//   "queue_delays": {
//     "average_wait_time": "12 minutes",
//     "peak_hours": ["09:00-11:00", "14:00-16:00"]
//   },
//   "resource_usage": {
//     "cpu_utilization": 0.75,
//     "memory_usage": 0.68,
//     "recommendations": [
//       "Scale up during peak hours",
//       "Implement task prioritization"
//     ]
//   }
// }`}</code></pre>

      <h3>Optimization Strategies</h3>

      <ul>
        <li><strong>Load Balancing</strong>: Distribute tasks evenly across agents</li>
        <li><strong>Skill Matching</strong>: Assign tasks to best-suited agents</li>
        <li><strong>Prompt Optimization</strong>: Refine system prompts for efficiency</li>
        <li><strong>Resource Scaling</strong>: Auto-scale based on demand</li>
      </ul>

      <h2>Reporting</h2>

      <p>Generate comprehensive reports for stakeholders:</p>

      <pre><code>{`// Generate monthly report
const report = await fetch('/api/reports/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    type: 'monthly_summary',
    period: '2024-01',
    include_sections: [
      'executive_summary',
      'team_performance', 
      'cost_analysis',
      'recommendations'
    ],
    format: 'pdf'
  })
})

const reportData = await report.json()
console.log('Report generated:', reportData.download_url)`}</code></pre>

      <h3>Report Types</h3>

      <div className="not-prose mb-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border border-gray-200 rounded-lg p-6">
            <h4 className="font-semibold text-gray-900 mb-3">Executive Reports</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• High-level performance metrics</li>
              <li>• Cost summaries and trends</li>
              <li>• ROI analysis</li>
              <li>• Strategic recommendations</li>
            </ul>
          </div>

          <div className="border border-gray-200 rounded-lg p-6">
            <h4 className="font-semibold text-gray-900 mb-3">Technical Reports</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• Detailed agent performance</li>
              <li>• System utilization metrics</li>
              <li>• Error analysis and debugging</li>
              <li>• Optimization recommendations</li>
            </ul>
          </div>
        </div>
      </div>

      <h2>Best Practices</h2>

      <h3>Monitoring Strategy</h3>

      <ul>
        <li><strong>Baseline Metrics</strong>: Establish performance baselines for comparison</li>
        <li><strong>Regular Reviews</strong>: Weekly team performance reviews</li>
        <li><strong>Proactive Alerts</strong>: Set up alerts before problems become critical</li>
        <li><strong>Continuous Optimization</strong>: Regular tuning based on metrics</li>
      </ul>

      <h3>Data Retention</h3>

      <pre><code>{`// Configure data retention policies
const retentionPolicy = {
  metrics: {
    detailed: "30 days",
    aggregated: "1 year", 
    archived: "3 years"
  },
  logs: {
    error_logs: "90 days",
    access_logs: "30 days",
    audit_logs: "2 years"
  }
}`}</code></pre>

      <div className="not-prose mt-12">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-blue-900 font-semibold mb-4">Need help with monitoring?</h3>
          <p className="text-blue-700 text-sm mb-4">
            Our monitoring tools help you optimize your AI team performance and reduce costs.
          </p>
          <div className="space-y-2">
            <div className="text-blue-700 text-sm">
              📊 <strong>Real-time dashboards</strong> for immediate insights
            </div>
            <div className="text-blue-700 text-sm">
              🔍 <strong>Performance analytics</strong> to identify optimization opportunities
            </div>
            <div className="text-blue-700 text-sm">
              💰 <strong>Cost tracking</strong> to manage AI development expenses
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}