// @ts-check
const { expect } = require('@playwright/test');
const { reviewerTest } = require('../helpers/auth');
const { submitReviewSignature } = require('../helpers/reviewSignature');

const REVIEWER_PASSWORD = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

reviewerTest('review actions require signature modal and submit signature payload @regression @documents', async ({ page }) => {
  const docs = [{
    doc_id: 'sig-doc-1',
    filename: 'signature-doc.txt',
    status: 'pending',
    kb_id: 'kb1',
    uploaded_at_ms: Date.now(),
  }];
  let signatureChallengeBody = null;
  let approveBody = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'kb1' }] }),
    });
  });

  await page.route('**/api/knowledge/documents/sig-doc-1/conflict', async (route) => {
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

  await page.route('**/api/knowledge/documents/sig-doc-1/approve', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    approveBody = route.request().postDataJSON();
    docs.length = 0;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.goto('/documents');
  await expect(page.getByTestId('docs-approve-sig-doc-1')).toBeVisible();

  const signatureChallengeRequest = page.waitForRequest('**/api/auth/signature-challenge');
  const signatureChallengeResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
      && response.url().includes('/api/auth/signature-challenge')
      && response.ok()
  ));
  const approveResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
      && response.url().includes('/api/knowledge/documents/sig-doc-1/approve')
  ));
  await page.getByTestId('docs-approve-sig-doc-1').click();
  await submitReviewSignature(page, {
    password: REVIEWER_PASSWORD,
    meaning: 'Approve signed document',
    reason: 'Signature is mandatory for approval',
  });
  const [challengeRequest, challengePayload] = await Promise.all([
    signatureChallengeRequest,
    signatureChallengeResponse.then((response) => response.json()),
  ]);
  await approveResponse;

  signatureChallengeBody = challengeRequest.postDataJSON();
  expect(signatureChallengeBody).toEqual({ password: REVIEWER_PASSWORD });
  expect(approveBody).toMatchObject({
    sign_token: challengePayload.sign_token,
    signature_meaning: 'Approve signed document',
    signature_reason: 'Signature is mandatory for approval',
  });
  await expect(page.getByTestId('docs-approve-sig-doc-1')).toHaveCount(0);
});
