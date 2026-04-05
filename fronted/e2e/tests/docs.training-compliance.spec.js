// @ts-check
const { expect } = require('@playwright/test');
const { docAdminTest } = require('../helpers/docAuth');
const { loadDocFixtures } = require('../helpers/bootstrapSummary');

const fixtures = loadDocFixtures();

docAdminTest('培训合规文档流程覆盖刷新与页签切换 @doc-e2e', async ({ page }) => {
  await page.goto('/training-compliance');

  await expect(page.getByTestId('training-compliance-page')).toBeVisible();
  await expect(page.getByRole('cell', { name: fixtures.training.requirement_code }).first()).toBeVisible();
  await expect(page.getByTestId('training-records-tab-panel')).toBeVisible();

  const refreshResponses = Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === 'GET'
        && response.url().includes('/api/training-compliance/requirements')
    ),
    page.waitForResponse(
      (response) =>
        response.request().method() === 'GET'
        && response.url().includes('/api/training-compliance/records')
    ),
    page.waitForResponse(
      (response) =>
        response.request().method() === 'GET'
        && response.url().includes('/api/training-compliance/certifications')
    ),
  ]);
  await page.getByRole('button', { name: '刷新' }).click();
  await refreshResponses;

  await page.getByTestId('training-tab-certifications').click();
  await expect(page.getByTestId('training-certifications-tab-panel')).toBeVisible();
  await page.getByTestId('training-tab-records').click();
  await expect(page.getByTestId('training-records-tab-panel')).toBeVisible();
});

docAdminTest('培训合规文档流程使用真实用户搜索并保存培训记录和认证 @doc-e2e', async ({ page }) => {
  await page.goto('/training-compliance');

  await page.getByTestId('training-record-requirement').selectOption(fixtures.training.requirement_code);

  const recordSearchResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET'
      && response.url().includes('/api/users')
      && response.url().toLowerCase().includes(String(fixtures.training.unit_target_username).toLowerCase())
  );
  await page.getByTestId('training-record-user-search-input').fill(fixtures.training.unit_target_username);
  await recordSearchResponse;
  await page
    .getByTestId(`training-record-user-search-result-${fixtures.training.unit_target_user_id}`)
    .click();
  await expect(page.getByTestId('training-record-user-search-selected')).not.toContainText('未选择用户');

  await page.getByTestId('training-record-summary').fill('文档驱动培训记录，满足审批上岗条件');
  await page.getByTestId('training-record-notes').fill('真实环境保存培训记录');

  const recordResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST'
      && response.url().includes('/api/training-compliance/records')
  );
  await page.getByTestId('training-record-submit').click();
  const savedRecordResponse = await recordResponse;
  await expect(savedRecordResponse.ok()).toBeTruthy();
  await expect(page.getByTestId('training-compliance-success')).toBeVisible();

  await page.getByTestId('training-tab-certifications').click();
  await expect(page.getByTestId('training-certifications-tab-panel')).toBeVisible();
  await expect(page.getByTestId('training-certification-user-search-selected')).not.toContainText('未选择用户');

  await page.getByTestId('training-certification-requirement').selectOption(fixtures.training.requirement_code);
  await page.getByTestId('training-certification-status').selectOption('active');
  await page.getByTestId('training-certification-valid-until').fill('2026-12-31T09:30');
  await page.getByTestId('training-certification-notes').fill('真实环境保存上岗认证');

  const certificationResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST'
      && response.url().includes('/api/training-compliance/certifications')
  );
  await page.getByTestId('training-certification-submit').click();
  const savedCertificationResponse = await certificationResponse;
  await expect(savedCertificationResponse.ok()).toBeTruthy();
  await expect(page.getByTestId('training-compliance-success')).toBeVisible();
});
