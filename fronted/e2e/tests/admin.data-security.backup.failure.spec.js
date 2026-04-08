// @ts-check
const { expect } = require('@playwright/test');
const { realAdminTest, mockAuthMe } = require('../helpers/auth');

realAdminTest('data security run backup completes from server local backup only @regression @admin', async ({ page }) => {
  await mockAuthMe(page);

  const settings = {
    enabled: false,
    interval_minutes: 60,
    ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
    ragflow_stop_services: false,
    full_backup_include_images: true,
    auth_db_path: 'data/auth.db',
    last_run_at_ms: null,
    local_backup_target_path: '/app/data/backups',
    local_backup_pack_count: 1,
  };

  const jobs = [];
  let jobGetCount = 0;

  await page.route('**/api/admin/data-security/settings', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    if (method === 'PUT') {
      const body = route.request().postDataJSON();
      Object.assign(settings, body);
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    return route.fallback();
  });

  await page.route('**/api/admin/data-security/backup/run', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    jobs.unshift({
      id: 2,
      status: 'queued',
      progress: 0,
      message: 'queued',
      created_at_ms: Date.now(),
      started_at_ms: Date.now(),
      output_dir: '',
      detail: null,
    });
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ job_id: 2 }) });
  });

  await page.route('**/api/admin/data-security/backup/jobs?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs }) });
  });

  await page.route('**/api/admin/data-security/restore-drills**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], count: 0 }) });
  });

  await page.route('**/api/admin/data-security/backup/jobs/2', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    jobGetCount += 1;
    const job = jobs[0];
    if (jobGetCount === 1) {
      Object.assign(job, { status: 'running', progress: 10, message: 'running' });
    } else {
      Object.assign(job, {
        status: 'completed',
        progress: 100,
        message: 'backup_completed_local',
        detail: null,
        output_dir: '/app/data/backups/migration_pack_20260404_010101',
      });
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(job) });
  });

  await page.goto('/data-security');
  await page.getByTestId('ds-run-now').click();

  await expect(page.getByTestId('ds-active-job-status')).toContainText('#2');
  await expect(page.getByTestId('ds-active-job-message')).toContainText('backup_completed_local', { timeout: 20_000 });
  await expect(page.getByTestId('ds-active-job')).toContainText('/app/data/backups/migration_pack_20260404_010101');
  await expect(page.getByTestId('ds-active-job-status')).toContainText('completed');
  await expect(page.getByTestId('ds-job-row-2')).toContainText('服务器本机备份: 成功');
  await expect(page.getByTestId('data-security-page')).not.toContainText('Windows');

  await expect(page.getByTestId('ds-run-now')).toBeEnabled();
});
