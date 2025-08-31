// Mock data that approximates the real API schema used by the UI

export let organizations = [
	{
		id: '9953005b-1395-4577-b01d-323c2e547681',
		name: 'Acme Corp',
		description: 'A leading technology company',
		settings: {},
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
	},
	{
		id: 'c4613ff9-d306-4535-a980-2baaedf4fe50',
		name: 'TechStart Inc',
		description: 'Innovative startup in AI',
		settings: {},
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
	},
]

export let teams = [
	{
		id: '4d0b5f8a-08b0-4d2a-9c6e-18f0f0d0a111',
		organization_id: organizations[0].id,
		name: 'Engineering',
		description: 'Core engineering team',
		team_type: 'development',
		color: '#2563eb',
		status: 'active',
		created: new Date().toISOString(),
		settings: {},
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		members: [
			{
				id: 'a1111111-2222-3333-4444-555555555555',
				name: 'React Developer 1',
				role: 'Frontend Developer',
				type: 'developer',
				status: 'active',
				joinedDate: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
				performance: {
					tasksCompleted: 12,
					tasksActive: 1,
					efficiency: '92%'
				}
			},
			{
				id: 'b1111111-2222-3333-4444-555555555555',
				name: 'Backend Dev 1',
				role: 'Backend Developer',
				type: 'developer',
				status: 'idle',
				joinedDate: new Date(Date.now() - 1000 * 60 * 60 * 24 * 45).toISOString(),
				performance: {
					tasksCompleted: 8,
					tasksActive: 0,
					efficiency: '88%'
				}
			}
		],
		stats: {
			totalTasks: 15,
			completedTasks: 20,
			activeTasks: 1,
			avgResponseTime: '2.3s'
		},
		knowledgeBase: []
	},
]

export let agents = [
	{
		id: 'a1111111-2222-3333-4444-555555555555',
		team_id: teams[0].id,
		name: 'React Developer 1',
		role: 'Frontend Developer',
		type: 'developer',
		status: 'active',
		config: {
			model: 'claude-sonnet-4-20250514',
			temperature: 0.7,
			tools: ['code_generation', 'code_review'],
			goal: 'Build high-quality React apps',
			backstory: 'Experienced frontend engineer'
		},
		template_id: 'react-dev',
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		tasks: { completed: 12, running: 1, pending: 2 },
		lastActivity: new Date().toISOString(),
		performance: {
			tasksCompleted: 12,
			tasksActive: 1,
			efficiency: '92%'
		},
		joinedDate: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
		conversations: [],
	},
	{
		id: 'b1111111-2222-3333-4444-555555555555',
		team_id: teams[0].id,
		name: 'Backend Dev 1',
		role: 'Backend Developer',
		type: 'developer',
		status: 'idle',
		config: {
			model: 'claude-sonnet-4-20250514',
			temperature: 0.7,
			tools: ['api_development'],
			goal: 'Build robust APIs',
			backstory: 'Backend specialist'
		},
		template_id: 'backend-dev',
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		tasks: { completed: 8, running: 0, pending: 1 },
		lastActivity: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
		performance: {
			tasksCompleted: 8,
			tasksActive: 0,
			efficiency: '88%'
		},
		joinedDate: new Date(Date.now() - 1000 * 60 * 60 * 24 * 45).toISOString(),
		conversations: [],
	},
]

