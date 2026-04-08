// @ts-check
const { expect } = require('@playwright/test');
const { realAdminTest, mockAuthMe } = require('../helpers/auth');

realAdminTest('data security advanced settings are gated by query flag @regression @admin', async ({ page }) => {
  await mockAuthMe(page);

  await page.route('**/api/admin/data-security/settings', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        enabled: false,
        ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
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
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.route('**/api/admin/data-security/restore-drills**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], count: 0 }) });
  });

  await page.goto('/data-security');
  await expect(page.getByTestId('data-security-page')).toBeVisible();
  await expect(page.getByTestId('ds-enabled')).toHaveCount(0);
  await expect(page.getByTestId('ds-settings-save')).toHaveCount(0);

  await page.goto('/data-security?advanced=1');
  await expect(page.getByTestId('data-security-page')).toBeVisible();
  await expect(page.getByTestId('ds-enabled')).toBeVisible();
  await expect(page.getByTestId('ds-ragflow-compose-path')).toBeVisible();
  await expect(page.getByTestId('ds-settings-save')).toBeVisible();
});
