// Very small mock fetch layer that intercepts calls the app makes and returns realistic data
// Disable by not importing this module in main.tsx

import { agents, teams, organizations, agentTemplates, knowledgeDocs, jsonResponse, saveMockDB, loadMockDB, tasks } from './data'
import type { ChatMessage } from './data'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

function match(url: string, _method: HttpMethod) {
	const u = new URL(url, window.location.origin)
	const path = u.pathname
	return { path, url: u }
}

async function handleRequest(input: RequestInfo | URL, init?: RequestInit) {
	const href = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url
	const method = ((init?.method || (typeof input !== 'string' && !(input instanceof URL) ? (input as Request).method : 'GET')) as HttpMethod) || 'GET'
	const { path } = match(href, method)

	// Ensure latest data loaded
	loadMockDB()

	// Hierarchy API
	if (method === 'GET' && path === '/organizations') return jsonResponse(organizations)
	if (method === 'GET' && path.startsWith('/organizations/')) {
		const id = path.split('/')[2]
		const org = organizations.find(o => o.id === id) || organizations[0]
		return jsonResponse(org)
	}
	if (method === 'PUT' && path.startsWith('/organizations/')) {
		// accept update and echo
		const id = path.split('/')[2]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		return jsonResponse({ ...organizations.find(o => o.id === id), ...body })
	}
	if (method === 'GET' && path === '/teams') return jsonResponse(teams)
	if (method === 'POST' && path === '/teams') {
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const newTeam = {
			id: crypto.randomUUID(),
			organization_id: body.organization_id,
			name: body.name,
			description: body.description,
			team_type: body.team_type,
			color: body.settings?.color || '#2563eb',
			status: 'active',
			created: new Date().toISOString(),
			settings: body.settings || {},
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString(),
			members: [],
			stats: {
				totalTasks: 0,
				completedTasks: 0,
				activeTasks: 0,
				avgResponseTime: '0s'
			},
			knowledgeBase: []
		}
		teams.push(newTeam)
		saveMockDB()
		return jsonResponse(newTeam, { status: 201 })
	}
	// Team members: attach an existing agent to a team (enforce one team per agent)
	if (method === 'POST' && path.startsWith('/teams/') && path.endsWith('/members')) {
		const teamId = path.split('/')[2]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const teamIdx = teams.findIndex(t => t.id === teamId)
		if (teamIdx === -1) return jsonResponse({ message: 'Team not found' }, { status: 404 })
		const agentId = body.agent_id as string | undefined
		if (!agentId) return jsonResponse({ message: 'agent_id is required' }, { status: 400 })
		const agentIdx = agents.findIndex(a => a.id === agentId)
		if (agentIdx === -1) return jsonResponse({ message: 'Agent not found' }, { status: 404 })
		const now = new Date().toISOString()
		const agent = agents[agentIdx] as any
		// If agent already in this team and member exists, return existing
		const alreadyInTeam = agent.team_id === teamId
		const existingMemberIdx = teams[teamIdx].members.findIndex(m => m.id === agentId)
		if (alreadyInTeam && existingMemberIdx !== -1) {
			return jsonResponse({ member: teams[teamIdx].members[existingMemberIdx], agent_id: agentId, team_id: teamId })
		}
		// Remove from previous team's members if present
		if (agent.team_id) {
			const prevIdx = teams.findIndex(t => t.id === agent.team_id)
			if (prevIdx !== -1) {
				const memberIdx = teams[prevIdx].members.findIndex(m => m.id === agentId)
				if (memberIdx !== -1) teams[prevIdx].members.splice(memberIdx, 1)
			}
		}
		// Update agent's team assignment
		agent.team_id = teamId
		agent.updated_at = now
		agents[agentIdx] = agent
		// Create or update member record for target team
		const member = {
			id: agent.id,
			name: agent.name,
			role: agent.role,
			type: agent.type,
			status: agent.status || 'active',
			joinedDate: agent.joinedDate || now,
			performance: agent.performance || { tasksCompleted: 0, tasksActive: 0, efficiency: '0%' }
		}
		if (existingMemberIdx === -1) {
			teams[teamIdx].members.push(member as any)
		} else {
			teams[teamIdx].members[existingMemberIdx] = member as any
		}
		saveMockDB()
		return jsonResponse({ member, agent_id: agentId, team_id: teamId }, { status: 201 })
	}
	if (method === 'GET' && path.startsWith('/teams/') && !path.endsWith('/tasks')) {
		const id = path.split('/')[2]
		const team = teams.find(t => t.id === id)
		if (team) {
			return jsonResponse(team)
		}
		return jsonResponse({ message: 'Team not found' }, { status: 404 })
	}

	// Team tasks
	if (method === 'GET' && path.startsWith('/teams/') && path.endsWith('/tasks')) {
		const teamId = path.split('/')[2]
		return jsonResponse(tasks.filter(t => t.team_id === teamId))
	}
	if (method === 'POST' && path.startsWith('/teams/') && path.endsWith('/tasks')) {
		const teamId = path.split('/')[2]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const now = new Date().toISOString()
		const newTask = {
			id: crypto.randomUUID(),
			title: body.title || 'New Task',
			description: body.description || '',
			status: (body.status || 'pending') as any,
			priority: (body.priority || 'medium') as any,
			created_at: now,
			team_id: teamId,
			agent_id: body.agent_id || undefined,
		}
		tasks.push(newTask as any)
		saveMockDB()
		return jsonResponse(newTask, { status: 201 })
	}

	// Assign existing task to agent
	if (method === 'PUT' && path.startsWith('/tasks/') && path.endsWith('/assign')) {
		const taskId = path.split('/')[2]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const agentId = body.agent_id as string | undefined
		const idx = tasks.findIndex(t => t.id === taskId)
		if (idx === -1) return jsonResponse({ message: 'Task not found' }, { status: 404 })
		if (!agentId) return jsonResponse({ message: 'agent_id is required' }, { status: 400 })
		const agent = agents.find(a => a.id === agentId)
		if (!agent) return jsonResponse({ message: 'Agent not found' }, { status: 404 })
		// Optional: ensure team matches
		if (tasks[idx].team_id && agent.team_id && tasks[idx].team_id !== agent.team_id) {
			return jsonResponse({ message: 'Task belongs to another team' }, { status: 400 })
		}
		tasks[idx] = { ...tasks[idx], agent_id: agentId }
		saveMockDB()
		return jsonResponse(tasks[idx])
	}

	// Orchestrator-like endpoints
	if (method === 'GET' && path === '/agents') return jsonResponse(agents)
	if (method === 'POST' && path === '/agents') {
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const id = crypto.randomUUID()
		const now = new Date().toISOString()
		const cfg = body.config || {
			model: 'claude-sonnet-4-20250514',
			temperature: 0.7,
			tools: [],
			goal: '',
			backstory: ''
		}
		const newAgent = {
			id,
			team_id: body.team_id || (teams[0]?.id || ''),
			name: body.name || 'New Agent',
			role: body.role || 'Agent',
			type: body.type || 'developer',
			status: 'active',
			config: cfg,
			template_id: body.template_id || undefined,
			created_at: now,
			updated_at: now,
			tasks: { completed: 0, running: 0, pending: 0 },
			lastActivity: now,
			performance: {
				tasksCompleted: 0,
				tasksActive: 0,
				efficiency: '0%'
			},
			joinedDate: now,
			conversations: []
		}
		agents.push(newAgent)
		saveMockDB()
		return jsonResponse({ agent_id: id, status: 'created', agent: newAgent }, { status: 201 })
	}
	if (method === 'GET' && path.startsWith('/agents/') && path.endsWith('/tasks')) {
		const id = path.split('/')[2]
		return jsonResponse(tasks.filter(t => t.agent_id === id))
	}
	if (method === 'POST' && path.startsWith('/agents/') && path.endsWith('/tasks')) {
		const id = path.split('/')[2]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const now = new Date().toISOString()
		const newTask = {
			id: crypto.randomUUID(),
			title: body.title || 'New Task',
			description: body.description || '',
			status: (body.status || 'pending') as any,
			priority: (body.priority || 'medium') as any,
			created_at: now,
			agent_id: id,
			team_id: body.team_id || agents.find(a => a.id === id)?.team_id,
		}
		tasks.push(newTask as any)
		saveMockDB()
		return jsonResponse(newTask, { status: 201 })
	}
	if (method === 'GET' && path.startsWith('/agents/') && !path.includes('/tasks') && !path.includes('/conversations')) {
		const id = path.split('/')[2]
		return jsonResponse(agents.find(a => a.id === id) || agents[0])
	}
	if (method === 'PUT' && path.startsWith('/agents/')) {
		const id = path.split('/')[2]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const idx = agents.findIndex(a => a.id === id)
		if (idx === -1) return jsonResponse({ message: 'Agent not found' }, { status: 404 })
		const existing = agents[idx]
		const updated = {
			...existing,
			...body,
			config: { ...existing.config, ...(body.config || {}) },
			updated_at: new Date().toISOString(),
		}
		agents[idx] = updated as any
		saveMockDB()
		return jsonResponse(updated)
	}
	if (method === 'GET' && path === '/agent-templates') return jsonResponse(agentTemplates)

	// Knowledge endpoints
	if (method === 'GET' && path.includes('/knowledge/')) return jsonResponse(knowledgeDocs)
	if (method === 'POST' && path.includes('/knowledge/')) { const res = jsonResponse({ ok: true }, { status: 201 }); saveMockDB(); return res }
	if (method === 'DELETE' && path.includes('/knowledge/')) { const res = jsonResponse({ ok: true }); saveMockDB(); return res }

	// Conversations endpoints (now nested under agent objects)
	if (method === 'GET' && path.startsWith('/agents/') && path.endsWith('/conversations')) {
		const agentId = path.split('/')[2]
		const aIdx = agents.findIndex(a => (a as any).id === agentId)
		if (aIdx === -1) return jsonResponse([], { status: 200 })
		const list = ((agents as any)[aIdx].conversations || [])
		if (list.length === 0) {
			const now = new Date().toISOString()
			const convo = { id: crypto.randomUUID(), agent_id: agentId, title: 'Conversation', created_at: now, updated_at: now, status: 'running' as const, messages: [] }
			;(agents as any)[aIdx].conversations = [convo]
			saveMockDB()
			return jsonResponse([convo])
		}
		return jsonResponse(list)
	}
	if (method === 'POST' && path.startsWith('/agents/') && path.endsWith('/conversations')) {
		const agentId = path.split('/')[2]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const now = new Date().toISOString()
		const aIdx = agents.findIndex(a => (a as any).id === agentId)
		if (aIdx === -1) return jsonResponse({ message: 'Agent not found' }, { status: 404 })
		const existing = ((agents as any)[aIdx].conversations || [])[0]
		if (existing) return jsonResponse(existing)
		const convo = { id: crypto.randomUUID(), agent_id: agentId, title: body.title || 'Conversation', created_at: now, updated_at: now, status: 'running' as const, messages: [] }
		;(agents as any)[aIdx].conversations = [convo]
		saveMockDB()
		return jsonResponse(convo, { status: 201 })
	}
	if (method === 'GET' && path.includes('/conversations/') && path.endsWith('/messages')) {
		const parts = path.split('/')
		const conversationId = parts[4]
		// Load from nested agent store
		for (const a of agents as any[]) {
			const c = a.conversations?.find((x: any) => x.id === conversationId)
			if (c) return jsonResponse(c.messages || [])
		}
		return jsonResponse([])
	}
	if (method === 'POST' && path.includes('/conversations/') && path.endsWith('/messages')) {
		const parts = path.split('/')
		const agentId = parts[2]
		const conversationId = parts[4]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const now = new Date().toISOString()
		const userMsg: ChatMessage = { id: crypto.randomUUID(), conversation_id: conversationId, role: 'user', content: body.content || body.message || '', timestamp: now, status: 'sent' }
		for (const a of agents as any[]) {
			const ci = a.conversations?.findIndex((c: any) => c.id === conversationId) ?? -1
			if (ci !== -1) {
				a.conversations[ci].updated_at = now
				a.conversations[ci].messages = Array.isArray(a.conversations[ci].messages) ? a.conversations[ci].messages : []
				a.conversations[ci].messages.push(userMsg)
				break
			}
		}
		saveMockDB()
		// Do not broadcast the user's message to avoid client duplication; only simulate agent reply
		simulateAgentReply(agentId, conversationId)
		return jsonResponse(userMsg, { status: 201 })
	}

	// Conversation status update
	if (method === 'PUT' && path.startsWith('/conversations/') && path.endsWith('/status')) {
		const conversationId = path.split('/')[2]
		const body = init?.body ? JSON.parse(init.body as string) : {}
		const status = body.status as 'running' | 'paused' | 'stopped' | undefined
		let updated: any = null
		for (const a of agents as any[]) {
			const ci = a.conversations?.findIndex((c: any) => c.id === conversationId) ?? -1
			if (ci !== -1) {
				if (!status || !['running','paused','stopped'].includes(status)) return jsonResponse({ message: 'Invalid status' }, { status: 400 })
				a.conversations[ci] = { ...a.conversations[ci], status, updated_at: new Date().toISOString() }
				updated = a.conversations[ci]
				break
			}
		}
		if (!updated) return jsonResponse({ message: 'Conversation not found' }, { status: 404 })
		saveMockDB()
		return jsonResponse(updated)
	}

	// Default fallthrough
	return jsonResponse({ message: 'Mock endpoint not implemented', path, method }, { status: 404 })
}

