// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test, expect, request } = require('@playwright/test');

const FRONTEND_BASE_URL = process.env.E2E_FRONTEND_BASE_URL || 'http://localhost:8080';
const BACKEND_BASE_URL = process.env.E2E_BACKEND_BASE_URL || 'http://localhost:8001';
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.E2E_ADMIN_PASS || 'admin123';

async function backendIsReady() {
  try {
    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    const resp = await api.get('/docs');
    await api.dispose();
    return resp.ok();
  } catch {
    return false;
  }
}

test('upload -> reject -> appears in records @integration', async ({ page }) => {
  test.setTimeout(120_000);

  if (!(await backendIsReady())) {
    test.skip(true, `backend not reachable at ${BACKEND_BASE_URL}`);
  }

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const loginResp = await api.post('/api/auth/login', { data: { username: ADMIN_USER, password: ADMIN_PASS } });
  if (!loginResp.ok()) {
    await api.dispose();
    test.skip(true, 'admin login failed; check E2E_ADMIN_USER/E2E_ADMIN_PASS');
  }
  const tokens = await loginResp.json();
  const meResp = await api.get('/api/auth/me', { headers: { Authorization: `Bearer ${tokens.access_token}` } });
  if (!meResp.ok()) {
    await api.dispose();
    test.skip(true, 'GET /api/auth/me failed; backend not ready');
  }

  const datasetsResp = await api.get('/api/datasets', { headers: { Authorization: `Bearer ${tokens.access_token}` } });
  if (!datasetsResp.ok()) {
    await api.dispose();
    test.skip(true, 'GET /api/datasets failed; ragflow may be unavailable');
  }
  const datasetsPayload = await datasetsResp.json();
  const datasets = datasetsPayload.datasets || [];
  if (!Array.isArray(datasets) || datasets.length === 0) {
    await api.dispose();
    test.skip(true, 'no datasets available for this user');
  }
  await api.dispose();

  await page.goto(`${FRONTEND_BASE_URL}/login`);
  await page.getByTestId('login-username').fill(ADMIN_USER);
  await page.getByTestId('login-password').fill(ADMIN_PASS);
  await page.getByTestId('login-submit').click();
  await expect(page).toHaveURL(/\/$/);

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ragflowauth-e2e-'));
  const filename = `e2e_${Date.now()}_${Math.random().toString(16).slice(2, 8)}.txt`;
  const filePath = path.join(tmpDir, filename);
  fs.writeFileSync(filePath, `hello ${filename}\n`, 'utf8');

  try {
    await page.goto(`${FRONTEND_BASE_URL}/upload`);
    // The file input is hidden; Playwright can still set files on it.
    await page.getByTestId('upload-file-input').setInputFiles(filePath);
    await page.getByTestId('upload-submit').click();

    // Upload page auto-navigates to /documents.
    await expect(page).toHaveURL(/\/documents/);

    // Pending list should contain our filename.
    const row = page.locator('tr', { hasText: filename });
    await expect(row).toBeVisible({ timeout: 30_000 });

    // Reject prompts for notes.
    page.once('dialog', async (dialog) => {
      if (dialog.type() === 'prompt') await dialog.accept('e2e reject');
      else await dialog.dismiss();
    });
    await row.getByRole('button', { name: '驳回' }).click();

    // Pending list should no longer show it.
    await expect(page.locator('tr', { hasText: filename })).toHaveCount(0, { timeout: 30_000 });

    // Records tab should include it (documents list includes all statuses).
    await page.goto(`${FRONTEND_BASE_URL}/documents?tab=records`);
    await expect(page.getByText(filename)).toBeVisible({ timeout: 30_000 });
  } finally {
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // ignore
    }
  }
});
