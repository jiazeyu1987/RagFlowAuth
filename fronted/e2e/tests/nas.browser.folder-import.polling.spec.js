// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('nas browser folder import polling: reaches completed state @regression @tools @nas', async ({ page }) => {
  let importFolderBody = null;
  let statusPollCount = 0;

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
            name: 'folderA',
            path: 'folderA',
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
        task_id: 'task_folder_1',
        status: 'pending',
        folder_path: 'folderA',
        kb_ref: '展厅聊天',
        total_files: 2,
        processed_files: 0,
        progress_percent: 0,
        imported_count: 0,
        skipped_count: 0,
        failed_count: 0,
      }),
    });
  });

  await page.route('**/api/nas/import-folder/task_folder_1', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    statusPollCount += 1;

    if (statusPollCount < 2) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'task_folder_1',
          status: 'running',
          folder_path: 'folderA',
          kb_ref: '展厅聊天',
          total_files: 2,
          processed_files: 1,
          progress_percent: 50,
          imported_count: 1,
          skipped_count: 0,
          failed_count: 0,
          current_file: 'folderA/doc1.pdf',
        }),
      });
    }

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task_folder_1',
        status: 'completed',
        folder_path: 'folderA',
        kb_ref: '展厅聊天',
        total_files: 2,
        processed_files: 2,
        progress_percent: 100,
        imported_count: 2,
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

  await page.getByTestId('nas-import-btn-folderA').click();
  await expect(page.getByTestId('nas-import-dialog')).toBeVisible();
  await expect(page.getByTestId('nas-import-kb-select')).toHaveValue('展厅聊天');

  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/nas/import-folder' && resp.request().method() === 'POST'),
    page.getByTestId('nas-import-confirm').click(),
  ]);

  expect(importFolderBody).toEqual({ path: 'folderA', kb_ref: '展厅聊天' });

  await expect.poll(() => statusPollCount, { timeout: 20_000 }).toBeGreaterThan(1);
  await expect(page.getByText('folderA').first()).toBeVisible();
  await expect(page.getByText('completed')).toBeVisible();

  await expect
    .poll(
      async () => page.evaluate(() => window.localStorage.getItem('nas_active_folder_import_task')),
      { timeout: 10_000 }
    )
    .toBe(null);
});
