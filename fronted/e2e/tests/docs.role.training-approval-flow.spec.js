// @ts-check
const { test, expect } = require('@playwright/test');
const {
  companyAdminStorageStatePath,
  untrainedReviewerStorageStatePath,
} = require('../helpers/auth');
const { loadDocFixtures } = require('../helpers/bootstrapSummary');
const { submitReviewSignature } = require('../helpers/reviewSignature');

const fixtures = loadDocFixtures();
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
const reviewerPassword = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

async function openContextPage(browser, storageState) {
  const context = await browser.newContext({ storageState });
  const page = await context.newPage();
  return { context, page };
}

async function selectTrainingUser(page, prefix) {
  await page.getByTestId(`${prefix}-input`).fill(fixtures.training.role_target_username);
  const result = page.getByTestId(`${prefix}-result-${fixtures.training.role_target_user_id}`);
  await expect(result).toBeVisible();
  const displayLabel = (await result.locator('div').first().textContent())?.trim();
  await result.click();
  await expect(page.getByTestId(`${prefix}-selected`)).toContainText(displayLabel || fixtures.training.role_target_username);
}

async function createTrainingRecord(page) {
  await expect(page.getByTestId('training-compliance-page')).toBeVisible();
  await selectTrainingUser(page, 'training-record-user-search');
  await page.getByTestId('training-record-requirement').selectOption(fixtures.training.requirement_code);
  await page.getByTestId('training-record-summary').fill('Real doc E2E reviewer qualification record');
  await page.getByTestId('training-record-notes').fill('Seeded during role approval flow remediation');

  const response = page.waitForResponse((result) => (
    result.request().method() === 'POST'
    && result.url().includes('/api/training-compliance/records')
  ));
  await page.getByTestId('training-record-submit').click();
  await expect((await response).ok()).toBeTruthy();
}

async function createCertification(page, status) {
  await page.getByTestId('training-tab-certifications').click();
  await expect(page.getByTestId('training-certifications-tab-panel')).toBeVisible();
  await selectTrainingUser(page, 'training-certification-user-search');
  await page.getByTestId('training-certification-requirement').selectOption(fixtures.training.requirement_code);
  await page.getByTestId('training-certification-status').selectOption(status);
  await page.getByTestId('training-certification-valid-until').fill('2099-12-31T09:30');
  await page.getByTestId('training-certification-notes').fill(`Real doc E2E certification: ${status}`);

  const response = page.waitForResponse((result) => (
    result.request().method() === 'POST'
    && result.url().includes('/api/training-compliance/certifications')
  ));
  await page.getByTestId('training-certification-submit').click();
  await expect((await response).ok()).toBeTruthy();
}

async function attemptApproval(page, requestId, reason) {
  await page.goto(`/approvals?request_id=${requestId}`);
  await expect(page.getByTestId('approval-center-page')).toBeVisible();
  await expect(page.getByTestId(`approval-center-item-${requestId}`)).toBeVisible();
  await page.getByTestId(`approval-center-item-${requestId}`).click();
  await expect(page.getByTestId('approval-center-approve')).toBeVisible();

  const response = page.waitForResponse((result) => (
    result.request().method() === 'POST'
    && result.url().includes(`/api/operation-approvals/requests/${requestId}/approve`)
  ));
  await page.getByTestId('approval-center-approve').click();
  await submitReviewSignature(page, {
    password: reviewerPassword,
    meaning: 'Real doc approval decision',
    reason,
  });
  return response;
}

test('Doc role training flow enforces real approval gates, remediation, and re-blocking @doc-e2e', async ({ browser }) => {
  const reviewer = await openContextPage(browser, untrainedReviewerStorageStatePath);
  const admin = await openContextPage(browser, companyAdminStorageStatePath);

  try {
    const blockedMissingResponse = await attemptApproval(
      reviewer.page,
      fixtures.approvals.training_gate.missing_request_id,
      'Expect missing training to block approval'
    );
    expect(blockedMissingResponse.status()).toBe(403);
    expect(await blockedMissingResponse.json()).toMatchObject({ detail: 'training_record_missing' });
    await expect(reviewer.page.getByTestId('approval-center-error')).toBeVisible();

    await admin.page.goto(
      `/training-compliance?tab=records&user_id=${fixtures.training.role_target_user_id}&controlled_action=${fixtures.training.controlled_action}`
    );
    await createTrainingRecord(admin.page);
    await createCertification(admin.page, 'active');

    const approvedAfterRemediation = await attemptApproval(
      reviewer.page,
      fixtures.approvals.training_gate.missing_request_id,
      'Training and certification have now been completed'
    );
    await expect(approvedAfterRemediation.ok()).toBeTruthy();
    await expect(
      reviewer.page.getByTestId(`approval-center-item-${fixtures.approvals.training_gate.missing_request_id}`)
    ).toHaveCount(0);

    await admin.page.goto(
      `/training-compliance?tab=certifications&user_id=${fixtures.training.role_target_user_id}&controlled_action=${fixtures.training.controlled_action}`
    );
    await createCertification(admin.page, 'expired');

    const blockedExpiredResponse = await attemptApproval(
      reviewer.page,
      fixtures.approvals.training_gate.expired_request_id,
      'Latest certification is intentionally expired'
    );
    expect(blockedExpiredResponse.status()).toBe(403);
    expect(await blockedExpiredResponse.json()).toMatchObject({ detail: 'operator_certification_expired' });
    await expect(reviewer.page.getByTestId('approval-center-error')).toBeVisible();
    await expect(
      reviewer.page.getByTestId(`approval-center-item-${fixtures.approvals.training_gate.expired_request_id}`)
    ).toBeVisible();
  } finally {
    await admin.page.close();
    await admin.context.close();
    await reviewer.page.close();
    await reviewer.context.close();
  }
});
