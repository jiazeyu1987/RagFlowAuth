// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('document browser loads and previews a text file @regression', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        datasets: [{ id: 'ds1', name: '展厅' }],
        count: 1,
      }),
    });
  });

  await page.route('**/api/ragflow/documents?*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        documents: [{ id: 'doc1', name: 'readme.txt', status: 'ok' }],
        count: 1,
      }),
    });
  });

  await page.route('**/api/ragflow/documents/doc1/download?*', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
      body: 'hello from ragflow preview',
    });
  });

  await page.goto('/browser');
  await page.getByText('展厅', { exact: true }).click();
  await expect(page.getByText('readme.txt', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: '查看' }).click();
  await expect(page.getByRole('heading', { name: 'readme.txt' })).toBeVisible();
  await expect(page.getByText('hello from ragflow preview')).toBeVisible();
});
