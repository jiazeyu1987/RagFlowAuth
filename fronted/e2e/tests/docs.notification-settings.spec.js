// @ts-check
const { expect } = require('@playwright/test');
const { docAdminTest } = require('../helpers/docAuth');
const { loadDocFixtures } = require('../helpers/bootstrapSummary');

const fixtures = loadDocFixtures();

docAdminTest('Doc notification settings exercise real rules, channels, history, retry, and dispatch @doc-e2e', async ({ page }) => {
  let queuedJobId = String(fixtures.notifications.history.queued_job_id || '');
  let failedJobId = String(fixtures.notifications.history.failed_job_id || '');

  await page.goto('/notification-settings');
  await expect(page.getByTestId('notification-settings-page')).toBeVisible();

  const todoEmailRule = page.getByTestId('notification-rule-operation_approval_todo-email');
  const todoDingtalkRule = page.getByTestId('notification-rule-operation_approval_todo-dingtalk');
  const todoInAppRule = page.getByTestId('notification-rule-operation_approval_todo-in_app');

  await expect(todoEmailRule).not.toBeChecked();
  await expect(todoInAppRule).toBeChecked();
  await expect(todoDingtalkRule).not.toBeChecked();

  const saveRulesResponse = page.waitForResponse((response) => (
    response.request().method() === 'PUT'
    && response.url().includes('/api/admin/notifications/rules')
  ));
  await todoDingtalkRule.check();
  await page.getByTestId('notification-save-rules').click();
  await expect((await saveRulesResponse).ok()).toBeTruthy();

  await page.reload();
  await expect(page.getByTestId('notification-rule-operation_approval_todo-dingtalk')).toBeChecked();

  await page.getByTestId('notification-tab-channels').click();
  await page.getByTestId('notification-email-host').fill('smtp.doc-e2e.test');
  await page.getByTestId('notification-email-port').fill('465');
  await page.getByTestId('notification-email-from-email').fill('doc-e2e@example.test');
  await page.getByTestId('notification-dingtalk-app-key').fill('doc-e2e-app-key');
  await page.getByTestId('notification-dingtalk-recipient-map').fill(JSON.stringify({
    doc_company_admin: 'doc-company-admin',
    e2e_reviewer: 'real-reviewer',
  }, null, 2));

  const saveChannelResponses = Promise.all([
    page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes('/api/admin/notifications/channels/email-main')
    )),
    page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes('/api/admin/notifications/channels/dingtalk-main')
    )),
    page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes('/api/admin/notifications/channels/inapp-main')
    )),
  ]);
  await page.getByTestId('notification-save-channels').click();
  for (const response of await saveChannelResponses) {
    await expect(response.ok()).toBeTruthy();
  }
  await expect(page.getByTestId('notification-email-host')).toHaveValue('smtp.doc-e2e.test');

  await page.reload();
  await page.getByTestId('notification-tab-channels').click();
  await expect(page.getByTestId('notification-email-host')).toHaveValue('smtp.doc-e2e.test');
  await expect(page.getByTestId('notification-email-from-email')).toHaveValue('doc-e2e@example.test');
  await expect(page.getByTestId('notification-dingtalk-app-key')).toHaveValue('doc-e2e-app-key');

  await page.getByTestId('notification-tab-history').click();

  const failedHistoryResponse = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/admin/notifications/jobs')
    && response.url().includes('status=failed')
  ));
  await page.getByTestId('notification-history-status').selectOption('failed');
  await page.getByTestId('notification-history-apply').click();
  await expect((await failedHistoryResponse).ok()).toBeTruthy();
  const failedRetryButton = page.locator('[data-testid^="notification-retry-"]').first();
  await expect(failedRetryButton).toBeVisible();
  failedJobId = String((await failedRetryButton.getAttribute('data-testid')) || '')
    .replace('notification-retry-', '')
    .trim();
  expect(failedJobId).toBeTruthy();

  const retryResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/admin/notifications/jobs/${failedJobId}/retry`)
  ));
  await failedRetryButton.click();
  await expect((await retryResponse).ok()).toBeTruthy();

  const sentHistoryAfterRetry = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/admin/notifications/jobs')
    && response.url().includes('status=sent')
  ));
  await page.getByTestId('notification-history-status').selectOption('sent');
  await page.getByTestId('notification-history-apply').click();
  await expect((await sentHistoryAfterRetry).ok()).toBeTruthy();
  await expect(page.locator('tbody')).toContainText(String(failedJobId));

  const queuedHistoryResponse = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/admin/notifications/jobs')
    && response.url().includes('status=queued')
  ));
  await page.getByTestId('notification-history-status').selectOption('queued');
  await page.getByTestId('notification-history-apply').click();
  await expect((await queuedHistoryResponse).ok()).toBeTruthy();
  const queuedJobIdCell = page.locator('tbody tr td').first();
  await expect(queuedJobIdCell).toBeVisible();
  queuedJobId = String((await queuedJobIdCell.textContent()) || '').trim();
  expect(queuedJobId).toBeTruthy();
  await expect(page.locator('tbody')).toContainText(queuedJobId);

  const dispatchResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes('/api/admin/notifications/dispatch')
  ));
  await page.getByTestId('notification-dispatch-pending').click();
  await expect((await dispatchResponse).ok()).toBeTruthy();

  const sentHistoryAfterDispatch = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/admin/notifications/jobs')
    && response.url().includes('status=sent')
  ));
  await page.getByTestId('notification-history-status').selectOption('sent');
  await page.getByTestId('notification-history-apply').click();
  await expect((await sentHistoryAfterDispatch).ok()).toBeTruthy();
  await expect(page.locator('tbody')).toContainText(queuedJobId);
});
