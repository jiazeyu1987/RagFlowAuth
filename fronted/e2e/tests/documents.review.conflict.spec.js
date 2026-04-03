// @ts-check
const { expect } = require('@playwright/test');
const { reviewerTest } = require('../helpers/auth');
const { submitReviewSignature } = require('../helpers/reviewSignature');

const REVIEWER_PASSWORD = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

reviewerTest('review detects conflict and can approve-overwrite @regression @documents', async ({ page }) => {
  const oldDoc = { doc_id: 'old_1', filename: 'same.txt', uploaded_at_ms: Date.now() - 60000 };
  const docs = [{ doc_id: 'new_1', filename: 'same.txt', status: 'pending', kb_id: 'kb1', uploaded_at_ms: Date.now() }];
  let approveOverwriteBody = null;

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
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: docs, count: docs.length }) });
  });

  await page.route('**/api/knowledge/documents/new_1/conflict', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ conflict: true, existing: oldDoc, normalized_name: 'same' }),
    });
  });

  await page.route('**/api/knowledge/documents/new_1/approve-overwrite', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    approveOverwriteBody = route.request().postDataJSON();
    docs.length = 0;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/documents');
  await expect(page.getByTestId('docs-approve-new_1')).toBeVisible();
  await page.getByTestId('docs-approve-new_1').click();
  await expect(page.getByTestId('docs-overwrite-modal')).toBeVisible();

  const overwriteResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
      && response.url().includes('/api/knowledge/documents/new_1/approve-overwrite')
  ));
  await page.getByTestId('docs-overwrite-use-new').click();
  await submitReviewSignature(page, {
    password: REVIEWER_PASSWORD,
    meaning: 'Approve overwrite',
    reason: 'Use newer conflicting document',
  });
  await overwriteResponse;

  expect(approveOverwriteBody).toMatchObject({
    replace_doc_id: 'old_1',
    sign_token: expect.any(String),
    signature_meaning: 'Approve overwrite',
    signature_reason: 'Use newer conflicting document',
  });
  await expect(page.getByTestId('docs-overwrite-modal')).toHaveCount(0);
  await expect(page.getByTestId('docs-approve-new_1')).toHaveCount(0);
});
