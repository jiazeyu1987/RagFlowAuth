// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { createTempTextFixture, pollSearchToken } = require('../helpers/documentFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const {
  FRONTEND_BASE_URL,
  approveOperationRequestViaApi,
  loginApiAs,
  uploadKnowledgeFileViaApi,
  waitForOperationRequest,
} = require('../helpers/docRealFlow');
const {
  createChatSessionViaUi,
  deleteChatSessionViaApi,
  openChatAndSelect,
  sendChatQuestionViaUi,
} = require('../helpers/searchChatFlow');

const summary = loadBootstrapSummary();
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
const reviewerPassword = process.env.E2E_REVIEWER_PASS || adminPassword;

test('Doc: smart chat uses real knowledge and returns non-empty answer @doc-e2e', async ({ browser }) => {
  test.setTimeout(360_000);

  const fixture = createTempTextFixture('doc-chat');
  const chatId = String(summary?.knowledge?.chat?.id || '').trim();
  expect(chatId).toBeTruthy();

  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let adminSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let reviewerSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let adminUi = null;
  let createdSessionId = '';

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
      meaning: 'Doc chat approval',
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

    const precheck = await pollSearchToken(adminSession.api, adminSession.headers, {
      question: fixture.token,
      datasetIds: [String(summary.knowledge.dataset.id)],
      token: fixture.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    expect(precheck.ok, precheck.lastError || JSON.stringify(precheck.lastPayload || {})).toBeTruthy();

    adminUi = await openSessionPage(browser, adminSession);
    await openChatAndSelect(adminUi.page, chatId);

    createdSessionId = await createChatSessionViaUi(adminUi.page, chatId);
    const assistantMessage = await sendChatQuestionViaUi(
      adminUi.page,
      chatId,
      `请根据知识库回答：${fixture.token}`
    );
    await expect(assistantMessage).toBeVisible();
    await expect(adminUi.page.getByTestId('chat-error')).toHaveCount(0);

    await adminUi.page.goto(`${FRONTEND_BASE_URL}/chat`);
    await expect(adminUi.page.getByTestId('chat-page')).toBeVisible();
  } finally {
    if (adminSession && createdSessionId && chatId) {
      await deleteChatSessionViaApi(adminSession.api, adminSession.headers, chatId, createdSessionId);
    }
    if (adminUi) {
      try {
        await adminUi.context.close();
      } catch {
        // Browser may already be closed by timeout handling.
      }
    }
    if (adminSession) await adminSession.api.dispose();
    if (reviewerSession) await reviewerSession.api.dispose();
    fixture.cleanup();
  }
});
