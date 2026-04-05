// @ts-check
const path = require('node:path');
const { expect, test } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { openSessionPage } = require('../helpers/docSessionPage');
const { FRONTEND_BASE_URL } = require('../helpers/docRealFlow');
const {
  disposeSession,
  getDataSecurityJob,
  listRestoreDrills,
  loginApiAs,
  updateDataSecuritySettings,
  waitForDataSecurityJobTerminal,
} = require('../helpers/securityToolsFlow');

const summary = loadBootstrapSummary();
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const adminUsername = process.env.E2E_ADMIN_USER || summary?.users?.admin?.username;
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
const isolatedDbPath = process.env.E2E_TEST_DB_PATH || path.join(REPO_ROOT, 'data', 'e2e', 'worker05_doc_auth.db');
const composePath = path.join(REPO_ROOT, 'docker', 'docker-compose.yml');
const workerLocalTarget = path.join(REPO_ROOT, 'data', 'e2e', 'worker05_backup_target');

test('Data security uses real retention save and real backup execution or fail-fast blocker @doc-e2e', async ({ browser }) => {
  test.setTimeout(600_000);

  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let adminUi = null;

  try {
    adminSession = await loginApiAs(adminUsername, adminPassword);
    await updateDataSecuritySettings(adminSession.api, adminSession.headers, {
      target_mode: 'local',
      target_local_dir: workerLocalTarget,
      ragflow_compose_path: composePath,
      auth_db_path: isolatedDbPath,
    }, {
      changeReason: 'worker-05 isolated real data-security preflight',
    });

    adminUi = await openSessionPage(browser, adminSession);
    const page = adminUi.page;
    await page.goto(`${FRONTEND_BASE_URL}/data-security`);
    await expect(page.getByTestId('data-security-page')).toBeVisible();

    const retentionInput = page.locator('input[type="number"]').first();
    const currentRetention = Number(await retentionInput.inputValue());
    const nextRetention = String(Math.max(1, Math.min(100, Number.isFinite(currentRetention) ? currentRetention + 1 : 31)));
    page.once('dialog', (dialog) => dialog.accept('worker-05 retention save'));
    const retentionResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes('/api/admin/data-security/settings')
    ));
    await retentionInput.fill(nextRetention);
    await page.getByTestId('ds-retention-save').click();
    await expect((await retentionResponsePromise).ok()).toBeTruthy();
    await expect(retentionInput).toHaveValue(nextRetention);

    const runResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes('/api/admin/data-security/backup/run')
    ));
    await page.getByTestId('ds-run-now').click();
    const runResponse = await runResponsePromise;

    if (runResponse.status() === 400) {
      const runBody = await runResponse.json();
      const detail = String(runBody?.detail || '').trim();
      expect(detail).toBeTruthy();
      await expect(page.getByTestId('ds-error')).toContainText(detail);

      const runFullResponsePromise = page.waitForResponse((response) => (
        response.request().method() === 'POST'
        && response.url().includes('/api/admin/data-security/backup/run-full')
      ));
      await page.getByTestId('ds-run-full').click();
      const runFullResponse = await runFullResponsePromise;
      expect(runFullResponse.status()).toBe(400);
      const runFullBody = await runFullResponse.json();
      await expect(page.getByTestId('ds-error')).toContainText(String(runFullBody?.detail || '').trim());
      return;
    }

    await expect(runResponse.ok()).toBeTruthy();
    const runBody = await runResponse.json();
    const jobId = Number(runBody?.job_id || 0);
    expect(jobId).toBeGreaterThan(0);

    await expect(page.getByTestId('ds-active-job-status')).toContainText(`#${jobId}`);
    const settledJob = await waitForDataSecurityJobTerminal(adminSession.api, adminSession.headers, jobId);
    await expect.poll(async () => {
      const job = await getDataSecurityJob(adminSession.api, adminSession.headers, jobId);
      return String(job?.status || '');
    }).toBe(String(settledJob.status || ''));
    await expect(page.getByTestId(`ds-job-row-${jobId}`)).toBeVisible({ timeout: 30_000 });

    expect(String(settledJob.status || '')).toBe('completed');
    expect(String(settledJob.output_dir || '')).toBeTruthy();
    expect(String(settledJob.package_hash || '')).toBeTruthy();

    const beforeDrills = await listRestoreDrills(adminSession.api, adminSession.headers, 30);
    const restoreResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes('/api/admin/data-security/restore-drills')
    ));
    await page.selectOption('[data-testid="ds-restore-job-select"]', String(jobId));
    await page.getByTestId('ds-restore-target').fill(`worker05_restore_${Date.now()}`);
    await page.getByTestId('ds-restore-notes').fill('worker-05 real restore drill');
    await page.getByTestId('ds-restore-submit').click();
    const restoreResponse = await restoreResponsePromise;
    await expect(restoreResponse.ok()).toBeTruthy();
    const restoreBody = await restoreResponse.json();
    const drillId = String(restoreBody?.drill_id || '').trim();
    expect(drillId).toBeTruthy();
    await expect(page.getByTestId(`ds-restore-row-${drillId}`)).toBeVisible({ timeout: 30_000 });

    const afterDrills = await listRestoreDrills(adminSession.api, adminSession.headers, 30);
    expect(afterDrills.length).toBeGreaterThanOrEqual(beforeDrills.length + 1);
  } finally {
    if (adminUi) {
      await adminUi.context.close().catch(() => {});
    }
    await disposeSession(adminSession);
  }
});
