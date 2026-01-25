// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('data security run backup shows failure details and stops running @regression @admin', async ({ page }) => {
  const settings = {
    enabled: false,
    interval_minutes: 60,
    target_mode: 'local',
    target_local_dir: 'D:\\\\backup\\\\ragflowauth',
    target_ip: '',
    target_share_name: '',
    target_subdir: '',
    ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
    ragflow_stop_services: false,
    full_backup_include_images: true,
    auth_db_path: 'data/auth.db',
    last_run_at_ms: null,
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

  await page.route('**/api/admin/data-security/backup/jobs/2', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    jobGetCount += 1;
    const j = jobs[0];
    if (jobGetCount === 1) {
      Object.assign(j, { status: 'running', progress: 10, message: 'running' });
    } else {
      Object.assign(j, { status: 'failed', progress: 35, message: 'failed', detail: 'disk full' });
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(j) });
  });

  await page.goto('/data-security');
  await page.getByTestId('ds-run-now').click();

  await expect(page.getByTestId('ds-active-job-status')).toContainText('#2');
  await expect(page.getByTestId('ds-active-job-detail')).toHaveText('disk full', { timeout: 20_000 });
  await expect(page.getByTestId('ds-active-job-status')).toContainText('failed');

  // Should stop running after failure, allowing another run attempt.
  await expect(page.getByTestId('ds-run-now')).toBeEnabled();
});

