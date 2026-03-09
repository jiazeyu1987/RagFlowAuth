// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('nas browser basic: list and import one file @regression @tools @nas', async ({ page }) => {
  let importFileBody = null;

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb_showroom', name: '展厅聊天' }] }),
    });
  });

  await page.route('**/api/nas/files**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        current_path: '',
        parent_path: null,
        items: [
          {
            name: 'guidewire.txt',
            path: 'docs/guidewire.txt',
            is_dir: false,
            size: 512,
            modified_at: 1700000000,
          },
        ],
      }),
    });
  });

  await page.route('**/api/nas/import-file', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    importFileBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        imported_count: 1,
        skipped_count: 0,
        failed_count: 0,
        skipped: [],
        failed: [],
      }),
    });
  });

  page.on('dialog', async (dialog) => {
    await dialog.accept();
  });

  await page.goto('/tools/nas-browser');

  await expect(page.getByTestId('nas-browser-page')).toBeVisible();
  await expect(page.getByText('guidewire.txt')).toBeVisible();

  await page.getByTestId('nas-import-btn-docs_guidewire_txt').click();
  await expect(page.getByTestId('nas-import-dialog')).toBeVisible();
  await expect(page.getByTestId('nas-import-kb-select')).toHaveValue('展厅聊天');

  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/nas/import-file') && resp.request().method() === 'POST'),
    page.getByTestId('nas-import-confirm').click(),
  ]);

  expect(importFileBody).toEqual({ path: 'docs/guidewire.txt', kb_ref: '展厅聊天' });
  await expect(page.getByTestId('nas-import-dialog')).toHaveCount(0);
});
