// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('nas folder import failed status shows error @regression @tools @nas', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [{ id: 'kb1', name: '展厅聊天' }] }) });
  });

  await page.route('**/api/nas/files**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        current_path: '',
        parent_path: null,
        items: [{ name: 'folder_fail', path: 'folder_fail', is_dir: true, size: 0, modified_at: 1700000000 }],
      }),
    });
  });

  await page.route('**/api/nas/import-folder', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task_fail_1',
        status: 'pending',
        folder_path: 'folder_fail',
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

  await page.route('**/api/tasks/task_fail_1**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task_fail_1',
        status: 'failed',
        folder_path: 'folder_fail',
        kb_ref: '展厅聊天',
        total_files: 2,
        processed_files: 1,
        progress_percent: 50,
        imported_count: 1,
        skipped_count: 0,
        failed_count: 1,
        error: 'folder_import_failed_test',
      }),
    });
  });

  await page.goto('/tools/nas-browser');

  await page.getByTestId('nas-import-btn-folder_fail').click();
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/tasks/task_fail_1' && resp.request().method() === 'GET'),
    page.getByTestId('nas-import-confirm').click(),
  ]);

  await expect(page.getByText('folder_import_failed_test').first()).toBeVisible();
});

adminTest('nas import-file failure shows error @regression @tools @nas', async ({ page }) => {
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [{ id: 'kb1', name: '展厅聊天' }] }) });
  });

  await page.route('**/api/nas/files**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        current_path: '',
        parent_path: null,
        items: [{ name: 'file_fail.txt', path: 'file_fail.txt', is_dir: false, size: 100, modified_at: 1700000000 }],
      }),
    });
  });

  await page.route('**/api/nas/import-file', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'import_file_failed_test' }) });
  });

  await page.goto('/tools/nas-browser');

  await page.getByTestId('nas-import-btn-file_fail_txt').click();
  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/nas/import-file' && resp.request().method() === 'POST'),
    page.getByTestId('nas-import-confirm').click(),
  ]);

  await expect(page.getByText('import_file_failed_test')).toBeVisible();
});

adminTest('nas restore running task from localStorage and clear after completed @regression @tools @nas', async ({ page }) => {
  let pollCount = 0;

  await page.addInitScript(() => {
    window.localStorage.setItem('nas_active_folder_import_task', JSON.stringify({ taskId: 'task_restore_1' }));
  });

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [{ id: 'kb1', name: '展厅聊天' }] }) });
  });

  await page.route('**/api/nas/files**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ current_path: '', parent_path: null, items: [] }) });
  });

  await page.route('**/api/tasks/task_restore_1**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    pollCount += 1;

    if (pollCount === 1) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'task_restore_1',
          status: 'running',
          folder_path: 'restore_folder',
          kb_ref: '展厅聊天',
          total_files: 3,
          processed_files: 1,
          progress_percent: 33,
          imported_count: 1,
          skipped_count: 0,
          failed_count: 0,
        }),
      });
    }

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: 'task_restore_1',
        status: 'completed',
        folder_path: 'restore_folder',
        kb_ref: '展厅聊天',
        total_files: 3,
        processed_files: 3,
        progress_percent: 100,
        imported_count: 3,
        skipped_count: 0,
        failed_count: 0,
        skipped: [],
        failed: [],
      }),
    });
  });

  await page.goto('/tools/nas-browser');

  await expect.poll(() => pollCount, { timeout: 20_000 }).toBeGreaterThan(1);
  await expect(page.getByText('restore_folder')).toBeVisible();

  await expect
    .poll(() => page.evaluate(() => window.localStorage.getItem('nas_active_folder_import_task')), { timeout: 10_000 })
    .toBe(null);
});
