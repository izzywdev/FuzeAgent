import { test, expect } from '@playwright/test';

/**
 * Post-production test suite for:
 * 1. Multi-tier Brain architecture and CRUD REST endpoints (/brains, /agents/:id/brains)
 * 2. Cross-functional domain memory (frontend, devops, backend)
 * 3. Dual MCP exposure of brain tools & resources
 * 4. Standalone Chat Workspace (/chat/window) with extensible cards & thought disclosure
 */

const FUZEAGENT_BASE = process.env.FUZEAGENT_URL ?? 'https://fuzeagent.prod.fuzefront.com';
const FUZEFRONT_URL = process.env.FUZEFRONT_URL ?? 'https://app.fuzefront.com';

const CF_CLIENT_ID = process.env.CF_ACCESS_CLIENT_ID ?? '';
const CF_CLIENT_SECRET = process.env.CF_ACCESS_CLIENT_SECRET ?? '';
const HAS_CF_TOKEN = Boolean(CF_CLIENT_ID && CF_CLIENT_SECRET);

const cfHeaders: Record<string, string> = HAS_CF_TOKEN
  ? { 'CF-Access-Client-Id': CF_CLIENT_ID, 'CF-Access-Client-Secret': CF_CLIENT_SECRET }
  : {};

test.describe('Brain Multi-Tier Hierarchy & CRUD REST API (Post-Production)', () => {
  test('GET /brains responds with 200/302 and lists company brains', async ({ request }) => {
    const url = `${FUZEAGENT_BASE}/brains`;
    const response = await request.fetch(url, {
      headers: { ...cfHeaders, Accept: 'application/json' },
      maxRedirects: 0,
    });

    expect([200, 302], `Expected 200 or 302 from ${url}`).toContain(response.status());

    if (response.status() === 200) {
      const brains = await response.json();
      expect(Array.isArray(brains), 'Brains response must be an array').toBe(true);
      expect(brains.length, 'Must contain seeded brains').toBeGreaterThanOrEqual(5);

      const ids = brains.map((b: { id: string }) => b.id);
      expect(ids).toContain('brain_org_global');
      expect(ids).toContain('brain_cross_frontend');
      expect(ids).toContain('brain_cross_devops');
      expect(ids).toContain('brain_team_platform');
    }
  });

  test('GET /brains with query filters resolves cross-functional domains', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: Cloudflare Access service token not set');

    // Filter by cross_functional scope
    const cfUrl = `${FUZEAGENT_BASE}/brains?scope=cross_functional`;
    const cfRes = await request.get(cfUrl, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    });
    expect(cfRes.status()).toBe(200);
    const cfBrains = await cfRes.json();
    expect(cfBrains.length).toBeGreaterThanOrEqual(3);

    const domains = cfBrains.map((b: { functional_domain?: string }) => b.functional_domain);
    expect(domains).toContain('frontend');
    expect(domains).toContain('devops');
    expect(domains).toContain('backend');

    // Filter specifically by frontend domain
    const feUrl = `${FUZEAGENT_BASE}/brains?functional_domain=frontend`;
    const feRes = await request.get(feUrl, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    });
    expect(feRes.status()).toBe(200);
    const feBrains = await feRes.json();
    expect(feBrains.some((b: { id: string }) => b.id === 'brain_cross_frontend')).toBe(true);
  });

  test('GET /agents/:agent_id/brains resolves 4-tier hierarchy for agents', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: Cloudflare Access service token not set');

    // Verify react-dev hierarchy (frontend domain)
    const reactUrl = `${FUZEAGENT_BASE}/agents/react-dev/brains`;
    const reactRes = await request.get(reactUrl, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    });
    expect(reactRes.status()).toBe(200);
    const reactData = await reactRes.json();
    expect(reactData.agent_id).toBe('react-dev');
    expect(reactData.functional_domain).toBe('frontend');

    const reactBrainIds = reactData.brains.map((b: { id: string }) => b.id);
    expect(reactBrainIds).toContain('brain_agent_react_dev'); // Persona tier
    expect(reactBrainIds).toContain('brain_cross_frontend');  // Cross-functional tier
    expect(reactBrainIds).toContain('brain_team_platform');   // Team tier
    expect(reactBrainIds).toContain('brain_org_global');      // Organization tier

    // Verify devops-lead hierarchy (devops domain)
    const devopsUrl = `${FUZEAGENT_BASE}/agents/devops-lead/brains`;
    const devopsRes = await request.get(devopsUrl, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    });
    expect(devopsRes.status()).toBe(200);
    const devopsData = await devopsRes.json();
    expect(devopsData.functional_domain).toBe('devops');
    const devopsBrainIds = devopsData.brains.map((b: { id: string }) => b.id);
    expect(devopsBrainIds).toContain('brain_cross_devops');
    expect(devopsBrainIds).toContain('brain_org_global');
  });

  test('Brain CRUD Lifecycle in post-production environment', async ({ request }) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: Cloudflare Access service token not set');

    const testBrainId = `brain_postprod_smoke_${Date.now()}`;

    // 1. Create Brain
    const createRes = await request.post(`${FUZEAGENT_BASE}/brains`, {
      headers: { ...cfHeaders, 'Content-Type': 'application/json' },
      data: {
        id: testBrainId,
        name: 'Post-Prod Smoke Test Brain',
        description: 'Automated post-production verification brain',
        scope: 'cross_functional',
        functional_domain: 'qa',
        tags: ['postprod', 'smoke-test', 'automated'],
      },
    });
    expect([200, 201]).toContain(createRes.status());
    const created = await createRes.json();
    expect(created.id).toBe(testBrainId);

    // 2. Get Brain
    const getRes = await request.get(`${FUZEAGENT_BASE}/brains/${testBrainId}`, {
      headers: { ...cfHeaders, Accept: 'application/json' },
    });
    expect(getRes.status()).toBe(200);
    const fetched = await getRes.json();
    expect(fetched.name).toBe('Post-Prod Smoke Test Brain');

    // 3. Update Brain
    const updateRes = await request.put(`${FUZEAGENT_BASE}/brains/${testBrainId}`, {
      headers: { ...cfHeaders, 'Content-Type': 'application/json' },
      data: {
        description: 'Updated smoke test brain description',
        tags: ['postprod', 'smoke-test', 'updated'],
      },
    });
    expect(updateRes.status()).toBe(200);
    const updated = await updateRes.json();
    expect(updated.description).toBe('Updated smoke test brain description');
    expect(updated.tags).toContain('updated');

    // 4. Associate Brain
    const assocRes = await request.post(`${FUZEAGENT_BASE}/brains/${testBrainId}/associate`, {
      headers: { ...cfHeaders, 'Content-Type': 'application/json' },
      data: {
        scope: 'team',
        team_id: 'team_platform',
      },
    });
    expect(assocRes.status()).toBe(200);
    const associated = await assocRes.json();
    expect(associated.scope).toBe('team');
    expect(associated.team_id).toBe('team_platform');

    // 5. Delete Brain
    const delRes = await request.delete(`${FUZEAGENT_BASE}/brains/${testBrainId}`, {
      headers: { ...cfHeaders },
    });
    expect(delRes.status()).toBe(200);

    // Verify deletion
    const verifyDel = await request.get(`${FUZEAGENT_BASE}/brains/${testBrainId}`, {
      headers: { ...cfHeaders },
    });
    expect(verifyDel.status()).toBe(404);
  });
});

