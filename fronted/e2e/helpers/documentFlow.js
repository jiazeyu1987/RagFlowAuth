// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function createTempTextFixture(prefix = 'ragflowauth-e2e-flow') {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
  const token = `__E2E_TOKEN_${Date.now()}_${Math.random().toString(16).slice(2, 8)}__`;
  const filename = `e2e_${Date.now()}_${Math.random().toString(16).slice(2, 8)}.txt`;
  const content = `E2E flow token: ${token}\n`;
  const filePath = path.join(tmpDir, filename);
  fs.writeFileSync(filePath, content, 'utf8');
  return {
    tmpDir,
    filePath,
    filename,
    token,
    content,
    cleanup() {
      try {
        fs.rmSync(tmpDir, { recursive: true, force: true });
      } catch {
        // noop
      }
    },
  };
}

async function poll(fn, { timeoutMs = 120_000, intervalMs = 1_500 } = {}) {
  const start = Date.now();
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const out = await fn();
    if (out) return out;
    if (Date.now() - start >= timeoutMs) return null;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

async function fetchFirstDataset(api, headers) {
  const datasetsResp = await api.get('/api/datasets', { headers });
  if (!datasetsResp.ok()) {
    return { ok: false, reason: `GET /api/datasets failed: ${datasetsResp.status()}` };
  }
  const payload = await datasetsResp.json();
  const datasets = payload?.datasets || [];
  if (!Array.isArray(datasets) || datasets.length === 0) {
    return { ok: false, reason: 'no datasets available for current user' };
  }
  return { ok: true, dataset: datasets[0] };
}

async function uploadDocumentViaUI(page, frontendBaseUrl, dataset, filePath) {
  await page.goto(`${frontendBaseUrl}/upload`);
  await page.getByTestId('upload-kb-select').selectOption(String(dataset?.name || dataset?.id || ''));
  const [uploadResp] = await Promise.all([
    page.waitForResponse((r) => {
      if (r.request().method() !== 'POST') return false;
      const url = r.url();
      return url.includes('/api/documents/knowledge/upload') || url.includes('/api/knowledge/upload');
    }),
    (async () => {
      await page.getByTestId('upload-file-input').setInputFiles(filePath);
      await page.getByTestId('upload-submit').click();
    })(),
  ]);
  const body = await uploadResp.json().catch(() => ({}));
  return { ok: uploadResp.ok(), status: uploadResp.status(), body };
}

async function approvePendingDocument(page, docId) {
  page.once('dialog', async (dialog) => {
    if (dialog.type() === 'confirm') await dialog.accept();
    else await dialog.dismiss();
  });
  const [approveResp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes(`/api/knowledge/documents/${docId}/approve`) && r.request().method() === 'POST'),
    page.getByTestId(`docs-approve-${docId}`).click(),
  ]);
  const body = await approveResp.json().catch(() => ({}));
  return { ok: approveResp.ok(), status: approveResp.status(), body };
}

async function rejectPendingDocument(page, docId, note = 'e2e reject') {
  page.once('dialog', async (dialog) => {
    if (dialog.type() === 'prompt') await dialog.accept(note);
    else if (dialog.type() === 'confirm') await dialog.accept();
    else await dialog.dismiss();
  });
  const [rejectResp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes(`/api/knowledge/documents/${docId}/reject`) && r.request().method() === 'POST'),
    page.getByTestId(`docs-reject-${docId}`).click(),
  ]);
  const body = await rejectResp.json().catch(() => ({}));
  return { ok: rejectResp.ok(), status: rejectResp.status(), body };
}

function getChunkText(chunk) {
  if (!chunk) return '';
  if (typeof chunk.content === 'string' && chunk.content) return chunk.content;
  if (typeof chunk.content_with_weight === 'string' && chunk.content_with_weight) return chunk.content_with_weight;
  return '';
}

async function pollSearchToken(api, headers, { question, datasetIds, token, expectFound, timeoutMs = 180_000 }) {
  let lastError = null;
  let lastPayload = null;

  const found = await poll(
    async () => {
      const resp = await api.post('/api/search', {
        headers,
        data: {
          question,
          dataset_ids: Array.isArray(datasetIds) ? datasetIds : [],
          page: 1,
          page_size: 30,
          top_k: 30,
          similarity_threshold: 0.2,
          keyword: true,
          highlight: false,
        },
      });
      if (!resp.ok()) {
        lastError = `POST /api/search failed: ${resp.status()}`;
        return false;
      }
      const payload = await resp.json().catch(() => ({}));
      lastPayload = payload;
      const chunks = Array.isArray(payload?.chunks) ? payload.chunks : [];
      const hasToken = chunks.some((c) => getChunkText(c).includes(token));
      return expectFound ? hasToken : !hasToken;
    },
    { timeoutMs, intervalMs: 2_000 },
  );

  return {
    ok: !!found,
    lastError,
    lastPayload,
  };
}

async function pollAuditEvent(api, headers, { action, filename, username, timeoutMs = 60_000 }) {
  return poll(
    async () => {
      const query = new URLSearchParams({
        limit: '200',
        offset: '0',
        ...(action ? { action } : {}),
        ...(username ? { username } : {}),
      }).toString();
      const resp = await api.get(`/api/audit/events?${query}`, { headers });
      if (!resp.ok()) return null;
      const payload = await resp.json().catch(() => ({}));
      const items = Array.isArray(payload?.items) ? payload.items : [];
      return items.find((it) => String(it?.filename || '') === String(filename || '')) || null;
    },
    { timeoutMs, intervalMs: 1_500 },
  );
}

module.exports = {
  createTempTextFixture,
  poll,
  fetchFirstDataset,
  uploadDocumentViaUI,
  approvePendingDocument,
  rejectPendingDocument,
  pollSearchToken,
  pollAuditEvent,
};
