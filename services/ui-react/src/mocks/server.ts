// Very small mock fetch layer that intercepts calls the app makes and returns realistic data
// Disable by not importing this module in main.tsx

import { agents, teams, organizations, agentTemplates, knowledgeDocs, jsonResponse } from './data'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'

function match(url: string, method: HttpMethod) {
	const u = new URL(url, window.location.origin)
	const path = u.pathname
	return { path, url: u }
}

async function handleRequest(input: RequestInfo | URL, init?: RequestInit) {
	const href = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url
	const method = ((init?.method || (typeof input !== 'string' && !(input instanceof URL) ? (input as Request).method : 'GET')) as HttpMethod) || 'GET'
	const { path } = match(href, method)

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

	// Orchestrator-like endpoints
	if (method === 'GET' && path === '/agents') return jsonResponse(agents)
	if (method === 'POST' && path === '/agents') {
		const body = init?.body ? JSON.parse(init.body as string) : {}
		return jsonResponse({ agent_id: 'new-agent-id', ...body }, { status: 201 })
	}
	if (method === 'GET' && path.startsWith('/agents/') && path.endsWith('/tasks')) return jsonResponse([])
	if (method === 'GET' && path.startsWith('/agents/')) {
		const id = path.split('/')[2]
		return jsonResponse(agents.find(a => a.id === id) || agents[0])
	}
	if (method === 'GET' && path === '/agent-templates') return jsonResponse(agentTemplates)

	// Knowledge endpoints
	if (method === 'GET' && path.includes('/knowledge/')) return jsonResponse(knowledgeDocs)
	if (method === 'POST' && path.includes('/knowledge/')) return jsonResponse({ ok: true }, { status: 201 })
	if (method === 'DELETE' && path.includes('/knowledge/')) return jsonResponse({ ok: true })

	// Default fallthrough
	return jsonResponse({ message: 'Mock endpoint not implemented', path, method }, { status: 404 })
}

export function enableMockApi() {
	if ((window as any).__mockApiEnabled) return
	const origFetch = window.fetch.bind(window)
	window.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
		const url = typeof input === 'string' ? input : input instanceof URL ? input.href : (input as Request).url
		// Intercept only app API calls
		if (
			url.startsWith('http://localhost:8000') ||
			url.startsWith('http://localhost:8006') ||
			url.startsWith('/api')
		) {
			// Map real endpoints to mock paths
			const mapped = url
				.replace('http://localhost:8000', '')
				.replace('http://localhost:8006', '')
				.replace(/^\/api/, '')
			return handleRequest(mapped, init)
		}
		return origFetch(input as any, init)
	}) as any
	;(window as any).__mockApiEnabled = true
	console.info('[MockAPI] Enabled')
}


