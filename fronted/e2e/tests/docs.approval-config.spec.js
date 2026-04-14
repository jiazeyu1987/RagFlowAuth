// @ts-check
const { expect } = require('@playwright/test');
const { docAdminTest } = require('../helpers/docAuth');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');

const summary = loadBootstrapSummary();
const operatorUserId = String(summary?.users?.operator?.user_id || '');
const workflowName = 'E2E Upload Approval Flow';
const firstStepName = 'E2E Completeness Review';
const secondStepName = 'E2E Manager Signoff';

docAdminTest('approval configuration workflow uses real members and persists saved results @doc-e2e', async ({ page }) => {
  await page.goto('/approval-config');

  await expect(page.getByTestId('approval-config-page')).toBeVisible();
  await expect(page.getByTestId('approval-config-operation-select')).toBeVisible();

  const initialLoadResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET'
      && response.url().includes('/api/operation-approvals/workflows')
  );
  await page.reload();
  await expect((await initialLoadResponse).ok()).toBeTruthy();

  const operationSelect = page.getByTestId('approval-config-operation-select');
  await operationSelect.selectOption('knowledge_file_upload');

  const workflowNameInput = page.getByTestId('approval-config-name-knowledge_file_upload');
  await workflowNameInput.fill(workflowName);
  await expect(workflowNameInput).toHaveValue(/E2E/);

  const firstStepNameInput = page.getByTestId('approval-config-step-name-knowledge_file_upload-0');
  await firstStepNameInput.fill(firstStepName);
  await expect(firstStepNameInput).toHaveValue(firstStepName);

  await page.getByTestId('approval-config-add-member-knowledge_file_upload-0').click();
  const memberInput = page.getByTestId('approval-config-member-ref-knowledge_file_upload-0-1-input');
  await memberInput.fill(String(summary?.users?.operator?.username || 'operator'));
  await page.getByTestId(`approval-config-member-ref-knowledge_file_upload-0-1-result-${operatorUserId}`).click();
  await expect(
    page.getByTestId('approval-config-member-ref-knowledge_file_upload-0-1-selected')
  ).not.toContainText(/No user selected|未选择用户/);

  const firstMemberRow = page.getByTestId('approval-config-member-knowledge_file_upload-0-0');
  await firstMemberRow.getByRole('button', { name: /\u5220\u9664\u6210\u5458/ }).click();
  await expect(page.getByTestId('approval-config-member-knowledge_file_upload-0-0')).toBeVisible();
  await expect(
    page.getByTestId('approval-config-member-ref-knowledge_file_upload-0-0-selected')
  ).not.toContainText(/No user selected|未选择用户/);

  await page.getByTestId('approval-config-add-step-knowledge_file_upload').click();
  await expect(page.getByTestId('approval-config-step-knowledge_file_upload-1')).toBeVisible();
  await page
    .getByTestId('approval-config-step-knowledge_file_upload-1')
    .getByRole('button', { name: /\u5220\u9664\u672c\u5c42/ })
    .click();
  await expect(page.getByTestId('approval-config-step-knowledge_file_upload-1')).toHaveCount(0);

  await page.getByTestId('approval-config-add-step-knowledge_file_upload').click();
  const secondStepNameInput = page.getByTestId('approval-config-step-name-knowledge_file_upload-1');
  await secondStepNameInput.fill(secondStepName);
  await page.getByTestId('approval-config-member-type-knowledge_file_upload-1-0').selectOption('special_role');
  await expect(page.getByTestId('approval-config-member-role-knowledge_file_upload-1-0')).toContainText(/Direct Manager|直属主管/);

  const saveResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'PUT'
      && response.url().includes('/api/operation-approvals/workflows/knowledge_file_upload')
  );
  await page.getByTestId('approval-config-save-knowledge_file_upload').click();
  await saveResponse;
  await expect(page.getByTestId('approval-config-success')).toContainText(/Approval workflow saved|审批流程已保存/);

  const reloadResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET'
      && response.url().includes('/api/operation-approvals/workflows')
  );
  await page.reload();
  await expect((await reloadResponse).ok()).toBeTruthy();

  await expect(page.getByTestId('approval-config-step-name-knowledge_file_upload-0')).toHaveValue(firstStepName);
  await expect(
    page.getByTestId('approval-config-member-ref-knowledge_file_upload-0-0-selected')
  ).not.toContainText(/No user selected|未选择用户/);
  await expect(page.getByTestId('approval-config-step-name-knowledge_file_upload-1')).toHaveValue(secondStepName);
  await expect(page.getByTestId('approval-config-member-role-knowledge_file_upload-1-0')).toContainText(/Direct Manager|直属主管/);
});

