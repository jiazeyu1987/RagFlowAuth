// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('nas browser: files loading failure branch @regression @tools @nas', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: '展厅聊天' }] }),
    });
  });

  await page.route('**/api/nas/files**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'nas_files_failed_test' }),
    });
  });

  await page.goto('/tools/nas-browser');
  await expect(page.getByText('nas_files_failed_test')).toBeVisible();
});

adminTest('nas browser: dataset loading failure keeps import confirm disabled and cancel closes dialog @regression @tools @nas', async ({ page }) => {
  let importFileCalls = 0;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'datasets_failed_test' }),
    });
  });

  await page.route('**/api/nas/files**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        current_path: '',
        parent_path: null,
        items: [{ name: 'guidewire.txt', path: 'guidewire.txt', is_dir: false, size: 100, modified_at: 1700000000 }],
      }),
    });
  });

  await page.route('**/api/nas/import-file', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    importFileCalls += 1;
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ imported_count: 1, skipped_count: 0, failed_count: 0 }) });
  });

  await page.goto('/tools/nas-browser');
  await page.getByTestId('nas-import-btn-guidewire_txt').click();

  await expect(page.getByTestId('nas-import-dialog')).toBeVisible();
  await expect(page.getByTestId('nas-import-confirm')).toBeDisabled();
  await page.getByTestId('nas-import-cancel').click();
  await expect(page.getByTestId('nas-import-dialog')).toHaveCount(0);
  expect(importFileCalls).toBe(0);
});
