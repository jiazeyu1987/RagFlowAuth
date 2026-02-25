// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, ADMIN_USER, preflightAdmin, uiLogin } = require('../helpers/integration');
const {
  createTempTextFixture,
  fetchFirstDataset,
  uploadDocumentViaUI,
  approvePendingDocument,
  pollSearchToken,
  pollAuditEvent,
} = require('../helpers/documentFlow');

test('flow: upload -> approve -> searchable -> audit visible @integration @flow', async ({ page }) => {
  test.setTimeout(240_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);
  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const fx = createTempTextFixture('ragflowauth-e2e-approve-flow');
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

    const approved = await approvePendingDocument(page, localDocId);
    expect(approved.ok).toBeTruthy();

    const search = await pollSearchToken(api, headers, {
      question: fx.token,
      datasetIds: [String(dataset.id)],
      token: fx.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    if (!search.ok) {
      const detail = search.lastError || JSON.stringify(search.lastPayload || {});
      test.fail(true, `document not searchable after approve: ${detail}`);
    }

    const uploadEvent = await pollAuditEvent(api, headers, {
      action: 'document_upload',
      filename: fx.filename,
      username: ADMIN_USER,
      timeoutMs: 60_000,
    });
    expect(uploadEvent).toBeTruthy();

    await page.goto(`${FRONTEND_BASE_URL}/logs`);
    await expect(page.getByTestId('audit-logs-page')).toBeVisible();
    await page.getByTestId('audit-filter-action').selectOption('document_upload');
    await page.getByTestId('audit-filter-username').fill(ADMIN_USER);
    await page.getByTestId('audit-apply').click();
    await expect(page.getByTestId('audit-table')).toContainText(fx.filename, { timeout: 30_000 });
    await expect(page.getByTestId('audit-total')).not.toHaveText('0');
  } finally {
    fx.cleanup();
    try {
      if (localDocId) await api.delete(`/api/knowledge/documents/${localDocId}`, { headers }).catch(() => {});
    } finally {
      await api.dispose();
    }
  }
});

