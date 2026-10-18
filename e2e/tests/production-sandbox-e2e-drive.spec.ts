import { test, expect } from '@playwright/test'
import path from 'path'

const RESULTS_DIR = path.resolve(__dirname, '../test-results')

const FUZEFRONT_URL = process.env.FUZEFRONT_URL ?? 'https://app.fuzefront.com'
const FUZEAGENT_APP_URL = `${FUZEFRONT_URL}/apps/fuzeagent/`
const STANDALONE_AGENT_URL = process.env.FUZEAGENT_URL ?? 'https://fuzeagent.prod.fuzefront.com'

const CF_CLIENT_ID = process.env.CF_ACCESS_CLIENT_ID ?? ''
const CF_CLIENT_SECRET = process.env.CF_ACCESS_CLIENT_SECRET ?? ''
const TEST_SESSION_TOKEN = process.env.TEST_SESSION_TOKEN ?? ''
const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL ?? ''
const TEST_USER_PASSWORD = process.env.TEST_USER_PASSWORD ?? ''
const RUN_PROD_DRIVE = process.env.RUN_PROD_DRIVE === 'true'

const HAS_CF_TOKEN = Boolean(CF_CLIENT_ID && CF_CLIENT_SECRET)

const cfHeaders: Record<string, string> = HAS_CF_TOKEN
  ? { 'CF-Access-Client-Id': CF_CLIENT_ID, 'CF-Access-Client-Secret': CF_CLIENT_SECRET }
  : {}

