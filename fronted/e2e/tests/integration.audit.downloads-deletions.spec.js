// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

async function poll(fn, { timeoutMs = 30_000, intervalMs = 1_000 } = {}) {
  const start = Date.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const out = await fn();
    if (out) return out;
    if (Date.now() - start > timeoutMs) return null;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

test('download + delete produce audit records (real backend) @integration', async ({ page }) => {
  test.setTimeout(180_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);
  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });

  let dataset = null;
  let localDocId = null;
  let ragflowDocId = null;
  let downloadId = null;
  let deletionId = null;

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

    await page.goto(`${FRONTEND_BASE_URL}/upload`);
    await page.getByTestId('upload-kb-select').selectOption(String(dataset.name || dataset.id));

    const [uploadResp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/api/knowledge/upload') && r.request().method() === 'POST'),
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

    await Promise.all([
      page.waitForResponse((r) => r.url().includes(`/api/ragflow/documents/${ragflowDocId}/download`) && r.request().method() === 'GET'),
      page.getByTestId(`browser-doc-download-${dataset.id}-${ragflowDocId}`).click(),
    ]);

    const downloadRecord = await poll(async () => {
      const resp = await api.get('/api/ragflow/downloads?limit=50', { headers });
      if (!resp.ok()) return null;
      const payload = await resp.json();
      const list = payload.downloads || [];
      const found = list.find((d) => d && (d.ragflow_doc_id === ragflowDocId || d.filename === filename));
      return found || null;
    });
    if (!downloadRecord) test.fail(true, 'download audit record not found');
    downloadId = downloadRecord.id;

    await page.goto(`${FRONTEND_BASE_URL}/documents?tab=records`);
    await page.getByTestId('documents-tab-records').click();
    await page.getByTestId('audit-tab-downloads').click();
    await expect(page.getByTestId(`audit-download-row-${downloadId}`)).toBeVisible({ timeout: 30_000 });

    // Deleting an approved document isn't available in the current UI (approve tab lists only pending docs),
    // so we delete via API and then assert the audit UI shows the deletion record.
    const delResp = await api.delete(`/api/knowledge/documents/${localDocId}`, { headers });
    if (!delResp.ok()) test.fail(true, `delete /api/knowledge/documents/${localDocId} failed: ${delResp.status()}`);

    const deletionRecord = await poll(async () => {
      const resp = await api.get('/api/knowledge/deletions?limit=50', { headers });
      if (!resp.ok()) return null;
      const payload = await resp.json();
      const list = payload.deletions || [];
      const found = list.find((d) => d && (d.doc_id === localDocId || d.filename === filename));
      return found || null;
    });
    if (!deletionRecord) test.fail(true, 'deletion audit record not found');
    deletionId = deletionRecord.id;

    await page.goto(`${FRONTEND_BASE_URL}/documents?tab=records`);
    await page.getByTestId('documents-tab-records').click();
    await page.getByTestId('audit-tab-deletions').click();
    await expect(page.getByTestId(`audit-deletion-row-${deletionId}`)).toBeVisible({ timeout: 30_000 });
  } finally {
    try {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    } catch {
      // ignore
    }

    try {
      if (localDocId) await api.delete(`/api/knowledge/documents/${localDocId}`, { headers }).catch(() => {});
    } finally {
      await api.dispose();
    }
  }
});
