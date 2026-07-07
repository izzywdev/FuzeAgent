import { test, expect, type Page } from '@playwright/test'

/**
 * Post-production smoke suite — FuzeAgent loading inside FuzeFront.
 *
 * Architecture note: fuzeagent.prod.fuzefront.com sits behind Cloudflare
 * Access (team: fuzefront.cloudflareaccess.com). Authenticated users
 * (those already logged into FuzeFront) carry a CF_Authorization cookie
 * that is scoped to the fuzefront team domain and grants access to ALL
 * apps in the same org, including fuzeagent.prod.fuzefront.com — so no
 * separate login is needed for real users.
 *
 * For machine/CI access we use a Cloudflare Access Service Token:
 *   CF_ACCESS_CLIENT_ID     — set as a GitHub Actions secret
 *   CF_ACCESS_CLIENT_SECRET — set as a GitHub Actions secret
 *
 * Without those secrets the auth-gated tests are skipped (not failed).
 */

const FUZEFRONT_URL = 'https://app.fuzefront.com'
const FUZEAGENT_REMOTE_ENTRY = 'https://fuzeagent.prod.fuzefront.com/remoteEntry.js'
const FUZEAGENT_BASE = 'https://fuzeagent.prod.fuzefront.com'

const CF_CLIENT_ID = process.env.CF_ACCESS_CLIENT_ID ?? ''
const CF_CLIENT_SECRET = process.env.CF_ACCESS_CLIENT_SECRET ?? ''
const HAS_CF_TOKEN = Boolean(CF_CLIENT_ID && CF_CLIENT_SECRET)

/** Extra headers to attach to every request when running with a service token. */
const cfHeaders: Record<string, string> = HAS_CF_TOKEN
  ? { 'CF-Access-Client-Id': CF_CLIENT_ID, 'CF-Access-Client-Secret': CF_CLIENT_SECRET }
  : {}

// ---------------------------------------------------------------------------
// Helper
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

/** Navigate using extraHTTPHeaders so every request (including CF auth) is covered. */
async function gotoAuthenticated(page: Page, url: string) {
  if (HAS_CF_TOKEN) {
    await page.setExtraHTTPHeaders(cfHeaders)
  }
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60_000 })
}

// ---------------------------------------------------------------------------
// 1. CORS check on remoteEntry.js
//    CF Access sits in front, so an unauthenticated request gets a 302.
//    We verify two things:
//      a) with service token → 200 + correct CORS header
//      b) without token     → the 302 itself also carries CORS headers
//         (so the browser's preflight passes before CF redirects)
// ---------------------------------------------------------------------------
test.describe('remoteEntry.js CORS headers', () => {
  test('302 redirect from Cloudflare Access carries CORS header', async ({ request }) => {
    // Playwright's request follows redirects by default; we need the raw 302.
    // Use fetch with redirect:manual equivalent — check the first response.
    const response = await request.fetch(FUZEAGENT_REMOTE_ENTRY, {
      headers: { Origin: 'https://app.fuzefront.com' },
      maxRedirects: 0,
    })

    // CF Access returns 302 for unauthenticated requests.
    // The CORS header on the 302 lets the browser proceed with the redirect.
    const status = response.status()
    expect([200, 302], `Expected 200 (with token) or 302 (CF redirect), got ${status}`).toContain(status)

    const corsHeader = response.headers()['access-control-allow-origin']
    expect(
      corsHeader,
      'Even the CF Access redirect must carry Access-Control-Allow-Origin so the browser can follow it',
    ).toBe('https://app.fuzefront.com')
  })

  test('remoteEntry.js returns 200 + CORS header with service token', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET not set')

    const response = await request.get(FUZEAGENT_REMOTE_ENTRY, {
      headers: {
        Origin: 'https://app.fuzefront.com',
        ...cfHeaders,
      },
    })

    expect(response.status(), 'remoteEntry.js should return 200 with valid service token').toBe(200)

    const corsHeader = response.headers()['access-control-allow-origin']
    expect(corsHeader, 'CORS header must allow app.fuzefront.com').toBe('https://app.fuzefront.com')

    const ct = response.headers()['content-type'] ?? ''
    expect(ct, 'remoteEntry.js must be served as JavaScript').toContain('javascript')
  })
})

