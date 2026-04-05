// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { createTempTextFixture } = require('../helpers/documentFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const { submitReviewSignature } = require('../helpers/reviewSignature');
const {
  FRONTEND_BASE_URL,
  findDatasetByRef,
  loginApiAs,
  pollSearchToken,
  waitForBrowserDocument,
  waitForOperationRequest,
} = require('../helpers/docRealFlow');

const summary = loadBootstrapSummary();
const uploaderPassword = process.env.E2E_UPLOADER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';
const reviewerPassword = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';
const viewerPassword = process.env.E2E_VIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

async function readSelectTexts(selectLocator) {
  return selectLocator.locator('option').evaluateAll((options) =>
    options
      .map((option) => (option.textContent || '').trim())
      .filter(Boolean)
      .join('\n')
  );
}

test('Doc upload publish flow covers real upload, approval, browser visibility, and searchability @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  const uploadFx = createTempTextFixture('doc-upload-publish');
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let uploaderSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let reviewerSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let viewerSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let uploaderUi = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let reviewerUi = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let viewerUi = null;

  try {
    uploaderSession = await loginApiAs(summary.users.uploader.username, uploaderPassword);
    reviewerSession = await loginApiAs(summary.users.reviewer.username, reviewerPassword);
    viewerSession = await loginApiAs(summary.users.viewer.username, viewerPassword);
    const dataset = await findDatasetByRef(
      viewerSession.api,
      viewerSession.headers,
      summary.knowledge.dataset.id
    );

    uploaderUi = await openSessionPage(browser, uploaderSession);
    await uploaderUi.page.goto(`${FRONTEND_BASE_URL}/upload`);
    await expect(uploaderUi.page.getByTestId('knowledge-upload-page')).toBeVisible();
    await expect.poll(
      () => readSelectTexts(uploaderUi.page.getByTestId('upload-kb-select')),
      { timeout: 60_000, intervals: [500, 1_000, 2_000] }
    ).toContain(summary.knowledge.dataset.name);
    await uploaderUi.page.getByTestId('upload-kb-select').selectOption(summary.knowledge.dataset.name);
    await uploaderUi.page.getByTestId('upload-file-input').setInputFiles(uploadFx.filePath);

    const uploadResponsePromise = uploaderUi.page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes('/api/documents/knowledge/upload')
    ));
    await uploaderUi.page.getByTestId('upload-submit').click();

    const uploadResponse = await uploadResponsePromise;
    await expect(uploadResponse.ok()).toBeTruthy();
    const uploadBody = await uploadResponse.json();
    const requestId = String(uploadBody?.request_id || '').trim();
    expect(requestId).toBeTruthy();

    await uploaderUi.page.waitForURL(/\/approvals\?view=mine/, { timeout: 30_000 });
    await expect(uploaderUi.page.getByTestId(`approval-center-item-${requestId}`)).toBeVisible();

    reviewerUi = await openSessionPage(browser, reviewerSession);
    await reviewerUi.page.goto(`${FRONTEND_BASE_URL}/approvals?request_id=${encodeURIComponent(requestId)}`);
    const requestItem = reviewerUi.page.getByTestId(`approval-center-item-${requestId}`);
    await expect(requestItem).toBeVisible();
    await requestItem.click();
    await expect(reviewerUi.page.getByTestId('approval-center-approve')).toBeVisible();

    const approveResponsePromise = reviewerUi.page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes(`/api/operation-approvals/requests/${requestId}/approve`)
    ));
    await reviewerUi.page.getByTestId('approval-center-approve').click();
    await submitReviewSignature(reviewerUi.page, {
      password: reviewerPassword,
      meaning: 'Doc upload publish accept',
      reason: `Approve ${uploadFx.filename}`,
    });
    await expect((await approveResponsePromise).ok()).toBeTruthy();

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
    const docRow = await waitForBrowserDocument(viewerUi.page, {
      dataset,
      filename: uploadFx.filename,
      timeoutMs: 240_000,
    });
    await expect(docRow).toContainText(uploadFx.filename);

    await docRow.locator('[data-testid^="browser-doc-view-"]').click();
    await expect(viewerUi.page.getByTestId('document-preview-modal')).toBeVisible();
    await expect(viewerUi.page.getByTestId('document-preview-modal')).toContainText(uploadFx.filename);
    await viewerUi.page.getByTestId('document-preview-close').click();
    await expect(viewerUi.page.getByTestId('document-preview-modal')).toHaveCount(0);

    const search = await pollSearchToken(viewerSession.api, viewerSession.headers, {
      question: uploadFx.token,
      datasetIds: [String(dataset.id)],
      token: uploadFx.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    expect(search.ok, search.lastError || JSON.stringify(search.lastPayload || {})).toBeTruthy();
  } finally {
    if (uploaderUi) await uploaderUi.context.close();
    if (reviewerUi) await reviewerUi.context.close();
    if (viewerUi) await viewerUi.context.close();
    if (uploaderSession) await uploaderSession.api.dispose();
    if (reviewerSession) await reviewerSession.api.dispose();
    if (viewerSession) await viewerSession.api.dispose();
    uploadFx.cleanup();
  }
});
