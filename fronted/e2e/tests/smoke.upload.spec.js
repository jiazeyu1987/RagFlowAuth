// @ts-check
const path = require('node:path');
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('upload document (mock datasets) @smoke', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds_e2e', name: 'kb-e2e' }], count: 1 }),
    });
  });

  await page.route('**/api/documents/knowledge/upload?*', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ doc_id: 'local_doc_1', filename: 'hello.txt' }),
    });
  });

  await page.goto('/upload');
  await expect(page.getByTestId('layout-user-name')).toBeVisible();

  const projectRoot = path.resolve(__dirname, '..', '..');
  const filePath = path.join(projectRoot, 'e2e', 'fixtures', 'files', 'hello.txt');
  await page.getByTestId('upload-file-input').setInputFiles(filePath);
  await page.getByTestId('upload-submit').click();

  await expect(page).toHaveURL(/\/documents/, { timeout: 15_000 });
});
