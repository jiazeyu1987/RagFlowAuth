// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test, expect, request } = require('@playwright/test');
const { BACKEND_BASE_URL, FRONTEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

async function ensureDatasetsAvailable(tokens) {
  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  try {
    const datasetsResp = await api.get('/api/datasets', { headers: { Authorization: `Bearer ${tokens.access_token}` } });
    if (!datasetsResp.ok()) return { ok: false, reason: 'GET /api/datasets failed; ragflow may be unavailable' };
    const payload = await datasetsResp.json();
    const datasets = payload?.datasets || [];
    if (!Array.isArray(datasets) || datasets.length === 0) return { ok: false, reason: 'no datasets available for this user' };
    return { ok: true };
  } finally {
    await api.dispose();
  }
}

test('documents conflict -> close modal keeps pending (real backend) @integration', async ({ page }) => {
  test.setTimeout(180_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const ds = await ensureDatasetsAvailable(pre.tokens);
  if (!ds.ok) test.skip(true, ds.reason);

  let approveOverwriteSeen = false;
  page.on('request', (req) => {
    if (req.url().includes('/api/knowledge/documents/') && req.url().includes('/approve-overwrite')) approveOverwriteSeen = true;
  });

  await uiLogin(page);

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ragflowauth-e2e-'));
  const filename = `conflict_${Date.now()}_${Math.random().toString(16).slice(2, 8)}.txt`;
  const filePath = path.join(tmpDir, filename);

  try {
    // Upload #1 (old doc) and approve it.
    fs.writeFileSync(filePath, `old ${filename}\n`, 'utf8');
    await page.goto(`${FRONTEND_BASE_URL}/upload`);
    await page.getByTestId('upload-file-input').setInputFiles(filePath);
    await page.getByTestId('upload-submit').click();
    await expect(page).toHaveURL(/\/documents/, { timeout: 30_000 });

    const oldRow = page.locator('tr', { hasText: filename });
    await expect(oldRow).toBeVisible({ timeout: 30_000 });

    page.once('dialog', async (dialog) => dialog.accept());
    const [approveResp] = await Promise.all([
      page.waitForResponse(
        (r) => /\/api\/knowledge\/documents\/[^/]+\/approve$/.test(r.url()) && r.request().method() === 'POST',
        { timeout: 120_000 },
      ),
      oldRow.locator('[data-testid^="docs-approve-"]').first().click(),
    ]);
    expect(approveResp.ok()).toBeTruthy();
    await expect(page.locator('tr', { hasText: filename })).toHaveCount(0, { timeout: 60_000 });

    // Upload #2 triggers conflict modal.
    fs.writeFileSync(filePath, `new ${filename}\n`, 'utf8');
    await page.goto(`${FRONTEND_BASE_URL}/upload`);
    await page.getByTestId('upload-file-input').setInputFiles(filePath);
    await page.getByTestId('upload-submit').click();
    await expect(page).toHaveURL(/\/documents/, { timeout: 30_000 });

    const newRow = page.locator('tr', { hasText: filename });
    await expect(newRow).toBeVisible({ timeout: 30_000 });

    await newRow.locator('[data-testid^="docs-approve-"]').first().click();
    await expect(page.getByTestId('docs-overwrite-modal')).toBeVisible({ timeout: 30_000 });

    await page.getByTestId('docs-overwrite-close').click();
    await expect(page.getByTestId('docs-overwrite-modal')).toHaveCount(0, { timeout: 30_000 });

    // Should remain pending; no overwrite request should be sent.
    await expect(newRow).toBeVisible({ timeout: 30_000 });
    await page.waitForTimeout(1500);
    expect(approveOverwriteSeen).toBeFalsy();
  } finally {
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // ignore
    }
  }
});