export function enableMockApi() {
	if ((window as any).__mockApiEnabled) return
	const origFetch = window.fetch.bind(window)
	const apiPrefixes = ['/agents', '/teams', '/organizations', '/agent-templates', '/knowledge', '/rag', '/tasks']
	window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
		const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url
		const u = new URL(raw, window.location.origin)
		const path = u.pathname
		const shouldIntercept =
			raw.startsWith('http://localhost:8000') ||
			raw.startsWith('http://localhost:8006') ||
			raw.startsWith('/api') ||
			apiPrefixes.some(p => path.startsWith(p))
		if (shouldIntercept) {
			const mapped = path + (u.search || '')
			return handleRequest(mapped, init)
		}
		return origFetch(input as any, init)
	}) as any
	;(window as any).__mockApiEnabled = true
	console.info('[MockAPI] Enabled')
}

// --- Mock WebSocket for conversations ---
type WSHandler = ((event: { data: string }) => void) | null
class MockWebSocket {
	url: string
	readyState: number
	onopen: (() => void) | null = null
	onmessage: WSHandler = null
	onerror: ((err: unknown) => void) | null = null
	onclose: (() => void) | null = null
	private conversationId: string
	constructor(url: string) {
		this.url = url
		this.readyState = 0
		// Parse conversation id: /ws/agents/{agentId}/conversations/{conversationId}
		try {
			const u = new URL(url, window.location.origin)
			const parts = u.pathname.split('/')
			this.conversationId = parts[5]
		} catch {
			this.conversationId = ''
		}
		setTimeout(() => {
			this.readyState = 1
			registerWsClient(this.conversationId, this)
			this.onopen && this.onopen()
			// optional: send initial pong to confirm
		}, 10)
	}
	send(data: string) {
		try {
			const parsed = JSON.parse(data)
			if (parsed.type === 'ping') {
				this.onmessage && this.onmessage({ data: JSON.stringify({ type: 'pong' }) })
				return
			}
			if (parsed.type === 'message') {
				// Treat as user message via WS
				const now = new Date().toISOString()
				const msg: ChatMessage = { id: crypto.randomUUID(), conversation_id: this.conversationId, role: 'user', content: parsed.content || '', timestamp: now, status: 'sent', metadata: parsed.metadata }
				// Push into nested agent conversation
				for (const a of agents as any[]) {
					const ci = a.conversations?.findIndex((c: any) => c.id === this.conversationId) ?? -1
					if (ci !== -1) {
						a.conversations[ci].messages = Array.isArray(a.conversations[ci].messages) ? a.conversations[ci].messages : []
						a.conversations[ci].messages.push(msg)
						break
					}
				}
				saveMockDB()
				broadcastConversation(this.conversationId, { type: 'new_message', message: msg })
				// Simulate reply
				// Find agentId from conversation
				let agentId = ''
				for (const a of agents as any[]) {
					const c = a.conversations?.find((x: any) => x.id === this.conversationId)
					if (c) { agentId = a.id; break }
				}
				simulateAgentReply(agentId, this.conversationId)
			}
		} catch (e) {
			this.onerror && this.onerror(e)
		}
	}
	close() {
		this.readyState = 3
		unregisterWsClient(this.conversationId, this)
		this.onclose && this.onclose()
	}
}

