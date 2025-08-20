// Mock data that approximates the real API schema used by the UI

export const organizations = [
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

export const teams = [
	{
		id: '4d0b5f8a-08b0-4d2a-9c6e-18f0f0d0a111',
		organization_id: organizations[0].id,
		name: 'Engineering',
		description: 'Core engineering team',
		team_type: 'technical',
		settings: {},
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
	},
]

export const agents = [
	{
		id: 'a1111111-2222-3333-4444-555555555555',
		team_id: teams[0].id,
		name: 'React Developer 1',
		role: 'Frontend Developer',
		type: 'developer',
		status: 'active',
		config: {},
		template_id: 'react-dev',
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		tasks: { completed: 12, running: 1, pending: 2 },
		lastActivity: new Date().toISOString(),
	},
	{
		id: 'b1111111-2222-3333-4444-555555555555',
		team_id: teams[0].id,
		name: 'Backend Dev 1',
		role: 'Backend Developer',
		type: 'developer',
		status: 'idle',
		config: {},
		template_id: 'backend-dev',
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString(),
		tasks: { completed: 8, running: 0, pending: 1 },
		lastActivity: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
	},
]

export const agentTemplates = [
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

export const knowledgeDocs = [
	{
		id: 'doc-1',
		title: 'Engineering Handbook',
		source: 'upload',
		created_at: new Date().toISOString(),
	},
]

export function jsonResponse(body: unknown, init: ResponseInit = { status: 200 }) {
	return new Response(JSON.stringify(body), {
		...init,
		headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
	})
}


