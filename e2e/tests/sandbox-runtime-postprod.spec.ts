import { test, expect } from '@playwright/test'

/**
 * Post-production smoke test suite for FuzeAgent Sandboxed Containers
 * and Full-Duplex Bidirectional Chat Streaming.
 *
 * Verifies:
 * 1. Orchestrator API health and template registry endpoints
 * 2. Active sandbox listing and resource limits
 * 3. Multi-agent WebSocket stream (/api/ws/multi-agent) handshake & ping/pong
 * 4. Runtime container on-demand spawn action dispatch
 * 5. MultiAgentChatWorkspace UI rendering & "Launch Pod" action controls
 */

const FUZEAGENT_BASE = process.env.FUZEAGENT_URL ?? 'https://fuzeagent.prod.fuzefront.com'
const FUZEFRONT_URL = process.env.FUZEFRONT_URL ?? 'https://app.fuzefront.com'

const CF_CLIENT_ID = process.env.CF_ACCESS_CLIENT_ID ?? ''
const CF_CLIENT_SECRET = process.env.CF_ACCESS_CLIENT_SECRET ?? ''
const HAS_CF_TOKEN = Boolean(CF_CLIENT_ID && CF_CLIENT_SECRET)

const cfHeaders: Record<string, string> = HAS_CF_TOKEN
  ? { 'CF-Access-Client-Id': CF_CLIENT_ID, 'CF-Access-Client-Secret': CF_CLIENT_SECRET }
  : {}

test.describe('Sandbox Runtime & Orchestrator API (Post-Production)', () => {
  test('Orchestrator health check responds with 200 or CF gate', async ({ request }) => {
    const healthUrl = `${FUZEAGENT_BASE}/health`
    const response = await request.fetch(healthUrl, {
      headers: { ...cfHeaders },
      maxRedirects: 0,
    })

    // 200 if authenticated or public, 302 if behind Cloudflare Access
    expect([200, 302], `Expected 200 or 302 redirect from ${healthUrl}`).toContain(response.status())
  })

  test('Template registry returns pre-configured sandbox runners with resource limits', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET not set')

    const tmplUrl = `${FUZEAGENT_BASE}/api/templates`
    const response = await request.get(tmplUrl, {
      headers: {
        ...cfHeaders,
        Accept: 'application/json',
      },
    })

    expect(response.status(), 'Templates API should respond with 200').toBe(200)
    const templates = await response.json()
    expect(Array.isArray(templates) || typeof templates === 'object').toBeTruthy()

    // Verify python-dev and react-dev templates exist
    const tmplList = Array.isArray(templates) ? templates : Object.values(templates)
    const pythonTmpl = tmplList.find((t: any) => t.id?.includes('python') || t.name?.includes('Python'))
    expect(pythonTmpl, 'python-dev template should be registered in the registry').toBeDefined()

    if (pythonTmpl && pythonTmpl.sandboxing) {
      expect(pythonTmpl.sandboxing.defaultTimeoutSeconds).toBeGreaterThan(0)
      expect(pythonTmpl.sandboxing.cpuLimit).toBeDefined()
      expect(pythonTmpl.sandboxing.memoryLimit).toBeDefined()
    }
  })

  test('Active sandboxes endpoint returns running container roster', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET not set')

    const sbxUrl = `${FUZEAGENT_BASE}/api/sandboxes`
    const response = await request.get(sbxUrl, {
      headers: {
        ...cfHeaders,
        Accept: 'application/json',
      },
    })

    expect(response.status(), 'Sandboxes API should respond with 200').toBe(200)
    const sandboxes = await response.json()
    expect(Array.isArray(sandboxes), 'Sandboxes response should be an array').toBe(true)
  })
})

