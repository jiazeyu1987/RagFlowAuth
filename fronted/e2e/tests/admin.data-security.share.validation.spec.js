// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('data security run backup displays backend validation error @regression @admin', async ({ page }) => {
  await page.route('**/api/admin/data-security/settings', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        target_mode: 'share',
        target_local_dir: '',
        target_ip: '',
        target_share_name: '',
        target_subdir: '',
        ragflow_compose_path: '',
        ragflow_stop_services: false,
        full_backup_include_images: true,
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
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.route('**/api/admin/data-security/backup/run', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 400,
      contentType: 'application/json',
      body: JSON.stringify({ detail: '请先填写\"目标电脑 IP\"和\"共享名\"，再点击\"立即备份\"。' }),
    });
  });

  await page.goto('/data-security');
  await page.getByTestId('ds-run-now').click();
  await expect(page.getByTestId('ds-error')).toContainText('目标电脑 IP');
});
