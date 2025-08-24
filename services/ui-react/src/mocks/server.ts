// Very small mock fetch layer that intercepts calls the app makes and returns realistic data
// Disable by not importing this module in main.tsx

import { agents, teams, organizations, agentTemplates, knowledgeDocs, jsonResponse, saveMockDB, loadMockDB } from './data'

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
	if (method === 'GET' && path.startsWith('/teams/')) {
		const id = path.split('/')[2]
		const team = teams.find(t => t.id === id)
		if (team) {
			return jsonResponse(team)
		}
		return jsonResponse({ message: 'Team not found' }, { status: 404 })
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
			joinedDate: now
		}
		agents.push(newAgent)
		saveMockDB()
		return jsonResponse({ agent_id: id, status: 'created', agent: newAgent }, { status: 201 })
	}
	if (method === 'GET' && path.startsWith('/agents/') && path.endsWith('/tasks')) return jsonResponse([])
	if (method === 'GET' && path.startsWith('/agents/')) {
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

	// Default fallthrough
	return jsonResponse({ message: 'Mock endpoint not implemented', path, method }, { status: 404 })
}

export function enableMockApi() {
	if ((window as any).__mockApiEnabled) return
	const origFetch = window.fetch.bind(window)
	const apiPrefixes = ['/agents', '/teams', '/organizations', '/agent-templates', '/knowledge', '/rag']
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


