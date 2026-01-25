// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('data security settings save persists and re-renders @regression @admin', async ({ page }) => {
  const settings = {
    enabled: false,
    interval_minutes: 60,
    target_mode: 'share',
    target_local_dir: '',
    target_ip: '192.168.1.10',
    target_share_name: 'backup',
    target_subdir: 'ragflowauth',
    ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
    ragflow_stop_services: false,
    full_backup_include_images: true,
    auth_db_path: 'data/auth.db',
    last_run_at_ms: null,
  };

  let capturedPut = null;

  await page.route('**/api/admin/data-security/settings', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    if (method === 'PUT') {
      capturedPut = route.request().postDataJSON();
      Object.assign(settings, capturedPut);
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    return route.fallback();
  });

  await page.route('**/api/admin/data-security/backup/jobs**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs: [] }) });
  });

  await page.goto('/data-security');

  // Modify settings
  await page.getByTestId('ds-enabled').check();
  await page.getByTestId('ds-interval-minutes').fill('120');
  await page.getByTestId('ds-target-mode').selectOption('share');
  await page.getByTestId('ds-target-ip').fill('10.0.0.5');
  await page.getByTestId('ds-target-share-name').fill('share');
  await page.getByTestId('ds-target-subdir').fill('subdir');
  await expect(page.getByTestId('ds-target-preview')).toContainText('\\\\10.0.0.5\\share\\subdir');

  await page.getByTestId('ds-ragflow-compose-path').fill('/app/ragflow_compose/docker-compose.yml');
  await page.getByTestId('ds-ragflow-stop-services').check();
  await page.getByTestId('ds-full-backup-include-images').uncheck();
  await page.getByTestId('ds-auth-db-path').fill('data/auth2.db');

  await page.getByTestId('ds-save').click();

  expect(capturedPut).toBeTruthy();
  expect(capturedPut.enabled).toBe(true);
  expect(capturedPut.interval_minutes).toBe(120);
  expect(capturedPut.target_ip).toBe('10.0.0.5');
  expect(capturedPut.target_share_name).toBe('share');
  expect(capturedPut.target_subdir).toBe('subdir');
  expect(capturedPut.ragflow_stop_services).toBe(true);
  expect(capturedPut.full_backup_include_images).toBe(false);
  expect(capturedPut.auth_db_path).toBe('data/auth2.db');

  // Reload should reflect saved values (GET returns updated settings object).
  await page.reload();
  await expect(page.getByTestId('ds-enabled')).toBeChecked();
  await expect(page.getByTestId('ds-interval-minutes')).toHaveValue('120');
  await expect(page.getByTestId('ds-target-ip')).toHaveValue('10.0.0.5');
  await expect(page.getByTestId('ds-target-share-name')).toHaveValue('share');
  await expect(page.getByTestId('ds-target-subdir')).toHaveValue('subdir');
  await expect(page.getByTestId('ds-target-preview')).toContainText('\\\\10.0.0.5\\share\\subdir');
  await expect(page.getByTestId('ds-ragflow-stop-services')).toBeChecked();
  await expect(page.getByTestId('ds-full-backup-include-images')).not.toBeChecked();
  await expect(page.getByTestId('ds-auth-db-path')).toHaveValue('data/auth2.db');
});

