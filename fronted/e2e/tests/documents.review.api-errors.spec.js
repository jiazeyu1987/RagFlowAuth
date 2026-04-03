// @ts-check
const { expect } = require('@playwright/test');
const { reviewerTest } = require('../helpers/auth');
const { submitReviewSignature } = require('../helpers/reviewSignature');

async function expectErrorVisible(page, message) {
  await expect(page.getByTestId('docs-error')).toContainText(message);
}

const REVIEWER_PASSWORD = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

reviewerTest('documents pending list 500 shows error banner @regression @documents', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }] }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'server exploded' }),
    });
  });

  await page.goto('/documents');
  await expectErrorVisible(page, 'server exploded');
});

reviewerTest('documents pending list 504 shows error banner @regression @documents', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }] }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({
      status: 504,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'gateway timeout' }),
    });
  });

  await page.goto('/documents');
  await expectErrorVisible(page, 'gateway timeout');
});

reviewerTest('documents empty pending list shows empty state @regression @documents', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }] }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [], count: 0 }) });
  });

  await page.goto('/documents');
  await expect(page.getByTestId('docs-empty')).toBeVisible({ timeout: 30000 });
});

reviewerTest('documents approve 403 shows error and keeps row @regression @documents', async ({ page }) => {
  const docs = [{ doc_id: 'd1', filename: 'e2e_pending.txt', status: 'pending', kb_id: 'kb1', uploaded_at_ms: Date.now() }];

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }] }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: docs, count: docs.length }),
    });
  });

  await page.route('**/api/knowledge/documents/d1/conflict', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ conflict: false }) });
  });

  await page.route('**/api/knowledge/documents/d1/approve', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({ status: 403, contentType: 'application/json', body: JSON.stringify({ detail: 'forbidden' }) });
  });

  await page.goto('/documents');
  await expect(page.getByTestId('docs-approve-d1')).toBeVisible();

  const approveRequest = page.waitForRequest('**/api/knowledge/documents/d1/approve');
  await page.getByTestId('docs-approve-d1').click();
  await submitReviewSignature(page, {
    password: REVIEWER_PASSWORD,
    meaning: 'Approve document',
    reason: 'Expect backend to reject this request',
  });
  await approveRequest;

  await expectErrorVisible(page, 'forbidden');
  await expect(page.getByTestId('docs-approve-d1')).toBeVisible();
});
