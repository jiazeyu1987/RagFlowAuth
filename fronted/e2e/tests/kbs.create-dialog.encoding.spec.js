// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('knowledge base create dialog shows readable chinese text @regression @kbs', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        datasets: [{ id: 'ds1', name: 'test-kb' }],
        count: 1,
      }),
    });
  });

  await page.route('**/api/knowledge/directories', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        nodes: [],
        datasets: [{ id: 'ds1', name: 'test-kb', node_id: null, node_path: '/' }],
      }),
    });
  });

  await page.goto('/kbs');
  await page.getByTestId('kbs-create-kb').click();

  await expect(page.getByTestId('create-kb-dialog')).toBeVisible();
  await expect(page.getByTestId('create-kb-dialog-title')).toHaveText('\u65b0\u5efa\u77e5\u8bc6\u5e93');
  await expect(page.getByPlaceholder('\u8f93\u5165\u77e5\u8bc6\u5e93\u540d\u79f0')).toBeVisible();
});
