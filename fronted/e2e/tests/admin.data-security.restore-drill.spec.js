// @ts-check
const { expect } = require('@playwright/test');
const { realAdminTest, mockAuthMe } = require('../helpers/auth');

realAdminTest('data security restore drill can be recorded and listed @regression @admin', async ({ page }) => {
  await mockAuthMe(page);

  const settings = {
    enabled: false,
    interval_minutes: 60,
    ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
    ragflow_stop_services: false,
    full_backup_include_images: true,
    auth_db_path: 'data/auth.db',
    last_run_at_ms: null,
    backup_retention_max: 30,
    local_backup_target_path: '/app/data/backups',
    local_backup_pack_count: 1,
  };

  const nowMs = Date.now();
  const jobs = [
    {
      id: 101,
      kind: 'full',
      status: 'completed',
      progress: 100,
      message: 'done',
      detail: null,
      output_dir: '/app/data/backups/migration_pack_20260402',
      package_hash: 'abcd1234hash',
      verified_by: null,
      verified_at_ms: null,
      created_at_ms: nowMs,
      started_at_ms: nowMs - 1000,
      finished_at_ms: nowMs,
    },
    {
      id: 102,
      kind: 'full',
      status: 'completed',
      progress: 100,
      message: 'missing local backup output',
      detail: 'output_dir_missing',
      output_dir: '',
      package_hash: 'missinglocalhash',
      verified_by: null,
      verified_at_ms: null,
      created_at_ms: nowMs - 10_000,
      started_at_ms: nowMs - 11_000,
      finished_at_ms: nowMs - 10_000,
    },
  ];
  const drills = [];
  let createPayload = null;

  await page.route('**/api/admin/data-security/settings', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    if (method === 'PUT') {
      Object.assign(settings, route.request().postDataJSON() || {});
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(settings) });
    }
    return route.fallback();
  });

  await page.route('**/api/admin/data-security/backup/jobs?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ jobs }) });
  });

  await page.route('**/api/admin/data-security/restore-drills?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: drills, count: drills.length }) });
  });

  await page.route('**/api/admin/data-security/restore-drills', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    createPayload = route.request().postDataJSON();
    const created = {
      drill_id: 'restore_drill_e2e_1',
      job_id: createPayload.job_id,
      backup_path: createPayload.backup_path,
      backup_hash: createPayload.backup_hash,
      actual_backup_hash: createPayload.backup_hash,
      hash_match: true,
      restore_target: createPayload.restore_target,
      restored_auth_db_path: '/tmp/restore/auth.db',
      compare_match: true,
      package_validation_status: 'passed',
      acceptance_status: 'passed',
      executed_by: 'u1',
      executed_at_ms: Date.now(),
      result: 'success',
      verification_notes: createPayload.verification_notes,
    };
    drills.unshift(created);
    jobs[0].verified_by = 'u1';
    jobs[0].verified_at_ms = created.executed_at_ms;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created) });
  });

  await page.goto('/data-security');

  await expect(page.getByTestId('ds-restore-job-select')).toBeVisible();
  await expect(page.getByRole('option', { name: /#101/ })).toHaveCount(1);
  await expect(page.getByRole('option', { name: /#102/ })).toHaveCount(0);
  await expect(page.getByTestId('data-security-page')).not.toContainText('Windows');
  await page.getByTestId('ds-restore-target').fill('qa-restore');
  await page.getByTestId('ds-restore-notes').fill('restore verified in qa');
  await page.getByTestId('ds-restore-submit').click();

  expect(createPayload).toBeTruthy();
  expect(createPayload.job_id).toBe(101);
  expect(createPayload.backup_path).toContain('migration_pack_20260402');
  expect(createPayload.backup_hash).toBe('abcd1234hash');
  expect(createPayload.restore_target).toBe('qa-restore');
  expect(createPayload.result).toBeUndefined();

  const row = page.getByTestId('ds-restore-row-restore_drill_e2e_1');
  await expect(row).toBeVisible();
  await expect(row).toContainText('package validation: passed');
  await expect(row).toContainText('acceptance: passed');
  await expect(row).toContainText('hash match: true');
  await expect(row).toContainText('compare match: true');
  await expect(page.getByTestId('ds-job-row-101')).toContainText('验证:');
});
