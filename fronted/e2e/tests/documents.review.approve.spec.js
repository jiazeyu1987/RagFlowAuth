// @ts-check
const { expect } = require('@playwright/test');
const { reviewerTest } = require('../helpers/auth');
const { submitReviewSignature } = require('../helpers/reviewSignature');

const REVIEWER_PASSWORD = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

reviewerTest('reviewer can approve a pending document (stubbed docs) @regression @documents', async ({ page }) => {
  const docs = [
    {
      doc_id: 'local1',
      filename: 'e2e_pending.txt',
      file_size: 12,
      mime_type: 'text/plain',
      uploaded_by: 'u1',
      uploaded_by_name: 'admin',
      status: 'pending',
      uploaded_at_ms: Date.now(),
      reviewed_by: null,
      reviewed_at_ms: null,
      review_notes: null,
      ragflow_doc_id: null,
      kb_id: 'kb1',
    },
  ];

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }], count: 1 }),
    });
  });

  await page.route('**/api/knowledge/documents/local1/conflict', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ conflict: false }),
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

  const approveReqPromise = page.waitForRequest('**/api/knowledge/documents/local1/approve');
  await page.route('**/api/knowledge/documents/local1/approve', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const body = route.request().postDataJSON();
    expect(body).toMatchObject({
      sign_token: expect.any(String),
      signature_meaning: 'Approve pending document',
      signature_reason: 'Mock approval for e2e review',
    });
    docs.length = 0;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/documents');
  await expect(page.getByTestId('docs-approve-local1')).toBeVisible();

  await page.getByTestId('docs-approve-local1').click();
  await submitReviewSignature(page, {
    password: REVIEWER_PASSWORD,
    meaning: 'Approve pending document',
    reason: 'Mock approval for e2e review',
  });

  await approveReqPromise;
  await expect(page.getByTestId('docs-approve-local1')).toHaveCount(0);
});
