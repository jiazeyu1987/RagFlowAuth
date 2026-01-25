// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('data security shows validation error when missing local target dir (mock) @regression @admin', async ({ page }) => {
  await page.route('**/api/admin/data-security/settings', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        enabled: false,
        interval_minutes: 60,
        target_mode: 'local',
        target_local_dir: '',
        target_ip: '',
        target_share_name: '',
        target_subdir: '',
        ragflow_compose_path: '',
        ragflow_stop_services: false,
        full_backup_include_images: false,
        auth_db_path: 'data/auth.db',
        last_run_at_ms: null,
      }),
    });
  });

  await page.route('**/api/admin/data-security/backup/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.goto('/data-security');
  await page.getByTestId('ds-run-now').click();
  await expect(page.getByTestId('ds-error')).toHaveText('请先填写"本机目标目录"，再点击"立即备份"。');
});
