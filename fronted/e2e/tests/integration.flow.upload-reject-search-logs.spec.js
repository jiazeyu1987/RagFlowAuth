// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, ADMIN_USER, preflightAdmin, uiLogin } = require('../helpers/integration');
const {
  createTempTextFixture,
  fetchFirstDataset,
  uploadDocumentViaUI,
  rejectPendingDocument,
  pollSearchToken,
  pollAuditEvent,
} = require('../helpers/documentFlow');

test('flow: upload -> reject -> not searchable -> upload audit visible @integration @flow', async ({ page }) => {
  test.setTimeout(240_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);
  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const fx = createTempTextFixture('ragflowauth-e2e-reject-flow');
  let localDocId = null;

  try {
    const datasetRes = await fetchFirstDataset(api, headers);
    if (!datasetRes.ok) test.skip(true, datasetRes.reason);
    const dataset = datasetRes.dataset;

    await uiLogin(page);
    await expect(page).toHaveURL(/\/chat$/);

    const upload = await uploadDocumentViaUI(page, FRONTEND_BASE_URL, dataset, fx.filePath);
    expect(upload.ok).toBeTruthy();
    localDocId = upload.body?.doc_id || null;
    expect(localDocId).toBeTruthy();
    await expect(page).toHaveURL(/\/documents/);

    const rejected = await rejectPendingDocument(page, localDocId, 'e2e reject');
    expect(rejected.ok).toBeTruthy();

    const search = await pollSearchToken(api, headers, {
      question: fx.token,
      datasetIds: [String(dataset.id)],
      token: fx.token,
      expectFound: false,
      timeoutMs: 90_000,
    });
    if (!search.ok) {
      const detail = search.lastError || JSON.stringify(search.lastPayload || {});
      test.fail(true, `rejected document unexpectedly searchable: ${detail}`);
    }

    const uploadEvent = await pollAuditEvent(api, headers, {
      action: 'document_upload',
      filename: fx.filename,
      username: ADMIN_USER,
      timeoutMs: 60_000,
    });
    expect(uploadEvent).toBeTruthy();

    await page.goto(`${FRONTEND_BASE_URL}/documents?tab=records`);
    await page.getByTestId('documents-tab-records').click();
    await expect(page.getByText(fx.filename)).toBeVisible({ timeout: 30_000 });
  } finally {
    fx.cleanup();
    try {
      if (localDocId) await api.delete(`/api/knowledge/documents/${localDocId}`, { headers }).catch(() => {});
    } finally {
      await api.dispose();
    }
  }
});

