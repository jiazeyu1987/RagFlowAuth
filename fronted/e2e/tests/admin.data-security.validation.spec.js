// @ts-check
const { expect } = require('@playwright/test');
const { realAdminTest, mockAuthMe } = require('../helpers/auth');

realAdminTest('data security run-full displays backend validation error (mock) @regression @admin', async ({ page }) => {
  await mockAuthMe(page);

  await page.route('**/api/admin/data-security/settings', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        enabled: false,
        ragflow_compose_path: '',
        ragflow_stop_services: false,
        full_backup_include_images: false,
        auth_db_path: 'data/auth.db',
        last_run_at_ms: null,
        backup_retention_max: 30,
        local_backup_target_path: '/app/data/backups',
        local_backup_pack_count: 0,
      }),
    });
  });

  await page.route('**/api/admin/data-security/backup/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.route('**/api/admin/data-security/restore-drills**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], count: 0 }) });
  });

  await page.route('**/api/admin/data-security/backup/run-full', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'ragflow_compose_path_required' }),
    });
  });

  await page.goto('/data-security');
  await page.getByTestId('ds-run-full').click();
  await expect(page.getByTestId('ds-error')).toContainText('ragflow_compose_path_required');
});
