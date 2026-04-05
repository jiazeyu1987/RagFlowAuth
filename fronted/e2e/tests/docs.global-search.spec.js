// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { createTempTextFixture } = require('../helpers/documentFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const {
  FRONTEND_BASE_URL,
  approveOperationRequestViaApi,
  loginApiAs,
  pollSearchToken,
  uploadKnowledgeFileViaApi,
  waitForOperationRequest,
} = require('../helpers/docRealFlow');

const summary = loadBootstrapSummary();
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
const reviewerPassword = process.env.E2E_REVIEWER_PASS || adminPassword;

test('Doc: global search returns real uploaded/approved knowledge chunk @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  const fixture = createTempTextFixture('doc-global-search');
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let adminSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let reviewerSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let adminUi = null;

  try {
    adminSession = await loginApiAs(summary.users.admin.username, adminPassword);
    reviewerSession = await loginApiAs(summary.users.reviewer.username, reviewerPassword);

    const upload = await uploadKnowledgeFileViaApi(adminSession.api, adminSession.headers, {
      kbRef: String(summary.knowledge.dataset.id),
      filePath: fixture.filePath,
      mimeType: 'text/plain',
    });
    const requestId = String(upload?.request_id || '').trim();
    expect(requestId).toBeTruthy();

    await approveOperationRequestViaApi(reviewerSession.api, reviewerSession.headers, {
      requestId,
      password: reviewerPassword,
      meaning: 'Doc global-search approval',
      reason: `Approve ${fixture.filename}`,
    });
    const executed = await waitForOperationRequest(
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
    expect(String(executed?.status || '')).toBe('executed');

    const searchResult = await pollSearchToken(adminSession.api, adminSession.headers, {
      question: fixture.token,
      datasetIds: [String(summary.knowledge.dataset.id)],
      token: fixture.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    expect(searchResult.ok, searchResult.lastError || JSON.stringify(searchResult.lastPayload || {})).toBeTruthy();

    adminUi = await openSessionPage(browser, adminSession);
    await adminUi.page.goto(`${FRONTEND_BASE_URL}/agents`);
    await expect(adminUi.page.getByTestId('agents-search-input')).toBeVisible();
    await adminUi.page.getByTestId('agents-search-input').fill(fixture.token);

    const searchResponsePromise = adminUi.page.waitForResponse(
      (response) => response.request().method() === 'POST' && response.url().includes('/api/search')
    );
    await adminUi.page.getByTestId('agents-search-button').click();
    const searchResponse = await searchResponsePromise;
    expect(searchResponse.ok()).toBeTruthy();

    await expect(adminUi.page.getByTestId('agents-result-item-0')).toBeVisible({ timeout: 60_000 });
    await expect(adminUi.page.getByTestId('agents-results-summary')).toContainText(/\d+/);
    await expect(adminUi.page.getByText(fixture.filename).first()).toBeVisible({ timeout: 60_000 });
    await expect(adminUi.page.getByTestId('agents-error')).toHaveCount(0);
  } finally {
    if (adminUi) await adminUi.context.close();
    if (adminSession) await adminSession.api.dispose();
    if (reviewerSession) await reviewerSession.api.dispose();
    fixture.cleanup();
  }
});