const wsClientsByConversation: Record<string, Set<MockWebSocket>> = {}
function registerWsClient(conversationId: string, ws: MockWebSocket) {
	if (!conversationId) return
	if (!wsClientsByConversation[conversationId]) wsClientsByConversation[conversationId] = new Set()
	wsClientsByConversation[conversationId].add(ws)
}
function unregisterWsClient(conversationId: string, ws: MockWebSocket) {
	wsClientsByConversation[conversationId]?.delete(ws)
}
function broadcastConversation(conversationId: string, payload: unknown) {
	const json = JSON.stringify(payload)
	wsClientsByConversation[conversationId]?.forEach(client => {
		client.onmessage && client.onmessage({ data: json })
	})
}
function randomReply(): string {
	const len = Math.floor(Math.random() * 40) + 10
	const letters = 'abcdefghijklmnopqrstuvwxyz'
	let s = ''
	for (let i = 0; i < len; i++) s += letters[Math.floor(Math.random() * letters.length)]
	return s
}
function simulateAgentReply(_agentId: string, conversationId: string) {
	const delay = Math.floor(Math.random() * 7000)
	// Always show typing
	broadcastConversation(conversationId, { type: 'typing', typing: true })
	setTimeout(() => {
		const now = new Date().toISOString()
		const assistant: ChatMessage = { id: crypto.randomUUID(), conversation_id: conversationId, role: 'assistant', content: randomReply(), timestamp: now, status: 'sent' }
		// Push into nested agent store
		for (const a of agents as any[]) {
			const ci = a.conversations?.findIndex((c: any) => c.id === conversationId) ?? -1
			if (ci !== -1) {
				a.conversations[ci].messages = Array.isArray(a.conversations[ci].messages) ? a.conversations[ci].messages : []
				a.conversations[ci].updated_at = now
				a.conversations[ci].messages.push(assistant)
				break
			}
		}
		saveMockDB()
		broadcastConversation(conversationId, { type: 'new_message', message: assistant })
		broadcastConversation(conversationId, { type: 'typing', typing: false })
	}, delay)
}

// no-op helper removed

export function enableMockWs() {
	if ((window as any).__mockWsEnabled) return
	;(window as any).WebSocket = MockWebSocket as any
	;(window as any).__mockWsEnabled = true
	console.info('[MockWS] Enabled')
}
