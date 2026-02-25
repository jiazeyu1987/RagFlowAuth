// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

test('upload -> approve -> visible in browser and previewable (real backend) @integration', async ({ page }) => {
  test.setTimeout(180_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  let dataset = null;
  let localDocId = null;
  let ragflowDocId = null;

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ragflowauth-e2e-'));
  const filename = `e2e_${Date.now()}_${Math.random().toString(16).slice(2, 8)}.txt`;
  const content = `hello ${filename}\n`;
  const filePath = path.join(tmpDir, filename);
  fs.writeFileSync(filePath, content, 'utf8');

  try {
    const datasetsResp = await api.get('/api/datasets', { headers });
    if (!datasetsResp.ok()) test.skip(true, 'GET /api/datasets failed; ragflow may be unavailable');
    const datasetsPayload = await datasetsResp.json();
    const datasets = datasetsPayload.datasets || [];
    if (!Array.isArray(datasets) || datasets.length === 0) test.skip(true, 'no datasets available for this user');
    dataset = datasets[0];

    await uiLogin(page);
    await expect(page).toHaveURL(/\/chat$/);

    await page.goto(`${FRONTEND_BASE_URL}/upload`);
    await page.getByTestId('upload-kb-select').selectOption(String(dataset.name || dataset.id));

    const [uploadResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/documents/knowledge/upload') && r.request().method() === 'POST'),
      (async () => {
        await page.getByTestId('upload-file-input').setInputFiles(filePath);
        await page.getByTestId('upload-submit').click();
      })(),
    ]);

    const uploaded = await uploadResp.json();
    localDocId = uploaded?.doc_id || null;
    if (!localDocId) test.fail(true, 'upload did not return doc_id');

    await expect(page).toHaveURL(/\/documents/);

    page.once('dialog', async (dialog) => {
      if (dialog.type() === 'confirm') await dialog.accept();
      else await dialog.dismiss();
    });

    const [approveResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes(`/api/knowledge/documents/${localDocId}/approve`) && r.request().method() === 'POST'),
      page.getByTestId(`docs-approve-${localDocId}`).click(),
    ]);

    const approved = await approveResp.json();
    ragflowDocId = approved?.ragflow_doc_id || null;
    if (!ragflowDocId) test.fail(true, 'approve did not return ragflow_doc_id');

    await expect(page.locator('tr', { hasText: filename })).toHaveCount(0, { timeout: 30_000 });

    await page.goto(`${FRONTEND_BASE_URL}/browser`);
    await page.getByTestId(`browser-dataset-toggle-${dataset.id}`).click();

    const rowId = `browser-doc-row-${dataset.id}-${ragflowDocId}`;
    for (let attempt = 0; attempt < 12; attempt++) {
      if (await page.getByTestId(rowId).count()) break;
      await page.getByTestId('browser-refresh-all').click();
      await page.waitForTimeout(2_000);
      await page.getByTestId(`browser-dataset-toggle-${dataset.id}`).click();
    }

    await expect(page.getByTestId(rowId)).toBeVisible({ timeout: 30_000 });

    await page.getByTestId(`browser-doc-view-${dataset.id}-${ragflowDocId}`).click();
    await expect(page.getByTestId('document-preview-modal')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('document-preview-modal').getByText(filename, { exact: false })).toBeVisible();
    await expect(page.getByText(content.trim(), { exact: false })).toBeVisible();
  } finally {
    try {
      if (fs.existsSync(tmpDir)) fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // ignore
    }

    try {
      if (localDocId) {
        await api.delete(`/api/knowledge/documents/${localDocId}`, { headers }).catch(() => {});
      }
    } finally {
      await api.dispose();
    }
  }
});
