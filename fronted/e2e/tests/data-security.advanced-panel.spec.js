// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('data security advanced settings are gated by query flag @regression @admin', async ({ page }) => {
  await page.route('**/api/admin/data-security/settings', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        target_mode: 'share',
        target_local_dir: '',
        target_ip: '192.168.1.10',
        target_share_name: 'backup',
        target_subdir: 'ragflowauth',
        ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
        ragflow_stop_services: false,
        full_backup_include_images: false,
        auth_db_path: 'data/auth.db',
        last_run_at_ms: null,
        backup_retention_max: 30,
        backup_target_path: '',
        backup_pack_count: 0,
      }),
    });
  });

  await page.route('**/api/admin/data-security/backup/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.goto('/data-security');
  await expect(page.getByTestId('data-security-page')).toBeVisible();
  await expect(page.getByTestId('ds-target-mode')).toHaveCount(0);

  await page.goto('/data-security?advanced=1');
  await expect(page.getByTestId('data-security-page')).toBeVisible();
  await expect(page.getByTestId('ds-enabled')).toBeVisible();
  await expect(page.getByTestId('ds-target-mode')).toBeVisible();
  await expect(page.getByTestId('ds-ragflow-compose-path')).toBeVisible();
});