// ---------------- Organization tools and settings (mock) ----------------
export type OrgTool = {
  id: string
  org_id: string
  key: string
  name: string
  description?: string
  default_config: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
}
export let orgTools: OrgTool[] = [
  {
    id: crypto.randomUUID(),
    org_id: organizations[0].id,
    key: 'code_generation',
    name: 'Code Generation',
    description: 'LLM-based code generation',
    default_config: { model: 'claude-sonnet-4-20250514', temperature: 0.4 },
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: crypto.randomUUID(),
    org_id: organizations[0].id,
    key: 'code_review',
    name: 'Code Review',
    description: 'Automated code review',
    default_config: { model: 'claude-sonnet-4-20250514', temperature: 0.2 },
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: crypto.randomUUID(),
    org_id: organizations[0].id,
    key: 'api_development',
    name: 'API Development',
    description: 'API scaffolding and contract testing',
    default_config: { language: 'python', framework: 'fastapi' },
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

export type TeamToolSetting = {
  team_id: string
  tool_id: string
  enabled: boolean
  config_override?: Record<string, any>
  updated_at: string
}
export let teamToolSettings: TeamToolSetting[] = [
  { team_id: teams[0].id, tool_id: orgTools[0].id, enabled: true, updated_at: new Date().toISOString() },
  { team_id: teams[0].id, tool_id: orgTools[1].id, enabled: true, updated_at: new Date().toISOString() },
]

export type AgentToolSetting = {
  agent_id: string
  tool_id: string
  enabled: boolean
  config_override?: Record<string, any>
  updated_at: string
}
export let agentToolSettings: AgentToolSetting[] = []

export let agentTemplates = [
	{
		id: 'react-dev',
		name: 'React Developer',
		category: 'DEVELOPMENT',
		description: 'Expert React developer specializing in modern frontend applications',
	},
	{
		id: 'backend-dev',
		name: 'Backend Developer',
		category: 'DEVELOPMENT',
		description: 'API and database expert',
	},
]

export let knowledgeDocs = [
	{
		id: 'doc-1',
		title: 'Engineering Handbook',
		source: 'upload',
		created_at: new Date().toISOString(),
	},
]

// Simple task store
export let tasks: Array<{
  id: string
  title: string
  description: string
  status: 'pending' | 'in_progress' | 'completed'
  priority: 'low' | 'medium' | 'high'
  created_at: string
  completed_at?: string
  team_id?: string
  agent_id?: string
}> = []

// Organizational goals
export type Goal = {
  id: string
  organization_id: string
  title: string
  description: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'planning' | 'active' | 'completed' | 'on_hold'
  target_completion_date: string
  progress_percentage: number
  assigned_teams: string[]
  milestones: {
    id: string
    title: string
    status: string
    due_date: string
  }[]
  created_at: string
  updated_at: string
}

export let goals: Goal[] = []

// Conversations and messages types (nested under agents)
export type ChatMessage = {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  status?: 'sending' | 'sent'
  metadata?: Record<string, unknown>
}
export type Conversation = {
  id: string
  agent_id: string
  title: string
  created_at: string
  updated_at: string
  status: 'running' | 'paused' | 'stopped'
  messages: ChatMessage[]
}

export function jsonResponse(body: unknown, init: ResponseInit = { status: 200 }) {
	return new Response(JSON.stringify(body), {
		...init,
		headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
	})
}

// LocalStorage-backed persistence for mock data
const STORAGE_KEY = 'fuzeagent_mock_db_v1'

type MockDB = {
	organizations: typeof organizations
	teams: typeof teams
	agents: typeof agents
	agentTemplates: typeof agentTemplates
	knowledgeDocs: typeof knowledgeDocs
	tasks: typeof tasks
	goals: typeof goals
	orgTools: typeof orgTools
	teamToolSettings: typeof teamToolSettings
	agentToolSettings: typeof agentToolSettings
}

function canUseLocalStorage(): boolean {
	try {
		return typeof localStorage !== 'undefined'
	} catch {
		return false
	}
}

export function saveMockDB() {
	if (!canUseLocalStorage()) return
	const state: MockDB = {
		organizations,
		teams,
		agents,
		agentTemplates,
		knowledgeDocs,
		tasks,
		goals,
		orgTools,
		teamToolSettings,
		agentToolSettings,
	}
	localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export function loadMockDB() {
	if (!canUseLocalStorage()) return
	const raw = localStorage.getItem(STORAGE_KEY)
	if (!raw) {
		// Seed with defaults but persist immediately for consistency across reloads
		saveMockDB()
		return
	}
	try {
		const parsed = JSON.parse(raw) as Partial<MockDB & { conversations?: any[]; messages?: ChatMessage[] }>
		if (parsed.organizations && Array.isArray(parsed.organizations)) organizations = parsed.organizations as any
		if (parsed.teams && Array.isArray(parsed.teams)) teams = parsed.teams as any
		if (parsed.agents && Array.isArray(parsed.agents)) agents = parsed.agents as any
		if (parsed.agentTemplates && Array.isArray(parsed.agentTemplates)) agentTemplates = parsed.agentTemplates as any
		if (parsed.knowledgeDocs && Array.isArray(parsed.knowledgeDocs)) knowledgeDocs = parsed.knowledgeDocs as any
		if (parsed.tasks && Array.isArray(parsed.tasks)) tasks = parsed.tasks as any
		if ((parsed as any).goals && Array.isArray((parsed as any).goals)) goals = (parsed as any).goals as any
		if ((parsed as any).orgTools && Array.isArray((parsed as any).orgTools)) orgTools = (parsed as any).orgTools as any
		if ((parsed as any).teamToolSettings && Array.isArray((parsed as any).teamToolSettings)) teamToolSettings = (parsed as any).teamToolSettings as any
		if ((parsed as any).agentToolSettings && Array.isArray((parsed as any).agentToolSettings)) agentToolSettings = (parsed as any).agentToolSettings as any
		// Migration: move top-level conversations/messages into agents
		const topConversations = (parsed as any).conversations as any[] | undefined
		const topMessages = (parsed as any).messages as ChatMessage[] | undefined
		if (Array.isArray(topConversations) || Array.isArray(topMessages)) {
			// Ensure conversations array on all agents
			agents = (agents as any[]).map(a => ({ ...a, conversations: Array.isArray(a.conversations) ? a.conversations : [] })) as any
			if (Array.isArray(topConversations)) {
				for (const c of topConversations) {
					const idx = (agents as any[]).findIndex(a => a.id === c.agent_id)
					if (idx !== -1) {
						const exists = (agents as any[])[idx].conversations.find((x: any) => x.id === c.id)
						if (!exists) {
							(agents as any[])[idx].conversations.push({ ...c, messages: [] })
						}
					}
				}
			}
			if (Array.isArray(topMessages)) {
				for (const m of topMessages) {
					for (const a of agents as any[]) {
						const ci = a.conversations?.findIndex((c: any) => c.id === m.conversation_id) ?? -1
						if (ci !== -1) {
							a.conversations[ci].messages = Array.isArray(a.conversations[ci].messages) ? a.conversations[ci].messages : []
							a.conversations[ci].messages.push(m)
							break
						}
					}
				}
			}
			// After migration, re-save without legacy keys
			saveMockDB()
		}
	} catch {
		// On parse error, re-save defaults
		saveMockDB()
	}
}

// Hydrate immediately on module load
loadMockDB()
