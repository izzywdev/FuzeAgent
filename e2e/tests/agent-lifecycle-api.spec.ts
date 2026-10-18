import { test, expect } from '@playwright/test'

/**
 * End-to-End & Post-Production Verification Suite for Agent Lifecycle:
 * A. List available agent templates using REST API (GET /api/agent-templates)
 * B. Create an agent template (POST /api/agent-templates)
 * C. Create an agent from a template (POST /api/agents)
 * D. List agents (GET /api/agents)
 * E. Start an agent session including wiring in/out streaming for chat output
 *    (POST /api/agents/{agent_id}/sessions & /api/sessions/{session_id}/messages)
 * F. Terminate a session (DELETE /api/sessions/{session_id})
 */

const FUZEAGENT_BASE =
  process.env.FUZEAGENT_URL ?? 'https://app.fuzefront.com/apps/fuzeagent'
const CF_CLIENT_ID = process.env.CF_ACCESS_CLIENT_ID ?? ''
const CF_CLIENT_SECRET = process.env.CF_ACCESS_CLIENT_SECRET ?? ''
const HAS_CF_TOKEN = Boolean(CF_CLIENT_ID && CF_CLIENT_SECRET)

const cfHeaders: Record<string, string> = HAS_CF_TOKEN
  ? {
      'CF-Access-Client-Id': CF_CLIENT_ID,
      'CF-Access-Client-Secret': CF_CLIENT_SECRET,
    }
  : {}