test.describe('Dual MCP Server Brain Tools (Post-Production)', () => {
  test('OpenAPI contract publishes Brain tag and schemas', async ({ request }) => {
    const openApiUrl = `${FUZEAGENT_BASE}/openapi.json`;
    const res = await request.fetch(openApiUrl, {
      headers: { ...cfHeaders, Accept: 'application/json' },
      maxRedirects: 0,
    });

    if (res.status() === 200) {
      const openApi = await res.json();
      expect(openApi.paths['/brains'] || openApi.paths['/api/brains']).toBeDefined();
      expect(openApi.paths['/agents/{agent_id}/brains'] || openApi.paths['/api/agents/{agent_id}/brains']).toBeDefined();
    }
  });
});

test.describe('Standalone Chat Workspace UI (/chat/window)', () => {
  test.beforeEach(({}) => {
    test.skip(!HAS_CF_TOKEN, 'Skipped: Cloudflare Access service token not set (set CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET)');
  });

  test('Navigates to /chat/window and renders standalone window layout', async ({ page }) => {
    if (HAS_CF_TOKEN) {
      await page.setExtraHTTPHeaders(cfHeaders);
    }

    const chatWindowUrl = `${FUZEAGENT_BASE}/chat/window`;
    const response = await page.goto(chatWindowUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30_000,
    });


    // Verify page responded
    expect(response?.status()).toBeLessThan(400);

    // Check header branding and standalone indicator
    const branding = page.locator('text=FuzeAgent').or(page.locator('text=Chat'));
    await expect(branding.first()).toBeVisible({ timeout: 15_000 });

    // Check conversation thread sidebar
    const conversationHeader = page.locator('text=Conversations').or(page.locator('text=LA Timezone Verification'));
    await expect(conversationHeader.first()).toBeVisible({ timeout: 10_000 });

    // Check active model selector
    const modelSelector = page.locator('select').or(page.getByRole('combobox'));
    await expect(modelSelector.first()).toBeVisible({ timeout: 5_000 });

    // Check Popout button
    const popoutButton = page.getByRole('button', { name: /popout/i }).or(page.locator('button:has-text("Popout")'));
    await expect(popoutButton.first()).toBeVisible({ timeout: 5_000 });

    // Verify presence of interactive action chips
    const actionChip = page.locator('button:has-text("Time in LA")').or(page.locator('text=Time in LA'));
    await expect(actionChip.first()).toBeVisible({ timeout: 5_000 });

    // Verify multi-tier Brain architecture telemetry drawer is rendered
    const brainDrawer = page.locator('text=Brain Architecture').or(page.locator('text=Cross-Functional Brain'));
    await expect(brainDrawer.first()).toBeVisible({ timeout: 10_000 });
  });

  test('Renders TimeInZoneCard and Terminal logs in chat stream', async ({ page }) => {
    if (HAS_CF_TOKEN) {
      await page.setExtraHTTPHeaders(cfHeaders);
    }

    await page.goto(`${FUZEAGENT_BASE}/chat/window`, {
      waitUntil: 'domcontentloaded',
      timeout: 30_000,
    });

    // Check for LA time message bubble or card
    const timeMessage = page.locator('text=Los Angeles').or(page.locator('text=PDT'));
    await expect(timeMessage.first()).toBeVisible({ timeout: 10_000 });

    // Check container telemetry terminal
    const terminalTitle = page.locator('text=Container Sandbox Logs').or(page.locator('text=sandbox-init'));
    await expect(terminalTitle.first()).toBeVisible({ timeout: 10_000 });
  });
});
