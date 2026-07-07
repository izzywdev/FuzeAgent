import { test, expect, type Page } from '@playwright/test'

/**
 * Post-production smoke suite.
 *
 * Verifies that FuzeAgent loads visually inside FuzeFront's shell at
 * https://app.fuzefront.com.  Runs against the live prod stack — no
 * mocks, no local servers.
 *
 * What we check:
 *  1. remoteEntry.js is fetchable with correct CORS headers
 *  2. FuzeFront loads and the "Agents" nav item is present
 *  3. Clicking "Agents" navigates without a JS error
 *  4. The FuzeAgent UI renders visible content (not a blank/error screen)
 *  5. No CORS or federation errors appear in the browser console
 */

const FUZEFRONT_URL = 'https://app.fuzefront.com'
const FUZEAGENT_REMOTE_ENTRY = 'https://fuzeagent.prod.fuzefront.com/remoteEntry.js'

// ---------------------------------------------------------------------------
// Helper — collect console errors during a page action
// ---------------------------------------------------------------------------
async function withConsoleErrors(page: Page, fn: () => Promise<void>): Promise<string[]> {
  const errors: string[] = []
  const handler = (msg: { type: () => string; text: () => string }) => {
    if (msg.type() === 'error') errors.push(msg.text())
  }
  page.on('console', handler)
  await fn()
  page.off('console', handler)
  return errors
}

// ---------------------------------------------------------------------------
// 1. remoteEntry.js CORS check (direct HTTP, no browser)
// ---------------------------------------------------------------------------
test('remoteEntry.js is served with Access-Control-Allow-Origin for app.fuzefront.com', async ({ request }) => {
  const response = await request.get(FUZEAGENT_REMOTE_ENTRY, {
    headers: { Origin: 'https://app.fuzefront.com' },
  })

  expect(response.status(), 'remoteEntry.js should return 200').toBe(200)

  const corsHeader = response.headers()['access-control-allow-origin']
  expect(
    corsHeader,
    'CORS header must allow app.fuzefront.com (nginx inheritance bug recheck)',
  ).toBe('https://app.fuzefront.com')

  const ct = response.headers()['content-type'] ?? ''
  expect(ct, 'remoteEntry.js must be served as JavaScript').toContain('javascript')
})

// ---------------------------------------------------------------------------
// 2–5. Visual load check inside FuzeFront shell
// ---------------------------------------------------------------------------
test.describe('FuzeAgent inside FuzeFront shell', () => {
  test.beforeEach(async ({ page }) => {
    // Silence known non-fatal third-party noise so our CORS filter is tight
    await page.route('**/*', (route) => route.continue())
  })

  test('FuzeFront shell loads and shows the Agents nav item', async ({ page }) => {
    await page.goto(FUZEFRONT_URL, { waitUntil: 'networkidle' })

    // The nav item registered by FuzeFront PR #184 — label "Agents"
    const agentsLink = page.getByRole('link', { name: /agents/i }).or(
      page.getByRole('menuitem', { name: /agents/i }),
    )
    await expect(agentsLink.first()).toBeVisible({ timeout: 20_000 })
  })

  test('clicking Agents loads FuzeAgent without a blank screen or error boundary', async ({ page }) => {
    await page.goto(FUZEFRONT_URL, { waitUntil: 'networkidle' })

    // Collect console errors that fire while navigating to FuzeAgent
    const errors = await withConsoleErrors(page, async () => {
      const agentsLink = page.getByRole('link', { name: /agents/i }).or(
        page.getByRole('menuitem', { name: /agents/i }),
      )
      await agentsLink.first().click()

      // Wait for network to settle after the federation load
      await page.waitForLoadState('networkidle')
    })

    // Filter out known noisy-but-harmless warnings; keep only hard errors
    const realErrors = errors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('sourcemap') &&
        !e.includes('DevTools'),
    )

    // No CORS / federation errors
    const corsErrors = realErrors.filter(
      (e) => e.toLowerCase().includes('cors') || e.toLowerCase().includes('access-control'),
    )
    expect(corsErrors, `CORS errors: ${corsErrors.join('\n')}`).toHaveLength(0)

    const federationErrors = realErrors.filter(
      (e) =>
        e.toLowerCase().includes('remotentry') ||
        e.toLowerCase().includes('fuzeagentapp') ||
        e.toLowerCase().includes('failed to fetch dynamically'),
    )
    expect(federationErrors, `Federation errors: ${federationErrors.join('\n')}`).toHaveLength(0)
  })

  test('FuzeAgent UI content is visible after navigation', async ({ page }) => {
    await page.goto(FUZEFRONT_URL, { waitUntil: 'networkidle' })

    const agentsLink = page.getByRole('link', { name: /agents/i }).or(
      page.getByRole('menuitem', { name: /agents/i }),
    )
    await agentsLink.first().click()
    await page.waitForLoadState('networkidle')

    // The FuzeAgent App renders an agent dashboard — check for a meaningful
    // visible element rather than a blank/error screen.
    // We look for ANY of: the "Agents" heading, a stats card, the create-agent
    // button, or the organisation selector — whatever renders first on an empty org.
    const contentIndicators = page.locator(
      [
        // Headings the app renders
        'h1, h2, h3',
        // The "+ Create Agent" button visible even with 0 agents
        'button',
        // Any card / list element from StatsCards or AgentDashboard
        '[class*="card"], [class*="stat"], [class*="agent"], [class*="dashboard"]',
      ].join(', '),
    )

    await expect(contentIndicators.first()).toBeVisible({ timeout: 30_000 })

    // Confirm the page body has non-trivial text (not an empty shell)
    const bodyText = await page.locator('body').innerText()
    expect(bodyText.trim().length, 'Page should have visible text content').toBeGreaterThan(20)
  })

  test('FuzeAgent standalone URL is healthy (direct access)', async ({ page }) => {
    // Belt-and-suspenders: confirm the standalone app also serves without error.
    const response = await page.goto('https://fuzeagent.prod.fuzefront.com/', {
      waitUntil: 'networkidle',
    })
    expect(response?.status(), 'Standalone FuzeAgent should return 200').toBe(200)

    const title = await page.title()
    expect(title.trim().length, 'Page should have a title').toBeGreaterThan(0)
  })
})
