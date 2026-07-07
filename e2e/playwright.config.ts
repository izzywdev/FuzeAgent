import { defineConfig, devices } from '@playwright/test'

/**
 * Post-production smoke suite — runs against the live prod stack.
 * All URLs point at real Cloudflare-fronted services, no local server.
 *
 * Run:  cd e2e && npm test
 * CI:   npx playwright test --reporter=github
 */
export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  retries: 2,
  reporter: [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: 'https://app.fuzefront.com',
    // Capture a screenshot on every failure for debugging
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    headless: true,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
