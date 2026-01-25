// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('review detects conflict and can approve-overwrite (mock) @regression @documents', async ({ page }) => {
  const kbId = 'kb_1';
  const now = Date.now();

  const oldDoc = { doc_id: 'old_1', filename: 'same.txt', uploaded_at_ms: now - 60_000 };
  const newDoc = { doc_id: 'new_1', filename: 'same.txt', status: 'pending', kb_id: kbId, uploaded_at_ms: now };

  let pending = [newDoc];
  let approveOverwriteBody = null;

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
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: pending }) });
  });

  await page.route('**/api/knowledge/documents/new_1/conflict', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ conflict: true, existing: oldDoc, normalized_name: 'same' }),
    });
  });

  await page.route('**/api/knowledge/documents/new_1/approve-overwrite', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    approveOverwriteBody = route.request().postDataJSON();
    pending = [];
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/documents');

  await expect(page.getByText('same.txt', { exact: true })).toBeVisible();

  await page.getByTestId('docs-approve-new_1').click();
  await expect(page.getByTestId('docs-overwrite-modal')).toBeVisible();

  page.once('dialog', async (dialog) => {
    if (dialog.type() === 'confirm') await dialog.accept();
    else await dialog.dismiss();
  });
  await page.getByTestId('docs-overwrite-use-new').click();

  expect(approveOverwriteBody).toBeTruthy();
  expect(approveOverwriteBody.replace_doc_id).toBe('old_1');

  await expect(page.getByTestId('docs-overwrite-modal')).toHaveCount(0);
  await expect(page.getByText('same.txt', { exact: true })).toHaveCount(0);
});

