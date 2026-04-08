// @ts-check
const { expect } = require('@playwright/test');
const { docReviewerTest } = require('../helpers/docAuth');
const { loadDocFixtures } = require('../helpers/bootstrapSummary');
const { submitReviewSignature } = require('../helpers/reviewSignature');

const fixtures = loadDocFixtures();
const reviewerPassword = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

docReviewerTest('Doc approval center covers real approve, reject, and withdraw flows @doc-e2e', async ({ page }) => {
  await page.goto('/approvals');
  await expect(page.getByTestId('approval-center-page')).toBeVisible();
  await expect(page.getByTestId(`approval-center-item-${fixtures.approvals.unit.approve_request_id}`)).toBeVisible();
  await expect(page.getByTestId(`approval-center-item-${fixtures.approvals.unit.reject_request_id}`)).toBeVisible();

  await page.getByTestId(`approval-center-item-${fixtures.approvals.unit.approve_request_id}`).click();
  await expect(page.getByTestId('approval-center-approve')).toBeVisible();

  const approveResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/operation-approvals/requests/${fixtures.approvals.unit.approve_request_id}/approve`)
  ));
  await page.getByTestId('approval-center-approve').click();
  await submitReviewSignature(page, {
    password: reviewerPassword,
    meaning: 'Real doc approval accept',
    reason: 'The seeded upload request is ready to proceed',
  });
  await expect((await approveResponse).ok()).toBeTruthy();
  await expect(page.getByTestId(`approval-center-item-${fixtures.approvals.unit.approve_request_id}`)).toHaveCount(0);

  await page.goto(`/approvals?request_id=${fixtures.approvals.unit.reject_request_id}`);
  await expect(page.getByTestId('approval-center-reject')).toBeVisible();

  const rejectResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/operation-approvals/requests/${fixtures.approvals.unit.reject_request_id}/reject`)
  ));
  await page.getByTestId('approval-center-reject').click();
  await submitReviewSignature(page, {
    password: reviewerPassword,
    meaning: 'Real doc approval reject',
    reason: 'The seeded request should remain blocked for revision',
  });
  await expect((await rejectResponse).ok()).toBeTruthy();
  await expect(page.getByTestId(`approval-center-item-${fixtures.approvals.unit.reject_request_id}`)).toHaveCount(0);

  await page.goto(`/approvals?view=mine&request_id=${fixtures.approvals.unit.withdraw_request_id}`);
  await expect(page.getByTestId(`approval-center-item-${fixtures.approvals.unit.withdraw_request_id}`)).toBeVisible();
  await expect(page.getByTestId('approval-center-withdraw')).toBeVisible();

  const withdrawResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/operation-approvals/requests/${fixtures.approvals.unit.withdraw_request_id}/withdraw`)
  ));
  page.once('dialog', async (dialog) => {
    await dialog.accept('Real doc E2E withdraw reason');
  });
  await page.getByTestId('approval-center-withdraw').click({ force: true });

  const withdrawn = await withdrawResponse;
  await expect(withdrawn.ok()).toBeTruthy();
  expect(await withdrawn.json()).toMatchObject({
    result: {
      request_id: fixtures.approvals.unit.withdraw_request_id,
      status: 'withdrawn',
    },
  });
  await expect(page.getByTestId('approval-center-detail-status')).toContainText(/已撤回|withdraw/i);
});
