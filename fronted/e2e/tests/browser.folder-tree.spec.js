// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('document browser shows folder tree at left and datasets on the right @regression @browser', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        datasets: [{ id: 'ds1', name: '展厅' }],
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
        nodes: [
          { id: 'n1', name: '123', parent_id: null, path: '/123' },
          { id: 'n2', name: '234', parent_id: 'n1', path: '/123/234' },
        ],
        datasets: [{ id: 'ds1', name: '展厅', node_id: 'n2', node_path: '/123/234' }],
      }),
    });
  });

  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [] }),
    });
  });

  await page.goto('/browser');

  await expect(page.getByText('123')).toBeVisible();
  await expect(page.getByTestId('browser-dataset-ds1')).toHaveCount(0);

  await page.getByText('123').click();
  await expect(page.getByText('234')).toBeVisible();
  await expect(page.getByText('当前目录').first()).toBeVisible();
  await expect(page.getByTestId('browser-dataset-ds1')).toHaveCount(0);

  await page.getByText('234').click();
  await expect(page.getByTestId('browser-dataset-ds1')).toBeVisible();
  await expect(page.getByRole('button', { name: '根目录', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: '234', exact: true })).toBeVisible();
});
