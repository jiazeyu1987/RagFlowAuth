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

adminTest('documents conflict diff rejects unsupported types (mock) @regression @documents', async ({ page }) => {
  const kbId = 'kb_1';
  const now = Date.now();

  const oldDoc = { doc_id: 'old_1', filename: 'same.pdf', uploaded_at_ms: now - 60_000 };
  const newDoc = { doc_id: 'new_1', filename: 'same.pdf', status: 'pending', kb_id: kbId, uploaded_at_ms: now };

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: kbId, name: kbId }] }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    if (url.searchParams.get('status') !== 'pending') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [newDoc] }) });
  });

  await page.route('**/api/knowledge/documents/new_1/conflict', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ conflict: true, existing: oldDoc, normalized_name: 'same' }),
    });
  });

  await page.goto('/documents');
  await page.getByTestId('docs-approve-new_1').click();
  await expect(page.getByTestId('docs-overwrite-modal')).toBeVisible();

  await page.getByRole('button', { name: '对比差异' }).click();
  await expectErrorVisible(page, '对比功能仅支持');
});

