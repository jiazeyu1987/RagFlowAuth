// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

async function expectErrorVisible(page, message) {
  const byTestId = page.getByTestId('docs-error');
  if ((await byTestId.count()) > 0) {
    await expect(byTestId).toContainText(message);
    return;
  }
  await expect(page.getByText(message, { exact: false })).toBeVisible();
}

async function expectEmptyVisible(page) {
  const byTestId = page.getByTestId('docs-empty');
  if ((await byTestId.count()) > 0) {
    await expect(byTestId).toBeVisible();
    return;
  }
  // Fallback for older UI without testid.
  await expect(page.getByText(/暂无待审核文档|请选择知识库/)).toBeVisible();
}

adminTest('documents pending list 500 shows error banner (mock) @regression @documents', async ({ page }) => {
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

adminTest('documents pending list 504 shows error banner (mock) @regression @documents', async ({ page }) => {
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

adminTest('documents empty pending list shows empty state (mock) @regression @documents', async ({ page }) => {
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
  await expectEmptyVisible(page);
});

adminTest('documents approve 403 shows error and keeps row (mock) @regression @documents', async ({ page }) => {
  const filename = `e2e_pending_${Date.now()}.txt`;
  const docs = [{ doc_id: 'd1', filename, status: 'pending', kb_id: 'kb1', uploaded_at_ms: Date.now() }];

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
  await expect(page.locator('tr', { hasText: filename })).toBeVisible();

  page.once('dialog', async (dialog) => dialog.accept());
  await page.getByTestId('docs-approve-d1').click();

  await expectErrorVisible(page, 'forbidden');
  await expect(page.locator('tr', { hasText: filename })).toBeVisible();
});
