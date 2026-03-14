// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('document browser shows unsupported preview message (mock) @regression @browser', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: 'demo-ds' }], count: 1 }),
    });
  });

  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [{ id: 'doc1', name: 'archive.bin', status: 'ok' }], count: 1 }),
    });
  });

  await page.route('**/api/preview/documents/ragflow/doc1/preview?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'unsupported', filename: 'archive.bin', message: 'unsupported preview' }),
    });
  });

  await page.goto('/browser');
  await page.getByTestId('browser-dataset-toggle-ds1').click();
  await expect(page.getByTestId('browser-doc-row-ds1-doc1')).toBeVisible();

  const viewBtn = page.getByTestId('browser-doc-view-ds1-doc1');
  await expect(viewBtn).toBeDisabled();
  await expect(viewBtn).toHaveAttribute('title', /不支持在线预览|preview/i);
});
