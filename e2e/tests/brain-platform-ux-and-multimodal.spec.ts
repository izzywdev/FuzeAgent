import { test, expect } from '@playwright/test';
import path from 'path';

/**
 * End-to-End Playwright test suite for:
 * 1. Multimodal S3 Resumable Uploader & Ingestion Lifecycle (05-multimodal-s3-resumable-uploader.html)
 * 2. Enlightening Multi-Tier Context Pipeline Stepper (06-enlightening-multitier-context-pipeline.html)
 * 3. Agent Persona & Avatar Studio (07-agent-persona-and-avatar-studio.html)
 */

const FRAMES_DIR = path.resolve(__dirname, '../../design/frames/fuzeagent-chat-streaming');

test.describe('FuzeAgent Brain Platform: Multimodal Storage & UX Flows', () => {

  test('05: Multimodal S3 Resumable Uploader & Pipeline Ingestion Tracker', async ({ page }) => {
    const framePath = `file:///${path.join(FRAMES_DIR, '05-multimodal-s3-resumable-uploader.html').replace(/\\/g, '/')}`;
    await page.goto(framePath, { waitUntil: 'domcontentloaded' });

    // 1. Verify Page Title & Subtitle
    await expect(page.locator('h1.title')).toContainText('Multimodal S3 Ingestion');
    await expect(page.locator('.subtitle')).toContainText('MinIO S3 object storage');

    // 2. Verify Quota Card with 5GB quota and logical brain path mapping
    const quotaNumbers = page.locator('#quotaNumbers');
    await expect(quotaNumbers).toBeVisible();
    await expect(quotaNumbers).toContainText('5.00 GB');

    const quotaDetails = page.locator('.quota-details');
    await expect(quotaDetails).toContainText('brains/brain_cross_backend');
    await expect(quotaDetails).toContainText('MinIO S3 (FuzeInfra)');

    // 3. Verify Dropzone & Multi-select File Input
    const dropzone = page.locator('.dropzone');
    await expect(dropzone).toBeVisible();
    await expect(dropzone).toContainText('Drop documents, images, audio recordings, or videos here');

    const fileInput = page.locator('#fileInput');
    await expect(fileInput).toHaveAttribute('multiple', '');

    // 4. Verify Ingested File List Items and Media Types
    const fileList = page.locator('#fileList');
    await expect(fileList).toBeVisible();

    const fileItems = page.locator('.file-item');
    expect(await fileItems.count()).toBeGreaterThanOrEqual(2);

    // Verify video item with media ingestion stages
    const videoItem = page.locator('.file-item:has-text("backend-architecture-deepdive.mp4")');
    await expect(videoItem).toBeVisible();
    await expect(videoItem.locator('.badge:has-text("Whisper Audio Transcribed")')).toBeVisible();
    await expect(videoItem.locator('.badge:has-text("Keyframes Extracted")')).toBeVisible();
    await expect(videoItem.locator('.badge:has-text("pgvector")')).toBeVisible();

    // Verify document item with full graph pipeline completion
    const pdfItem = page.locator('.file-item:has-text("enterprise-zero-trust-guidelines.pdf")');
    await expect(pdfItem).toBeVisible();
    await expect(pdfItem.locator('.badge-done:has-text("pgvector Indexed")')).toBeVisible();
    await expect(pdfItem.locator('.badge-done:has-text("Neo4j Graph Synced")')).toBeVisible();

    // 5. Test Resumable Upload Action Buttons (Pause / Resume)
    const pauseBtn = videoItem.locator('button.btn-small:has-text("Pause")');
    await expect(pauseBtn).toBeVisible();
    await pauseBtn.click();
    await page.waitForTimeout(200);
  });

  test('06: Enlightening Multi-Tier Context Pipeline (Fetching -> Augmenting -> Distilling -> Ready -> Stream)', async ({ page }) => {
    const framePath = `file:///${path.join(FRAMES_DIR, '06-enlightening-multitier-context-pipeline.html').replace(/\\/g, '/')}`;
    await page.goto(framePath, { waitUntil: 'domcontentloaded' });

    // 1. Verify Agent Header & Persona
    const agentTitle = page.locator('.agent-title');
    await expect(agentTitle).toContainText('John');
    await expect(agentTitle).toContainText('Senior Backend Engineer');

    const agentSubtitle = page.locator('.agent-subtitle');
    await expect(agentSubtitle).toContainText('Active Brains: Agent Persona + Platform Squad + Cross-Backend + Global Org');

    // 2. Verify Prompt Box & Stepper Initial State
    const promptInput = page.locator('.prompt-input');
    await expect(promptInput).toBeVisible();

    const runBtn = page.locator('.btn-run').first();
    await expect(runBtn).toBeVisible();

    // 3. Trigger Pipeline Simulation
    await promptInput.fill('How do we configure org-scoped S3 buckets with 5GB quota and Neo4j GraphRAG?');
    await runBtn.click();

    // 4. Assert Step 1: Multi-Tier Brain Fetching (4 tiers)
    const step1 = page.locator('#step1');
    await expect(step1).toBeVisible();
    await expect(step1).toContainText('Step 1: Hierarchical Parallel Fetching');
    await expect(step1).toContainText('Tier 4: Agent Brain');
    await expect(step1).toContainText('Tier 3: Team Brain');
    await expect(step1).toContainText('Tier 2: Cross-Functional');
    await expect(step1).toContainText('Tier 1: Global Org');

    // 5. Assert Step 2: Knowledge Graph Traversal
    const step2 = page.locator('#step2');
    await expect(step2).toBeVisible();
    await expect(step2).toContainText('Step 2: Neo4j GraphRAG 2-Hop Traversal');
    await expect(step2).toContainText('BOLT: 7687 (FUZEINFRA)');

    // 6. Assert Step 3: Reciprocal Rank Fusion & Distillation
    const step3 = page.locator('#step3');
    await expect(step3).toBeVisible();
    await expect(step3).toContainText('Step 3: Reciprocal Rank Fusion & Token Distillation');

    // 7. Assert Ready Banner
    const readyBanner = page.locator('.ready-banner');
    await expect(readyBanner).toBeVisible();
    await expect(readyBanner).toContainText('Context Ready!');
    await expect(readyBanner).toContainText('Dispatched to LLM');
  });

  test('07: Agent Persona & Avatar Studio with Dynamic SVG Generator', async ({ page }) => {
    // Handle browser alert automatically if fired
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    const framePath = `file:///${path.join(FRAMES_DIR, '07-agent-persona-and-avatar-studio.html').replace(/\\/g, '/')}`;
    await page.goto(framePath, { waitUntil: 'domcontentloaded' });

    // 1. Verify Page Title
    await expect(page.locator('h1.title')).toContainText('Agent Persona & Avatar Studio');

    // 2. Verify all 4 pre-seeded personas exist in the grid
    const cards = page.locator('.persona-card');
    await expect(cards).toHaveCount(4);

    // Persona 1: Python Dev -> John
    const johnCard = page.locator('#card-python-dev');
    await expect(johnCard).toBeVisible();
    await expect(johnCard.locator('#name-python-dev')).toHaveValue('John');
    await expect(johnCard.locator('#role-python-dev')).toHaveValue('Senior Backend Engineer');

    // Persona 2: React Dev -> Sarah
    const sarahCard = page.locator('#card-react-dev');
    await expect(sarahCard).toBeVisible();
    await expect(sarahCard.locator('#name-react-dev')).toHaveValue('Sarah');
    await expect(sarahCard.locator('#role-react-dev')).toHaveValue('Frontend & UI Architect');

    // Persona 3: Alex -> DevOps
    const alexCard = page.locator('#card-devops-agent');
    await expect(alexCard).toBeVisible();
    await expect(alexCard.locator('#name-devops-agent')).toHaveValue('Alex');

    // Persona 4: Elena -> QA Lead
    const elenaCard = page.locator('#card-qa-agent');
    await expect(elenaCard).toBeVisible();
    await expect(elenaCard.locator('#name-qa-agent')).toHaveValue('Elena');

    // 3. Verify Dynamic SVG Avatar is rendered inside the avatar box
    const johnAvatarSvg = johnCard.locator('.avatar-box svg');
    await expect(johnAvatarSvg).toBeVisible();
    await expect(johnAvatarSvg.locator('circle, rect, path, text').first()).toBeVisible();

    // 4. Test Dynamic Avatar Regeneration
    const regenBtn = johnCard.locator('button.btn-gen:has-text("Regenerate")');
    await expect(regenBtn).toBeVisible();

    const initialSvg = await johnAvatarSvg.innerHTML();
    await regenBtn.click();
    await page.waitForTimeout(200);
    const updatedSvg = await johnAvatarSvg.innerHTML();

    expect(updatedSvg).not.toBe(initialSvg);

    // 5. Test Saving Persona
    const saveBtn = johnCard.locator('button.btn-save:has-text("Save Persona")');
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();
    await page.waitForTimeout(300);
  });
});
