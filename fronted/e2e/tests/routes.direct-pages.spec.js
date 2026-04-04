// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('change password route direct load renders form @regression @auth', async ({ page }) => {
  await page.goto('/change-password');
  await expect(page).toHaveURL(/\/change-password$/);
  await expect(page.getByTestId('change-password-old')).toBeVisible();
  await expect(page.getByTestId('change-password-new')).toBeVisible();
  await expect(page.getByTestId('change-password-confirm')).toBeVisible();
  await expect(page.getByTestId('change-password-submit')).toBeVisible();
});

adminTest('documents review direct route renders page @regression @documents', async ({ page }) => {
  await page.route('**/api/datasets**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'kb1', name: 'KB 1' }], count: 1 }),
    });
  });

  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [], count: 0 }),
    });
  });

  await page.goto('/documents/review');
  await expect(page).toHaveURL(/\/documents\/review$/);
  await expect(page.getByTestId('document-review-page')).toBeVisible();
});

adminTest('documents audit direct route renders page @regression @audit', async ({ page }) => {
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/knowledge/documents**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [] }) });
  });
  await page.route('**/api/knowledge/deletions**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ deletions: [] }) });
  });
  await page.route('**/api/ragflow/downloads**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ downloads: [] }) });
  });

  await page.goto('/documents/audit');
  await expect(page).toHaveURL(/\/documents\/audit$/);
  await expect(page.getByTestId('audit-page')).toBeVisible();
});

adminTest('data security test direct route renders page @regression @admin', async ({ page }) => {
  await page.route('**/api/admin/data-security/settings', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        enabled: false,
        interval_minutes: 60,
        target_mode: 'local',
        target_local_dir: 'D:\\\\backup\\\\ragflowauth',
        target_ip: '',
        target_share_name: '',
        target_subdir: '',
        ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
        ragflow_stop_services: false,
        full_backup_include_images: false,
        auth_db_path: 'data/auth.db',
        last_run_at_ms: null,
        local_backup_target_path: '/app/data/backups',
        local_backup_pack_count: 0,
        windows_backup_target_path: 'D:\\\\backup\\\\ragflowauth',
        windows_backup_pack_count: 0,
      }),
    });
  });
  await page.route('**/api/admin/data-security/backup/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.goto('/data-security-test');
  await expect(page).toHaveURL(/\/data-security-test$/);
  await expect(page.getByTestId('data-security-test-page')).toBeVisible();
});
