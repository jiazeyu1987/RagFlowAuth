// @ts-check
const { expect } = require('@playwright/test');
const { docAdminTest } = require('../helpers/docAuth');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');

const summary = loadBootstrapSummary();
const operatorUserId = String(summary?.users?.operator?.user_id || '');

docAdminTest('审批配置文档流程使用真实工作流、成员搜索与保存结果 @doc-e2e', async ({ page }) => {
  await page.goto('/approval-config');

  await expect(page.getByTestId('approval-config-page')).toBeVisible();
  await expect(page.getByTestId('approval-config-operation-select')).toBeVisible();

  const refreshResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET'
      && response.url().includes('/api/operation-approvals/workflows')
  );
  await page.getByRole('button', { name: '刷新' }).click();
  await refreshResponse;

  const operationSelect = page.getByTestId('approval-config-operation-select');
  await operationSelect.selectOption('knowledge_file_upload');

  const workflowNameInput = page.getByTestId('approval-config-name-knowledge_file_upload');
  await workflowNameInput.fill('文档 E2E 上传审批流');
  await expect(workflowNameInput).toHaveValue('文档 E2E 上传审批流');

  const firstStepNameInput = page.getByTestId('approval-config-step-name-knowledge_file_upload-0');
  await firstStepNameInput.fill('资料完整性复核');
  await expect(firstStepNameInput).toHaveValue('资料完整性复核');

  await page.getByTestId('approval-config-add-member-knowledge_file_upload-0').click();
  const memberInput = page.getByTestId('approval-config-member-ref-knowledge_file_upload-0-1-input');
  await memberInput.fill(String(summary?.users?.operator?.username || 'operator'));
  await page.getByTestId(`approval-config-member-ref-knowledge_file_upload-0-1-result-${operatorUserId}`).click();
  await expect(
    page.getByTestId('approval-config-member-ref-knowledge_file_upload-0-1-selected')
  ).not.toContainText('未选择用户');

  const firstMemberRow = page.getByTestId('approval-config-member-knowledge_file_upload-0-0');
  await firstMemberRow.getByRole('button', { name: '删除成员' }).click();
  await expect(page.getByTestId('approval-config-member-knowledge_file_upload-0-0')).toBeVisible();
  await expect(
    page.getByTestId('approval-config-member-ref-knowledge_file_upload-0-0-selected')
  ).not.toContainText('未选择用户');

  await page.getByTestId('approval-config-add-step-knowledge_file_upload').click();
  await expect(page.getByTestId('approval-config-step-knowledge_file_upload-1')).toBeVisible();
  await page
    .getByTestId('approval-config-step-knowledge_file_upload-1')
    .getByRole('button', { name: '删除本层' })
    .click();
  await expect(page.getByTestId('approval-config-step-knowledge_file_upload-1')).toHaveCount(0);

  await page.getByTestId('approval-config-add-step-knowledge_file_upload').click();
  const secondStepNameInput = page.getByTestId('approval-config-step-name-knowledge_file_upload-1');
  await secondStepNameInput.fill('直属主管会签');
  await page.getByTestId('approval-config-member-type-knowledge_file_upload-1-0').selectOption('special_role');
  await expect(page.getByTestId('approval-config-member-role-knowledge_file_upload-1-0')).toContainText('直属主管');

  const saveResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'PUT'
      && response.url().includes('/api/operation-approvals/workflows/knowledge_file_upload')
  );
  await page.getByTestId('approval-config-save-knowledge_file_upload').click();
  await saveResponse;
  await expect(page.getByTestId('approval-config-success')).toContainText('文件上传');

  const reloadResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET'
      && response.url().includes('/api/operation-approvals/workflows')
  );
  await page.getByRole('button', { name: '刷新' }).click();
  await reloadResponse;

  await expect(page.getByTestId('approval-config-step-name-knowledge_file_upload-0')).toHaveValue('资料完整性复核');
  await expect(
    page.getByTestId('approval-config-member-ref-knowledge_file_upload-0-0-selected')
  ).not.toContainText('未选择用户');
  await expect(page.getByTestId('approval-config-step-name-knowledge_file_upload-1')).toHaveValue('直属主管会签');
  await expect(page.getByTestId('approval-config-member-role-knowledge_file_upload-1-0')).toContainText('直属主管');
});
