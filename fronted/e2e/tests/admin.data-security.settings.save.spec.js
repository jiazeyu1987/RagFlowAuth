// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('data security retention save persists and re-renders @regression @admin', async ({ page }) => {
  const settings = {
    target_mode: 'local',
    target_local_dir: '/mnt/backup/ragflowauth',
    target_ip: '',
    target_share_name: '',
    target_subdir: '',
    ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
    ragflow_stop_services: false,
    full_backup_include_images: true,
    auth_db_path: 'data/auth.db',
    last_run_at_ms: null,
    backup_retention_max: 30,
    backup_target_path: '/mnt/backup/ragflowauth',
    backup_pack_count: 6,
  };

  let capturedPut = null;

  await page.route('**/api/admin/data-security/settings', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    if (method === 'PUT') {
      capturedPut = route.request().postDataJSON();
      Object.assign(settings, capturedPut || {});
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    return route.fallback();
  });

  await page.route('**/api/admin/data-security/backup/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.goto('/data-security');

  const retentionInput = page.getByRole('spinbutton').first();
  await expect(retentionInput).toHaveValue('30');
  await retentionInput.fill('42');
  await page.getByTestId('ds-retention-save').click();

  expect(capturedPut).toBeTruthy();
  expect(capturedPut.backup_retention_max).toBe(42);

  await page.reload();
  await expect(page.getByRole('spinbutton').first()).toHaveValue('42');
});
