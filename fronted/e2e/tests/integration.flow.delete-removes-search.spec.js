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

test('flow: delete approved document removes search hit and writes delete audit @integration @flow', async ({ page }) => {
  test.setTimeout(300_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);
  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const fx = createTempTextFixture('ragflowauth-e2e-delete-flow');
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

    const searchableBeforeDelete = await pollSearchToken(api, headers, {
      question: fx.token,
      datasetIds: [String(dataset.id)],
      token: fx.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    if (!searchableBeforeDelete.ok) {
      const detail = searchableBeforeDelete.lastError || JSON.stringify(searchableBeforeDelete.lastPayload || {});
      test.fail(true, `document not searchable before delete: ${detail}`);
    }

    const delResp = await api.delete(`/api/knowledge/documents/${localDocId}`, { headers });
    expect(delResp.ok()).toBeTruthy();
    localDocId = null;

    const searchableAfterDelete = await pollSearchToken(api, headers, {
      question: fx.token,
      datasetIds: [String(dataset.id)],
      token: fx.token,
      expectFound: false,
      timeoutMs: 120_000,
    });
    if (!searchableAfterDelete.ok) {
      const detail = searchableAfterDelete.lastError || JSON.stringify(searchableAfterDelete.lastPayload || {});
      test.fail(true, `deleted document still searchable: ${detail}`);
    }

    const deleteEvent = await pollAuditEvent(api, headers, {
      action: 'document_delete',
      filename: fx.filename,
      username: ADMIN_USER,
      timeoutMs: 60_000,
    });
    expect(deleteEvent).toBeTruthy();

    await page.goto(`${FRONTEND_BASE_URL}/logs`);
    await page.getByTestId('audit-filter-action').selectOption('document_delete');
    await page.getByTestId('audit-filter-username').fill(ADMIN_USER);
    await page.getByTestId('audit-apply').click();
    await expect(page.getByTestId('audit-table')).toContainText(fx.filename, { timeout: 30_000 });
  } finally {
    fx.cleanup();
    try {
      if (localDocId) await api.delete(`/api/knowledge/documents/${localDocId}`, { headers }).catch(() => {});
    } finally {
      await api.dispose();
    }
  }
});