test.describe('Production Sandbox Proof Drive: Sign-in -> Template -> Launch -> Stream Chat', () => {
  test('Complete proof drive of Python Dev sandbox launch and real-time streaming', async ({ page }) => {
    test.skip(
      !HAS_CF_TOKEN && !TEST_SESSION_TOKEN && !RUN_PROD_DRIVE,
      'Skipped: Set RUN_PROD_DRIVE=true or supply CF_ACCESS tokens / TEST_SESSION_TOKEN'
    )

    // -------------------------------------------------------------------------
    // Step 1: Sign-in / Authenticate (Portal Shell Sentinel & Service Tokens)
    // -------------------------------------------------------------------------
    if (HAS_CF_TOKEN) {
      await page.setExtraHTTPHeaders(cfHeaders)
    }

    // Always inject the hosted session sentinel so FuzeAgent acts as authenticated inside FuzeFront
    await page.addInitScript((token) => {
      window.localStorage.setItem('fuzefront.session.token', token || 'test-session-token');
      (window as unknown as Record<string, unknown>).__FUZEFRONT__ = {
        token: token || 'test-session-token',
        user: {
          userId: 'usr_playwright_test',
          email: 'playwright-e2e@fuzefront.com',
          tenantId: null,
          roles: ['admin', 'developer'],
        },
      }
    }, TEST_SESSION_TOKEN)

    // Navigate to FuzeFront portal or direct federated app
    const targetUrl = HAS_CF_TOKEN ? STANDALONE_AGENT_URL : FUZEAGENT_APP_URL
    console.log(`[Drive] Navigating to: ${targetUrl}`)
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 45_000 })
    await page.waitForTimeout(2000)

    // If an interactive login form is presented, fill test credentials
    const emailInput = page.locator('input[type="email"], input[name="email"]')
    if (await emailInput.isVisible({ timeout: 4000 }).catch(() => false)) {
      if (TEST_USER_EMAIL && TEST_USER_PASSWORD) {
        console.log(`[Drive] Authenticating with test user: ${TEST_USER_EMAIL}`)
        await emailInput.fill(TEST_USER_EMAIL)
        await page.locator('input[type="password"], input[name="password"]').fill(TEST_USER_PASSWORD)
        await page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Log in")').first().click()
        await page.waitForLoadState('domcontentloaded')
      }
    }

    await page.screenshot({ path: path.join(RESULTS_DIR, 'step1-authenticated.png') })

    // -------------------------------------------------------------------------
    // Step 2: Navigate to Agent Chat Workspace Tab
    // -------------------------------------------------------------------------
    const workspaceButton = page
      .locator('button:has-text("Agent Chat")')
      .or(page.locator('button:has-text("Workspace")'))
      .or(page.getByRole('button', { name: /agent chat/i }))
      .or(page.getByRole('button', { name: /workspace/i }))
      .or(page.locator('[data-tab="workspace"]'))

    await expect(workspaceButton.first()).toBeVisible({ timeout: 25_000 })
    console.log('[Drive] Navigating to Agent Chat Workspace tab')
    await workspaceButton.first().click()
    await page.waitForTimeout(2000)

    await page.screenshot({ path: path.join(RESULTS_DIR, 'step2-workspace.png') })

    // -------------------------------------------------------------------------
    // Step 3: Select Python Developer Agent & Setup Env / Launch Pod
    // -------------------------------------------------------------------------
    const pythonAgentHeader = page
      .locator('text=Python Developer')
      .or(page.locator('text=@python-dev'))
      .first()

    await expect(pythonAgentHeader).toBeVisible({ timeout: 25_000 })
    console.log('[Drive] Python Developer agent panel identified')

    // Find the Launch Pod button for the Python developer agent if not already online
    const launchPodBtn = page
      .getByRole('button', { name: /launch pod/i })
      .or(page.locator('button:has-text("Launch Pod")'))
      .first()

    if (await launchPodBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('[Drive] Launching sandbox container pod from Python Dev template...')
      await launchPodBtn.click()

      const bootingIndicator = page
        .locator('text=Booting Pod')
        .or(page.locator('text=Provisioning container sandbox'))
        .first()

      await expect(bootingIndicator).toBeVisible({ timeout: 10_000 })
      console.log('[Drive] Ephemeral pod scheduled in K8s namespace fuzeagent')
    }

    // -------------------------------------------------------------------------
    // Step 4: Verify Container Sandbox Status Online
    // -------------------------------------------------------------------------
    const onlineIndicator = page
      .locator('text=online')
      .or(page.locator('[data-status="online"]'))
      .or(page.locator('.status-online'))
      .or(page.locator('span:has-text("online")'))
      .first()

    await expect(onlineIndicator).toBeVisible({ timeout: 30_000 })
    console.log('[Drive] Pod sandbox runner connected to orchestrator WebSocket relay!')
    await page.screenshot({ path: path.join(RESULTS_DIR, 'step3-pod-online.png') })

    // -------------------------------------------------------------------------
    // -------------------------------------------------------------------------
    // Step 5: Send Natural Language Query in Chat Window
    // -------------------------------------------------------------------------
    const chatInput = page
      .locator('input[placeholder*="Message"], input[placeholder*="Ask"], textarea')
      .first()

    await expect(chatInput).toBeVisible({ timeout: 10_000 })
    const timeQuery = 'What is the time now in LA?'
    console.log(`[Drive] Sending natural language query to agent: ${timeQuery}`)
    await chatInput.fill(timeQuery)

    const sendBtn = page
      .getByRole('button', { name: /send/i })
      .or(page.locator('button:has-text("Send")'))
      .or(page.locator('button[type="submit"]'))
      .first()

    await sendBtn.click()

    // -------------------------------------------------------------------------
    // Step 6: Observe Real-Time Two-Way Streaming in Conversation Window
    // -------------------------------------------------------------------------
    console.log('[Drive] Monitoring live streaming response...')

    // Wait for the user message to appear in the message thread
    const userMessage = page.locator(`text=${timeQuery}`).first()
    await expect(userMessage).toBeVisible({ timeout: 10_000 })

    // Verify response streams real Los Angeles time and NOT fake pytest output
    const timeResponse = page
      .locator('text=Los Angeles')
      .or(page.locator('text=PDT'))
      .or(page.locator('text=PST'))
      .or(page.locator('text=California'))
      .first()

    await expect(timeResponse).toBeVisible({ timeout: 35_000 })
    console.log('[Drive] Received live streaming Los Angeles time in conversation window!')

    // Assert that fake mock pytest string is NOT present
    const fakeMock = page.locator('text=64 passed, 1 skipped in 3.14s')
    await expect(fakeMock).toHaveCount(0)

    await page.screenshot({ path: path.join(RESULTS_DIR, 'step5-time-query-success.png') })
  })
})