test.describe('Multi-Agent WebSocket Streaming Bus (Post-Production)', () => {
  test('WebSocket endpoint /api/ws/multi-agent establishes connection and responds to ping', async ({ page }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET not set')

    // Navigate to standalone or embedded portal to run browser WebSocket with session
    if (HAS_CF_TOKEN) {
      await page.setExtraHTTPHeaders(cfHeaders)
    }

    await page.goto(FUZEAGENT_BASE, { waitUntil: 'domcontentloaded', timeout: 30_000 })

    // Execute in-browser WebSocket client against the live backend
    const wsResult = await page.evaluate(async (baseUrl) => {
      return new Promise<{ connected: boolean; activeAgents: string[]; pongReceived: boolean; spawnAcknowledged: boolean }>((resolve) => {
        const proto = baseUrl.startsWith('https') ? 'wss:' : 'ws:'
        const host = new URL(baseUrl).host
        const wsUrl = `${proto}//${host}/api/ws/multi-agent`

        let connected = false
        let pongReceived = false
        let spawnAcknowledged = false
        let activeAgents: string[] = []

        try {
          const ws = new WebSocket(wsUrl)
          const timeout = setTimeout(() => {
            ws.close()
            resolve({ connected, activeAgents, pongReceived, spawnAcknowledged })
          }, 8000)

          ws.onopen = () => {
            connected = true
            // 1. Send Ping
            ws.send(JSON.stringify({ action: 'ping' }))
            // 2. Send Test Spawn for python-dev
            ws.send(JSON.stringify({ action: 'spawn', agentId: 'python-dev' }))
          }

          ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data)
              if (data.type === 'connection_established') {
                activeAgents = data.activeAgents || []
              }
              if (data.type === 'pong') {
                pongReceived = true
              }
              if (data.type === 'agent_status' && data.status === 'booting' && data.agentId === 'python-dev') {
                spawnAcknowledged = true
              }
              if (connected && pongReceived && spawnAcknowledged) {
                clearTimeout(timeout)
                ws.close()
                resolve({ connected, activeAgents, pongReceived, spawnAcknowledged })
              }
            } catch {
              // ignore parse errors
            }
          }

          ws.onerror = () => {
            clearTimeout(timeout)
            resolve({ connected: false, activeAgents, pongReceived, spawnAcknowledged })
          }
        } catch {
          resolve({ connected: false, activeAgents, pongReceived, spawnAcknowledged })
        }
      })
    }, FUZEAGENT_BASE)

    expect(wsResult.connected, 'WebSocket bus should successfully establish connection').toBe(true)
    expect(wsResult.pongReceived, 'WebSocket bus should acknowledge ping with pong').toBe(true)
    expect(wsResult.spawnAcknowledged, 'WebSocket bus should acknowledge spawn action').toBe(true)
  })
})

test.describe('FuzeFront UI Workspace & Launch Pod Controls (Post-Production)', () => {
  test('FuzeAgent renders Multi-Agent Chat Workspace with Launch Pod controls', async ({ page }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET not set')

    if (HAS_CF_TOKEN) {
      await page.setExtraHTTPHeaders(cfHeaders)
    }

    // Go to standalone FuzeAgent or embedded route
    await page.goto(FUZEAGENT_BASE, { waitUntil: 'domcontentloaded', timeout: 45_000 })

    // Find and navigate to workspace tab if present
    const workspaceTab = page
      .getByRole('button', { name: /workspace/i })
      .or(page.getByRole('tab', { name: /workspace/i }))
      .or(page.locator('button:has-text("Workspace")'))

    if (await workspaceTab.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      await workspaceTab.first().click()
      await page.waitForTimeout(1000)
    }

    // Check that Agent Chat panels or buttons are visible
    const agentMention = page.locator('text=@python-dev').or(page.locator('text=Python Developer')).or(page.locator('text=Launch Pod'))
    await expect(agentMention.first()).toBeVisible({ timeout: 20_000 })

    // Verify Launch Pod button is present in the workspace
    const launchButton = page.getByRole('button', { name: /launch pod/i }).or(page.locator('button:has-text("Launch Pod")'))
    const count = await launchButton.count()
    expect(count, 'At least one Launch Pod control should be rendered for runtime containers').toBeGreaterThanOrEqual(1)
  })
})
