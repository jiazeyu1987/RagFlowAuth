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

adminTest('documents preview failure shows error (mock) @regression @documents', async ({ page }) => {
  const doc = { doc_id: 'd1', filename: 'a.txt', status: 'pending', uploaded_at_ms: Date.now(), kb_id: 'kb1', uploaded_by: 'u1' };

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }] }) });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [doc], count: 1 }) });
  });

  await page.route('**/api/knowledge/documents/d1/preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'preview failed' }) });
  });

  await page.goto('/documents');

  const row = page.locator('tr', { hasText: 'a.txt' });
  await expect(row).toBeVisible();
  await row.getByRole('button', { name: '查看' }).click();

  await expectErrorVisible(page, 'preview failed');
});

