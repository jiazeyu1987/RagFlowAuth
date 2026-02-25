// @ts-check
const path = require('node:path');
const { expect } = require('@playwright/test');
const { adminTest, viewerTest } = require('../helpers/auth');

adminTest('upload shows error when no datasets available (mock) @regression @upload', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [], count: 0 }) });
  });

  await page.goto('/upload');
  await expect(page.getByTestId('upload-error')).toBeVisible();
});

adminTest('upload shows error when backend upload fails (mock) @regression @upload', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: 'kb-one' }], count: 1 }),
    });
  });

  await page.route('**/api/documents/knowledge/upload?*', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'upload failed' }) });
  });

  await page.goto('/upload');

  const projectRoot = path.resolve(__dirname, '..', '..');
  const filePath = path.join(projectRoot, 'e2e', 'fixtures', 'files', 'hello.txt');
  await page.getByTestId('upload-file-input').setInputFiles(filePath);
  await page.getByTestId('upload-submit').click();

  await expect(page.getByTestId('upload-error')).toBeVisible();
  await expect(page.getByTestId('upload-error')).toContainText(/upload failed/i);
  await expect(page).toHaveURL(/\/upload/);
});

viewerTest('upload for viewer shows no-datasets message (mock) @regression @upload', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [], count: 0 }) });
  });

  await page.goto('/upload');
  await expect(page.getByTestId('upload-error')).toBeVisible();
});
