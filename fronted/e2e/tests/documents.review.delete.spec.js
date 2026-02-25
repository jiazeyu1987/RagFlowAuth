// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('admin can delete a local document (mock) @regression @documents', async ({ page }) => {
  const doc = {
    doc_id: 'd1',
    filename: 'to_delete.txt',
    file_size: 12,
    mime_type: 'text/plain; charset=utf-8',
    uploaded_by: 'u1',
    uploaded_by_name: 'admin',
    status: 'pending',
    uploaded_at_ms: Date.now(),
    kb_id: 'kb1',
  };

  let pending = [doc];
  let deleteSeen = false;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }] }) });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: pending, count: pending.length }) });
  });

  await page.route('**/api/documents/knowledge/d1', async (route) => {
    if (route.request().method() !== 'DELETE') return route.fallback();
    deleteSeen = true;
    pending = [];
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/documents');
  const row = page.locator('tr', { hasText: 'to_delete.txt' });
  await expect(row).toBeVisible();

  page.once('dialog', async (dialog) => dialog.accept());
  await row.locator('[data-testid="docs-delete-d1"]').click();

  await expect(page.locator('tr', { hasText: 'to_delete.txt' })).toHaveCount(0);
  expect(deleteSeen).toBe(true);
});
