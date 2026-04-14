// @ts-check
const { expect } = require('@playwright/test');
const { docAdminTest, docViewerTest } = require('../helpers/docAuth');

docAdminTest('质量体系批记录入口可访问并完成基础数据加载 @doc-e2e', async ({ page }) => {
  const templatesResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET'
      && response.url().includes('/api/quality-system/batch-records/templates')
  );
  const executionsResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET'
      && response.url().includes('/api/quality-system/batch-records/executions')
  );

  await page.goto('/quality-system/batch-records');

  await expect(page.getByTestId('quality-system-batch-records-page')).toBeVisible();
  await expect(page.getByTestId('batch-records-templates')).toBeVisible();
  await expect(page.getByTestId('batch-records-executions')).toBeVisible();
  await expect(page.getByTestId('batch-records-detail')).toBeVisible();

  const [templatesRes, executionsRes] = await Promise.all([templatesResponse, executionsResponse]);
  await expect(templatesRes.ok()).toBeTruthy();
  await expect(executionsRes.ok()).toBeTruthy();
});

docViewerTest('无质量权限账号无法访问批记录工作区 @doc-e2e', async ({ page }) => {
  await page.goto('/quality-system/batch-records');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});
