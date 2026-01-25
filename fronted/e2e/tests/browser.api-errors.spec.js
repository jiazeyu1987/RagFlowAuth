// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('browser shows message when no datasets (mock) @regression @browser', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [], count: 0 }) });
  });

  await page.goto('/browser');
  await expect(page.getByTestId('browser-error')).toBeVisible();
  await expect(page.getByText('暂无知识库')).toBeVisible();
});

adminTest('browser datasets 500 shows error banner (mock) @regression @browser', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'datasets failed' }) });
  });

  await page.goto('/browser');
  await expect(page.getByTestId('browser-error')).toBeVisible();
  // authClient.listRagflowDatasets may normalize the message.
  await expect(page.getByTestId('browser-error')).toContainText(/Failed to list datasets|datasets failed/);
});