// ---------------------------------------------------------------------------
// 2–5. Visual / functional checks inside FuzeFront
//      All require authentication; skipped when no service token is set.
// ---------------------------------------------------------------------------
test.describe('FuzeAgent inside FuzeFront shell', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET not set — set these secrets to run auth-gated tests')
    if (HAS_CF_TOKEN) {
      await page.setExtraHTTPHeaders(cfHeaders)
    }
  })

  test('FuzeFront shell loads and shows the Agents nav item', async ({ page }) => {
    await gotoAuthenticated(page, FUZEFRONT_URL)
    await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {
      // networkidle can be flaky on SPA shells; domcontentloaded is enough
    })

    const agentsLink = page
      .getByRole('link', { name: /agents/i })
      .or(page.getByRole('menuitem', { name: /agents/i }))
      .or(page.locator('[data-testid*="agent"], [href*="agent"]'))

    await expect(agentsLink.first()).toBeVisible({ timeout: 20_000 })
  })

  test('clicking Agents loads FuzeAgent without CORS or federation errors', async ({ page }) => {
    await gotoAuthenticated(page, FUZEFRONT_URL)
    await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {})

    const errors = await withConsoleErrors(page, async () => {
      const agentsLink = page
        .getByRole('link', { name: /agents/i })
        .or(page.getByRole('menuitem', { name: /agents/i }))
        .or(page.locator('[data-testid*="agent"], [href*="agent"]'))

      await agentsLink.first().click({ timeout: 20_000 })
      await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {})
    })

    const corsErrors = errors.filter(
      (e) => e.toLowerCase().includes('cors') || e.toLowerCase().includes('access-control'),
    )
    expect(corsErrors, `CORS errors in console:\n${corsErrors.join('\n')}`).toHaveLength(0)

    const federationErrors = errors.filter(
      (e) =>
        e.toLowerCase().includes('remoteentry') ||
        e.toLowerCase().includes('fuzeagentapp') ||
        e.toLowerCase().includes('failed to fetch dynamically'),
    )
    expect(federationErrors, `Federation errors in console:\n${federationErrors.join('\n')}`).toHaveLength(0)
  })

  test('FuzeAgent UI renders visible content after navigation', async ({ page }) => {
    await gotoAuthenticated(page, FUZEFRONT_URL)
    await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {})

    const agentsLink = page
      .getByRole('link', { name: /agents/i })
      .or(page.getByRole('menuitem', { name: /agents/i }))
      .or(page.locator('[data-testid*="agent"], [href*="agent"]'))

    await agentsLink.first().click({ timeout: 20_000 })
    await page.waitForLoadState('networkidle', { timeout: 30_000 }).catch(() => {})

    // Any meaningful rendered element — heading, button, card
    const contentIndicators = page.locator('h1, h2, h3, button, [class*="card"], [class*="agent"], [class*="dashboard"]')
    await expect(contentIndicators.first()).toBeVisible({ timeout: 30_000 })

    const bodyText = await page.locator('body').innerText()
    expect(bodyText.trim().length, 'Page must have visible text content').toBeGreaterThan(20)
  })
})

// ---------------------------------------------------------------------------
// 6. Standalone FuzeAgent health (auth-gated)
// ---------------------------------------------------------------------------
test('FuzeAgent standalone URL is healthy with service token', async ({ page }) => {
  test.skip(!HAS_CF_TOKEN, 'Skipped: CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET not set')

  await gotoAuthenticated(page, FUZEAGENT_BASE)
  const response = await page.goto(FUZEAGENT_BASE, { waitUntil: 'domcontentloaded' })
  expect(response?.status(), 'Standalone FuzeAgent should return 200').toBe(200)

  const title = await page.title()
  expect(title.trim().length, 'Page should have a title').toBeGreaterThan(0)
})

// ---------------------------------------------------------------------------
// 7. Unauthenticated health — what anyone can see (always runs, no token needed)
// ---------------------------------------------------------------------------
test('fuzeagent.prod.fuzefront.com responds (CF Access gate is live)', async ({ request }) => {
  const response = await request.fetch(FUZEAGENT_BASE, { maxRedirects: 0 })
  // 200 = public / 302 = CF Access gate protecting the app
  expect([200, 302]).toContain(response.status())
})
