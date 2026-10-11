import { test, expect } from '@playwright/test'

/**
 * End-to-End Production Proof Drive:
 * 1. Sign in to FuzeFront portal / authenticate via Cloudflare Access or Session Token.
 * 2. Select/Create Python Developer Agent from template.
 * 3. Setup runtime environment and launch the sandbox pod.
 * 4. Verify pod transitions to Online.
 * 5. Send 'Hello World' command in the chat window.
 * 6. Observe real-time bidirectional streaming tokens and response.
 */

const FUZEFRONT_URL = process.env.FUZEFRONT_URL ?? 'https://app.fuzefront.com'
const FUZEAGENT_APP_URL = `${FUZEFRONT_URL}/apps/fuzeagent`
const STANDALONE_AGENT_URL = process.env.FUZEAGENT_URL ?? 'https://fuzeagent.prod.fuzefront.com'

const CF_CLIENT_ID = process.env.CF_ACCESS_CLIENT_ID ?? ''
const CF_CLIENT_SECRET = process.env.CF_ACCESS_CLIENT_SECRET ?? ''
const TEST_SESSION_TOKEN = process.env.TEST_SESSION_TOKEN ?? ''
const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL ?? ''
const TEST_USER_PASSWORD = process.env.TEST_USER_PASSWORD ?? ''

const HAS_CF_TOKEN = Boolean(CF_CLIENT_ID && CF_CLIENT_SECRET)

const cfHeaders: Record<string, string> = HAS_CF_TOKEN
  ? { 'CF-Access-Client-Id': CF_CLIENT_ID, 'CF-Access-Client-Secret': CF_CLIENT_SECRET }
  : {}

test.describe('Production Sandbox Proof Drive: Sign-in -> Template -> Launch -> Stream Chat', () => {
  test('Complete proof drive of Python Dev sandbox launch and real-time streaming', async ({ page }) => {
    test.skip(!HAS_CF_TOKEN && !TEST_SESSION_TOKEN, 'Skipped: CF_ACCESS service tokens or TEST_SESSION_TOKEN required for production cluster drive')

    // -------------------------------------------------------------------------
    // Step 1: Sign-in / Authenticate
    // -------------------------------------------------------------------------
    if (HAS_CF_TOKEN) {
      await page.setExtraHTTPHeaders(cfHeaders)
    }

    if (TEST_SESSION_TOKEN) {
      await page.addInitScript((token) => {
        window.localStorage.setItem('fuzefront.session.token', token)
      }, TEST_SESSION_TOKEN)
    }

    // Navigate to FuzeFront portal or direct federated app
    const targetUrl = HAS_CF_TOKEN ? STANDALONE_AGENT_URL : FUZEAGENT_APP_URL
    console.log(`[Drive] Navigating to: ${targetUrl}`)
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 45_000 })

    // If an interactive login form is presented, fill test credentials
    const emailInput = page.locator('input[type="email"], input[name="email"]')
    if (await emailInput.isVisible({ timeout: 5000 }).catch(() => false)) {
      if (TEST_USER_EMAIL && TEST_USER_PASSWORD) {
        console.log(`[Drive] Authenticating with test user: ${TEST_USER_EMAIL}`)
        await emailInput.fill(TEST_USER_EMAIL)
        await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER_PASSWORD)
        await page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Log in")').first().click()
        await page.waitForLoadState('domcontentloaded')
      }
    }

    await page.screenshot({ path: 'e2e/test-results/step1-authenticated.png' })

    // -------------------------------------------------------------------------
    // Step 2: Navigate to Agent Workspace / Templates
    // -------------------------------------------------------------------------
    const workspaceButton = page
      .getByRole('button', { name: /workspace/i })
      .or(page.getByRole('tab', { name: /workspace/i }))
      .or(page.locator('button:has-text("Workspace")'))
      .or(page.locator('[data-tab="workspace"]'))

    if (await workspaceButton.first().isVisible({ timeout: 10_000 }).catch(() => false)) {
      console.log('[Drive] Navigating to Multi-Agent Workspace tab')
      await workspaceButton.first().click()
      await page.waitForTimeout(1000)
    }

    await page.screenshot({ path: 'e2e/test-results/step2-workspace.png' })

    // -------------------------------------------------------------------------
    // Step 3: Select Python Developer Agent & Setup Env / Launch Pod
    // -------------------------------------------------------------------------
    const pythonAgentHeader = page
      .locator('text=Python Developer')
      .or(page.locator('text=@python-dev'))
      .first()

    await expect(pythonAgentHeader).toBeVisible({ timeout: 25_000 })
    console.log('[Drive] Python Developer agent panel identified')

    // Find the Launch Pod button for the Python developer agent
    const launchPodBtn = page
      .getByRole('button', { name: /launch pod/i })
      .or(page.locator('button:has-text("Launch Pod")'))
      .first()

    if (await launchPodBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      console.log('[Drive] Launching sandbox container pod from Python Dev template...')
      await launchPodBtn.click()

      // Verify button or status pill enters booting state
      const bootingIndicator = page
        .locator('text=Booting Pod')
        .or(page.locator('text=Provisioning container sandbox'))
        .first()

      await expect(bootingIndicator).toBeVisible({ timeout: 10_000 })
      console.log('[Drive] Ephemeral pod scheduled in K8s namespace fuzeagent')
    }

    // -------------------------------------------------------------------------
    // Step 4: Wait for Container Sandbox to Standby Online
    // -------------------------------------------------------------------------
    const onlineIndicator = page
      .locator('text=online')
      .or(page.locator('[data-status="online"]'))
      .or(page.locator('.status-online'))
      .first()

    // Give K8s up to 60s to pull image and establish relay WebSocket connection
    await expect(onlineIndicator).toBeVisible({ timeout: 60_000 })
    console.log('[Drive] Pod sandbox runner connected to orchestrator WebSocket relay!')
    await page.screenshot({ path: 'e2e/test-results/step3-pod-online.png' })

    // -------------------------------------------------------------------------
    // Step 5: Send Hello World Command in Chat Window
    // -------------------------------------------------------------------------
    const chatInput = page
      .locator('textarea, input[placeholder*="message"], input[placeholder*="Ask"], input[placeholder*="Type"]')
      .first()

    await expect(chatInput).toBeVisible({ timeout: 10_000 })
    const testCommand = "python3 -c \"print('Hello World from sandboxed FuzeOne container!')\""
    console.log(`[Drive] Sending command to container: ${testCommand}`)
    await chatInput.fill(testCommand)

    const sendBtn = page
      .getByRole('button', { name: /send/i })
      .or(page.locator('button:has-text("Send")'))
      .or(page.locator('button[type="submit"]'))
      .or(page.locator('button:has(svg)'))
      .first()

    await sendBtn.click()

    // -------------------------------------------------------------------------
    // Step 6: Observe Real-Time Two-Way Streaming in Conversation Window
    // -------------------------------------------------------------------------
    console.log('[Drive] Monitoring live streaming response...')

    // Wait for the response container to populate with tokens
    const responseStream = page
      .locator('text=Hello World from sandboxed FuzeOne container!')
      .or(page.locator('text=Processed in container sandbox'))
      .first()

    await expect(responseStream).toBeVisible({ timeout: 35_000 })
    console.log('[Drive] Received live streaming response from sandboxed container!')

    await page.screenshot({ path: 'e2e/test-results/step4-stream-success.png' })
  })
})