test.describe('Agent Lifecycle REST API & Streaming Session Management (A-F)', () => {
  let createdTemplateId: string
  let createdAgentId: string
  let createdSessionId: string

  test('A. List available agent templates via REST API', async ({ request }) => {
    const res = await request.get(`${FUZEAGENT_BASE}/api/agent-templates`, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    })

    expect([200, 302], 'Expected 200 OK or 302 redirect from templates API').toContain(
      res.status()
    )

    if (res.status() === 200) {
      const templates = await res.json()
      expect(Array.isArray(templates), 'Templates response should be an array').toBe(true)
      expect(templates.length, 'Should have pre-configured templates').toBeGreaterThanOrEqual(1)

      const ids = templates.map((t: any) => t.id || t.template_id)
      console.log(`[E2E] Found ${templates.length} templates:`, ids)
      expect(
        ids.some((id: string) => id.includes('python') || id.includes('react') || id.includes('dev')),
        'Expected built-in developer templates to be present'
      ).toBe(true)
    }
  })

  test('B. Create a custom agent template via REST API', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN && !process.env.RUN_PROD_DRIVE, 'Skip mutating post-prod when unauthenticated')

    const uniqueSuffix = Date.now().toString(36)
    const templatePayload = {
      id: `e2e_qa_auditor_${uniqueSuffix}`,
      name: `E2E QA Auditor ${uniqueSuffix}`,
      category: 'quality_assurance',
      role: 'Lead QA Automation Engineer',
      description: 'Autonomous E2E testing and quality gate agent',
      system_prompt: 'You are an autonomous QA engineer executing Playwright and pytest suites.',
      default_goal: 'Execute test suites and verify 100% pass rates',
      tools: ['playwright_runner', 'pytest_runner', 'code_review'],
      skills: ['e2e_testing', 'api_verification', 'regression'],
      default_model: 'claude-sonnet-4-20250514',
      default_temperature: 0.3,
    }

    const res = await request.post(`${FUZEAGENT_BASE}/api/agent-templates`, {
      headers: { ...cfHeaders, 'Content-Type': 'application/json' },
      data: templatePayload,
    })

    expect([201, 200]).toContain(res.status())
    const data = await res.json()
    expect(data.id).toBe(templatePayload.id)
    expect(data.name).toBe(templatePayload.name)
    createdTemplateId = data.id
    console.log(`[E2E] Created custom agent template: ${createdTemplateId}`)

    // Verify template is immediately retrievable via GET /api/agent-templates/{id}
    const getRes = await request.get(`${FUZEAGENT_BASE}/api/agent-templates/${createdTemplateId}`, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    })
    expect(getRes.status()).toBe(200)
    expect((await getRes.json()).name).toBe(templatePayload.name)
  })

  test('C. Create an agent instance from a template', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN && !process.env.RUN_PROD_DRIVE, 'Skip mutating post-prod when unauthenticated')

    const targetTemplate = createdTemplateId || 'python_developer'
    const agentPayload = {
      template_id: targetTemplate,
      name: `E2E Production Bot ${Date.now().toString(36)}`,
      role: 'Autonomous Cloud Engineer',
      overrides: {
        goal: 'Execute automated deployment validations',
        temperature: 0.5,
      },
    }

    const res = await request.post(`${FUZEAGENT_BASE}/api/agents`, {
      headers: { ...cfHeaders, 'Content-Type': 'application/json' },
      data: agentPayload,
    })

    expect([201, 200]).toContain(res.status())
    const agent = await res.json()
    expect(agent.id || agent.agent_id).toBeDefined()
    expect(agent.name).toBe(agentPayload.name)
    expect(agent.status).toBe('active')
    createdAgentId = agent.id || agent.agent_id
    console.log(`[E2E] Instantiated agent: ${createdAgentId} from template ${targetTemplate}`)
  })

  test('D. List agents via REST API', async ({ request }) => {
    const res = await request.get(`${FUZEAGENT_BASE}/api/agents`, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    })

    expect([200, 302]).toContain(res.status())
    if (res.status() === 200) {
      const agents = await res.json()
      expect(Array.isArray(agents)).toBe(true)
      console.log(`[E2E] Total agents listed: ${agents.length}`)

      if (createdAgentId) {
        const found = agents.some((a: any) => a.id === createdAgentId || a.agent_id === createdAgentId)
        expect(found, `Newly created agent ${createdAgentId} should appear in agents list`).toBe(true)
      }
    }
  })

  test('E. Start an agent session with bidirectional streaming wiring', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN && !process.env.RUN_PROD_DRIVE, 'Skip mutating post-prod when unauthenticated')

    const agentId = createdAgentId || 'python-dev'
    const sessionRes = await request.post(`${FUZEAGENT_BASE}/api/agents/${agentId}/sessions`, {
      headers: { ...cfHeaders, 'Content-Type': 'application/json' },
      data: {
        session_name: `E2E Verification Session ${Date.now()}`,
      },
    })

    expect([201, 200]).toContain(sessionRes.status())
    const session = await sessionRes.json()
    expect(session.session_id).toBeDefined()
    expect(session.status).toBe('active')
    expect(session.streaming).toBeDefined()
    expect(session.streaming.websocket_url).toContain(session.session_id)
    expect(session.streaming.stream_url).toContain(session.session_id)
    createdSessionId = session.session_id
    console.log(`[E2E] Session started with streaming wiring: ${createdSessionId}`)

    // Dispatch chat message into session
    const chatRes = await request.post(
      `${FUZEAGENT_BASE}/api/sessions/${createdSessionId}/messages`,
      {
        headers: { ...cfHeaders, 'Content-Type': 'application/json' },
        data: {
          message: 'What is the time now in LA?',
        },
      }
    )
    expect(chatRes.status()).toBe(200)
    const chatBody = await chatRes.json()
    expect(chatBody.status).toBe('processing')
    console.log(`[E2E] Inbound message dispatched to session stream: status=${chatBody.status}`)
  })

  test('F. Terminate an agent session', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN && !process.env.RUN_PROD_DRIVE, 'Skip mutating post-prod when unauthenticated')
    test.skip(!createdSessionId, 'No session available to terminate')

    const termRes = await request.delete(`${FUZEAGENT_BASE}/api/sessions/${createdSessionId}`, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    })

    expect(termRes.status()).toBe(200)
    const termBody = await termRes.json()
    expect(termBody.session_id).toBe(createdSessionId)
    expect(termBody.status).toBe('terminated')
    console.log(`[E2E] Successfully terminated session: ${createdSessionId}`)

    // Verify session state reflects terminated
    const checkRes = await request.get(`${FUZEAGENT_BASE}/api/sessions/${createdSessionId}`, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    })
    expect(checkRes.status()).toBe(200)
    expect((await checkRes.json()).status).toBe('terminated')
  })
})
