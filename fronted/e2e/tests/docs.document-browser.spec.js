// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { createTempTextFixture, poll } = require('../helpers/documentFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const {
  FRONTEND_BASE_URL,
  approveOperationRequestViaApi,
  findDatasetByRef,
  loginApiAs,
  uploadKnowledgeFileViaApi,
  waitForBrowserDocument,
  waitForOperationRequest,
} = require('../helpers/docRealFlow');

const summary = loadBootstrapSummary();
const uploaderPassword = process.env.E2E_UPLOADER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';
const reviewerPassword = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';
const viewerPassword = process.env.E2E_VIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';

async function readJson(response, message) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${message}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

test('Doc browser covers real published preview/download and version relationship checks @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  const browserFx = createTempTextFixture('doc-browser-visible');
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let uploaderSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let reviewerSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let viewerSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let companyAdminSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let viewerUi = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let uploaderUi = null;

  try {
    uploaderSession = await loginApiAs(summary.users.uploader.username, uploaderPassword);
    reviewerSession = await loginApiAs(summary.users.reviewer.username, reviewerPassword);
    viewerSession = await loginApiAs(summary.users.viewer.username, viewerPassword);
    companyAdminSession = await loginApiAs(summary.users.company_admin.username, adminPassword);

    const dataset = await findDatasetByRef(
      viewerSession.api,
      viewerSession.headers,
      summary.knowledge.dataset.id
    );

    const uploadBrief = await uploadKnowledgeFileViaApi(uploaderSession.api, uploaderSession.headers, {
      kbRef: String(dataset.id),
      filePath: browserFx.filePath,
      mimeType: 'text/plain',
    });
    const requestId = String(uploadBrief?.request_id || '').trim();
    expect(requestId).toBeTruthy();

    await approveOperationRequestViaApi(reviewerSession.api, reviewerSession.headers, {
      requestId,
      password: reviewerPassword,
      meaning: 'Doc browser approval',
      reason: `Approve ${browserFx.filename} for browser visibility`,
    });

    const executedRequest = await waitForOperationRequest(
      reviewerSession.api,
      reviewerSession.headers,
      requestId,
      (detail) => (
        ['executed', 'execution_failed', 'rejected', 'withdrawn'].includes(String(detail?.status || ''))
          ? detail
          : null
      ),
      { timeoutMs: 240_000, intervalMs: 2_000 }
    );
    expect(String(executedRequest?.status || '')).toBe('executed');

    viewerUi = await openSessionPage(browser, viewerSession);
    await viewerUi.page.goto(`${FRONTEND_BASE_URL}/browser`);
    await expect(viewerUi.page.getByTestId('browser-page')).toBeVisible();

    const viewerDocRow = await waitForBrowserDocument(viewerUi.page, {
      dataset,
      filename: browserFx.filename,
      timeoutMs: 240_000,
    });
    await expect(viewerDocRow).toContainText(browserFx.filename);

    await viewerDocRow.locator('[data-testid^="browser-doc-view-"]').click();
    await expect(viewerUi.page.getByTestId('document-preview-modal')).toBeVisible();
    await expect(viewerUi.page.getByTestId('document-preview-modal')).toContainText(browserFx.filename);
    await viewerUi.page.getByTestId('document-preview-close').click();
    await expect(viewerUi.page.getByTestId('document-preview-modal')).toHaveCount(0);
    await expect(viewerDocRow.locator('[data-testid^="browser-doc-download-"]')).toHaveCount(0);

    uploaderUi = await openSessionPage(browser, uploaderSession);
    await uploaderUi.page.goto(`${FRONTEND_BASE_URL}/browser`);
    await expect(uploaderUi.page.getByTestId('browser-page')).toBeVisible();

    const uploaderDocRow = await waitForBrowserDocument(uploaderUi.page, {
      dataset,
      filename: browserFx.filename,
      timeoutMs: 240_000,
    });
    const downloadResponsePromise = uploaderUi.page.waitForResponse((response) => (
      response.request().method() === 'GET'
      && response.url().includes('/api/documents/ragflow/')
      && response.url().includes('/download')
    ));
    await uploaderDocRow.locator('[data-testid^="browser-doc-download-"]').click();
    await expect((await downloadResponsePromise).ok()).toBeTruthy();

    const versionsPayload = await poll(async () => {
      const response = await companyAdminSession.api.get(
        `/api/knowledge/documents/${encodeURIComponent(summary.doc_fixtures.documents.current_doc_id)}/versions`,
        { headers: companyAdminSession.headers }
      );
      const payload = await readJson(response, 'load document versions failed');
      return Array.isArray(payload?.versions) && payload.versions.length >= 2 ? payload : null;
    }, { timeoutMs: 60_000, intervalMs: 1_500 });

    expect(versionsPayload).toBeTruthy();
    expect(String(versionsPayload.current_doc_id || '')).toBe(summary.doc_fixtures.documents.current_doc_id);
    expect(versionsPayload.versions.map((item) => String(item.doc_id))).toEqual(
      expect.arrayContaining([
        summary.doc_fixtures.documents.current_doc_id,
        summary.doc_fixtures.documents.previous_doc_id,
      ])
    );
  } finally {
    if (viewerUi) await viewerUi.context.close();
    if (uploaderUi) await uploaderUi.context.close();
    if (uploaderSession) await uploaderSession.api.dispose();
    if (reviewerSession) await reviewerSession.api.dispose();
    if (viewerSession) await viewerSession.api.dispose();
    if (companyAdminSession) await companyAdminSession.api.dispose();
    browserFx.cleanup();
  }
});
