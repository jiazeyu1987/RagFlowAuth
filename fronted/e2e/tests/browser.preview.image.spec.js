// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('document browser previews an image (mock) @regression @browser', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: '灞曞巺' }], count: 1 }),
    });
  });

  await page.route('**/api/ragflow/documents?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [{ id: 'doc1', name: 'pic.png', status: 'ok' }], count: 1 }),
    });
  });

  // 1x1 transparent PNG
  const pngBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6n0n0AAAAASUVORK5CYII=';

  await page.route('**/api/preview/documents/ragflow/doc1/preview?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'image', filename: 'pic.png', image_type: 'png', content: pngBase64 }),
    });
  });

  await page.goto('/browser');
  await page.getByTestId('browser-dataset-toggle-ds1').click();
  await expect(page.getByTestId('browser-doc-row-ds1-doc1')).toBeVisible();

  await page.getByTestId('browser-doc-view-ds1-doc1').click();
  await expect(page.getByTestId('document-preview-modal')).toBeVisible();
  await expect(page.getByTestId('document-preview-modal').getByText('pic.png', { exact: false })).toBeVisible();
  await expect(page.locator('img[alt=\"pic.png\"]')).toBeVisible();
});
