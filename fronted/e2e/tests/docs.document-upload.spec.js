// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { createTempTextFixture } = require('../helpers/documentFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const {
  FRONTEND_BASE_URL,
  loginApiAs,
  waitForOperationRequestStatus,
  withdrawOperationRequestViaApi,
} = require('../helpers/docRealFlow');

const summary = loadBootstrapSummary();
const uploaderPassword = process.env.E2E_UPLOADER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

async function readSelectTexts(selectLocator) {
  return selectLocator.locator('option').evaluateAll((options) =>
    options
      .map((option) => (option.textContent || '').trim())
      .filter(Boolean)
      .join('\n')
  );
}

test('Doc upload page uses real file selection, removal, clear, and submit flow @doc-e2e', async ({ browser }, testInfo) => {
  testInfo.setTimeout(180_000);

  const uploadFx = createTempTextFixture('doc-upload-primary');
  const removeFx = createTempTextFixture('doc-upload-remove');
  let requestId = '';
  /** @type {{api: import('@playwright/test').APIRequestContext, headers: Record<string, string>} | null} */
  let uploaderSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let uploaderUi = null;

  try {
    uploaderSession = await loginApiAs(summary.users.uploader.username, uploaderPassword);
    uploaderUi = await openSessionPage(browser, uploaderSession);
    const { page } = uploaderUi;

    await page.goto(`${FRONTEND_BASE_URL}/upload`);
    await expect(page.getByTestId('knowledge-upload-page')).toBeVisible();
    await expect.poll(
      () => readSelectTexts(page.getByTestId('upload-kb-select')),
      { timeout: 60_000, intervals: [500, 1_000, 2_000] }
    ).toContain(summary.knowledge.dataset.name);
    await expect(page.getByTestId('upload-submit')).toBeDisabled();

    await page.getByTestId('upload-file-input').setInputFiles([uploadFx.filePath, removeFx.filePath]);

    const keptRow = page.locator('[data-testid^="upload-file-item-"]').filter({ hasText: uploadFx.filename }).first();
    const removedRow = page.locator('[data-testid^="upload-file-item-"]').filter({ hasText: removeFx.filename }).first();
    await expect(keptRow).toBeVisible();
    await expect(removedRow).toBeVisible();

    await removedRow.locator('[data-testid^="upload-file-remove-"]').click();
    await expect(removedRow).toHaveCount(0);
    await expect(keptRow).toBeVisible();

    await page.getByTestId('upload-files-clear').click();
    await expect(page.locator('[data-testid^="upload-file-item-"]')).toHaveCount(0);
    await expect(page.getByTestId('upload-submit')).toBeDisabled();

    await page.getByTestId('upload-kb-select').selectOption(summary.knowledge.dataset.name);
    await page.getByTestId('upload-file-input').setInputFiles(uploadFx.filePath);
    await expect(page.getByTestId('upload-submit')).toBeEnabled();

    const uploadResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes('/api/documents/knowledge/upload')
    ));
    await page.getByTestId('upload-submit').click();

    const uploadResponse = await uploadResponsePromise;
    await expect(uploadResponse.ok()).toBeTruthy();
    const uploadBody = await uploadResponse.json();
    requestId = String(uploadBody?.request_id || '').trim();
    expect(requestId).toBeTruthy();

    await expect(page.getByTestId('upload-success')).toContainText(requestId);
    await page.waitForURL(/\/approvals\?view=mine/, { timeout: 30_000 });
    await expect(page.getByTestId('approval-center-page')).toBeVisible();
    await expect(page.getByTestId(`approval-center-item-${requestId}`)).toBeVisible();

    await waitForOperationRequestStatus(
      uploaderSession.api,
      uploaderSession.headers,
      requestId,
      'in_approval',
      { timeoutMs: 60_000, intervalMs: 1_000 }
    );
  } finally {
    if (uploaderUi) {
      await uploaderUi.context.close();
    }
    if (uploaderSession && requestId) {
      await withdrawOperationRequestViaApi(uploaderSession.api, uploaderSession.headers, {
        requestId,
        reason: 'Doc upload spec cleanup',
      });
    }
    if (uploaderSession) {
      await uploaderSession.api.dispose();
    }
    uploadFx.cleanup();
    removeFx.cleanup();
  }
});
