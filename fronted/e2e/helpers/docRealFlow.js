// @ts-check
const fs = require('node:fs');
const path = require('node:path');
const { expect, request } = require('@playwright/test');
const { poll, pollSearchToken } = require('./documentFlow');
const { BACKEND_BASE_URL, FRONTEND_BASE_URL, uiLogin } = require('./integration');

function toSafeId(value) {
  return String(value || '').replace(/[^a-zA-Z0-9_-]/g, '_');
}

async function readJson(response, fallbackMessage) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${fallbackMessage}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

async function loginApiAs(username, password) {
  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const loginResponse = await api.post('/api/auth/login', {
    data: { username, password },
  });
  const tokens = await readJson(loginResponse, `login failed for ${username}`);
  const headers = { Authorization: `Bearer ${tokens.access_token}` };
  const meResponse = await api.get('/api/auth/me', { headers });
  const user = await readJson(meResponse, `get current user failed for ${username}`);
  return { api, headers, tokens, user };
}

async function getOperationRequest(api, headers, requestId) {
  const response = await api.get(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}`, {
    headers,
  });
  return readJson(response, `get operation request failed for ${requestId}`);
}

async function waitForOperationRequest(api, headers, requestId, predicate, {
  timeoutMs = 180_000,
  intervalMs = 1_500,
} = {}) {
  let lastDetail = null;
  const matched = await poll(async () => {
    lastDetail = await getOperationRequest(api, headers, requestId);
    return predicate(lastDetail) ? lastDetail : null;
  }, { timeoutMs, intervalMs });

  if (!matched) {
    throw new Error(
      `operation request ${requestId} did not reach expected state: ${JSON.stringify(lastDetail || {})}`
    );
  }
  return matched;
}

async function waitForOperationRequestStatus(api, headers, requestId, expectedStatus, options) {
  return waitForOperationRequest(
    api,
    headers,
    requestId,
    (detail) => String(detail?.status || '') === String(expectedStatus || ''),
    options
  );
}

async function requestSignatureChallenge(api, headers, password) {
  const response = await api.post('/api/electronic-signatures/challenge', {
    headers,
    data: { password },
  });
  return readJson(response, 'request signature challenge failed');
}

async function approveOperationRequestViaApi(api, headers, {
  requestId,
  password,
  meaning = 'Real doc approval accept',
  reason = 'Approve real document request',
  notes,
}) {
  const challenge = await requestSignatureChallenge(api, headers, password);
  const response = await api.post(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}/approve`, {
    headers,
    data: {
      sign_token: challenge.sign_token,
      signature_meaning: meaning,
      signature_reason: reason,
      notes: notes || reason,
    },
  });
  return readJson(response, `approve operation request failed for ${requestId}`);
}

async function withdrawOperationRequestViaApi(api, headers, {
  requestId,
  reason = 'Doc E2E cleanup withdraw',
}) {
  const response = await api.post(`/api/operation-approvals/requests/${encodeURIComponent(requestId)}/withdraw`, {
    headers,
    data: { reason },
  });
  return readJson(response, `withdraw operation request failed for ${requestId}`);
}

async function uploadKnowledgeFileViaApi(api, headers, {
  kbRef,
  filePath,
  mimeType = 'text/plain',
}) {
  const cleanKbRef = String(kbRef || '').trim();
  if (!cleanKbRef) {
    throw new Error('kbRef is required');
  }
  const filename = path.basename(filePath);
  const response = await api.post(`/api/documents/knowledge/upload?kb_id=${encodeURIComponent(cleanKbRef)}`, {
    headers,
    multipart: {
      file: {
        name: filename,
        mimeType,
        buffer: fs.readFileSync(filePath),
      },
    },
  });
  return readJson(response, `upload knowledge file failed for ${filename}`);
}

async function getKnowledgeDocument(api, headers, docId) {
  const response = await api.get(`/api/knowledge/documents/${encodeURIComponent(docId)}`, {
    headers,
  });
  return readJson(response, `get knowledge document failed for ${docId}`);
}

async function listDatasets(api, headers) {
  const response = await api.get('/api/datasets', { headers });
  const payload = await readJson(response, 'list datasets failed');
  return Array.isArray(payload?.datasets) ? payload.datasets : [];
}

async function findDatasetByRef(api, headers, datasetRef) {
  const cleanRef = String(datasetRef || '').trim();
  if (!cleanRef) {
    throw new Error('datasetRef is required');
  }
  const datasets = await listDatasets(api, headers);
  const matched = datasets.find((dataset) => (
    String(dataset?.id || '').trim() === cleanRef
    || String(dataset?.name || '').trim() === cleanRef
  ));
  if (!matched) {
    throw new Error(`dataset not found for ref ${cleanRef}`);
  }
  return matched;
}

async function openBrowserDataset(page, dataset) {
  const quickButton = page.getByTestId(`browser-quick-dataset-${toSafeId(dataset?.id || dataset?.name)}`);
  await expect(quickButton).toBeVisible();
  await quickButton.click();
  await expect(page.getByTestId(`browser-dataset-toggle-${dataset.id}`)).toBeVisible();
}

async function waitForBrowserDocument(page, {
  dataset,
  ragflowDocId,
  filename,
  timeoutMs = 180_000,
} = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await page.goto(`${FRONTEND_BASE_URL}/browser`);
    await expect(page.getByTestId('browser-page')).toBeVisible();
    await openBrowserDataset(page, dataset);

    const row = ragflowDocId
      ? page.getByTestId(`browser-doc-row-${dataset.id}-${ragflowDocId}`)
      : page.locator(`[data-testid^="browser-doc-row-${dataset.id}-"]`).filter({ hasText: filename || '' });
    if (await row.count()) {
      await expect(row.first()).toBeVisible();
      return row.first();
    }

    await page.waitForTimeout(2_000);
  }

  throw new Error(
    `browser document not visible for dataset ${dataset?.id || dataset?.name}: ${filename || ragflowDocId || 'unknown'}`
  );
}

async function openLoggedInPage(browser, username, password) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await uiLogin(page, username, password);
  return { context, page };
}

module.exports = {
  approveOperationRequestViaApi,
  findDatasetByRef,
  FRONTEND_BASE_URL,
  BACKEND_BASE_URL,
  getKnowledgeDocument,
  getOperationRequest,
  listDatasets,
  loginApiAs,
  openBrowserDataset,
  openLoggedInPage,
  pollSearchToken,
  toSafeId,
  uploadKnowledgeFileViaApi,
  waitForBrowserDocument,
  waitForOperationRequest,
  waitForOperationRequestStatus,
  withdrawOperationRequestViaApi,
};
