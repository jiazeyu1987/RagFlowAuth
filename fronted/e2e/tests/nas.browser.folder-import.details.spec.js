// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('nas folder import completed details: skipped and failed entries rendered @regression @tools @nas', async ({ page }) => {
  let importFolderBody = null;

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
            name: 'folderB',
            path: 'folderB',
            is_dir: true,
            size: 0,
            modified_at: 1700000000,
          },
        ],
      }),
    });
  });

  await page.route('**/api/nas/import-folder', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    importFolderBody = route.request().postDataJSON();

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task_folder_details_1',
        status: 'completed',
        folder_path: 'folderB',
        kb_ref: '展厅聊天',
        total_files: 4,
        processed_files: 4,
        progress_percent: 100,
        imported_count: 2,
        skipped_count: 1,
        failed_count: 1,
        skipped: [
          {
            path: 'folderB/skip.exe',
            reason: 'unsupported_extension',
            detail: '.exe',
          },
        ],
        failed: [
          {
            path: 'folderB/fail.pdf',
            reason: 'ingestion_failed',
            detail: 'disk full',
          },
        ],
      }),
    });
  });

  page.on('dialog', async (dialog) => {
    await dialog.accept();
  });

  await page.goto('/tools/nas-browser');
  await expect(page.getByTestId('nas-browser-page')).toBeVisible();

  await page.getByTestId('nas-import-btn-folderB').click();
  await expect(page.getByTestId('nas-import-dialog')).toBeVisible();

  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/nas/import-folder' && resp.request().method() === 'POST'),
    page.getByTestId('nas-import-confirm').click(),
  ]);

  expect(importFolderBody).toEqual({ path: 'folderB', kb_ref: '展厅聊天' });

  await expect(page.getByText('folderB/skip.exe')).toBeVisible();
  await expect(page.getByText('folderB/fail.pdf')).toBeVisible();
  await expect(page.getByText('Unsupported extension (.exe)')).toBeVisible();
  await expect(page.getByText('Ingestion failed (disk full)')).toBeVisible();

  await expect
    .poll(
      async () => page.evaluate(() => window.localStorage.getItem('nas_active_folder_import_task')),
      { timeout: 10_000 }
    )
    .toBe(null);
});
