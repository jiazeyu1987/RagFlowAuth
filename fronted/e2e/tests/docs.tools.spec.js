// @ts-check
const { expect, test } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { openSessionPage } = require('../helpers/docSessionPage');
const { FRONTEND_BASE_URL } = require('../helpers/docRealFlow');
const {
  createToolsEmptyStateAccount,
  disposeSession,
  loginApiAs,
} = require('../helpers/securityToolsFlow');

const summary = loadBootstrapSummary();
const adminUsername = process.env.E2E_ADMIN_USER || summary?.users?.admin?.username;
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';

function readPageCount(text) {
  const match = String(text || '').match(/\/\s*(\d+)\s*页/);
  return match ? Number(match[1]) : 0;
}

test('Tools page covers real pagination, internal navigation, external popup, and empty-state visibility @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let adminUi = null;
  /** @type {Awaited<ReturnType<typeof createToolsEmptyStateAccount>> | null} */
  let emptyAccount = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let emptyUi = null;

  try {
    adminSession = await loginApiAs(adminUsername, adminPassword);
    adminUi = await openSessionPage(browser, adminSession);
    const page = adminUi.page;

    await page.goto(`${FRONTEND_BASE_URL}/tools`);
    await expect(page.getByTestId('tools-page')).toBeVisible();
    await expect(page.getByTestId('tool-card-nmpa')).toBeVisible();
    await expect(page.getByTestId('tool-card-nhsa_code_search')).toBeVisible();

    const indicator = page.getByTestId('tools-page-indicator');
    await expect.poll(async () => readPageCount(await indicator.textContent())).toBeGreaterThan(1);

    const firstPageLeadCard = await page.locator('[data-testid^="tool-card-"]').first().textContent();
    await page.getByTestId('tools-next-page').click();
    await expect(page.getByTestId('tools-page-indicator')).toContainText('第 2 /');
    const secondPageLeadCard = await page.locator('[data-testid^="tool-card-"]').first().textContent();
    expect(String(secondPageLeadCard || '').trim()).not.toBe(String(firstPageLeadCard || '').trim());

    await page.getByTestId('tools-prev-page').click();
    await expect(page.getByTestId('tools-page-indicator')).toContainText('第 1 /');

    await page.getByTestId('tool-card-nmpa').click();
    await expect(page).toHaveURL(/\/tools\/nmpa$/);
    await expect(page.getByTestId('nmpa-tool-page')).toBeVisible();

    await page.goto(`${FRONTEND_BASE_URL}/tools`);
    const popupPromise = page.waitForEvent('popup');
    await page.getByTestId('tool-card-nhsa_code_search').click();
    const popup = await popupPromise;
    await popup.waitForLoadState('domcontentloaded', { timeout: 30_000 }).catch(() => {});
    await expect.poll(() => popup.url()).toContain('code.nhsa.gov.cn');
    await popup.close();

    emptyAccount = await createToolsEmptyStateAccount(summary);
    emptyUi = await openSessionPage(browser, emptyAccount.userSession);
    const emptyPage = emptyUi.page;
    await emptyPage.goto(`${FRONTEND_BASE_URL}/tools`);
    await expect(emptyPage.getByTestId('tools-page')).toBeVisible();
    await expect(emptyPage.getByTestId('tools-empty-state')).toContainText('暂无可访问的实用工具');
    await expect(emptyPage.locator('[data-testid^="tool-card-"]')).toHaveCount(0);
  } finally {
    if (emptyUi) {
      await emptyUi.context.close().catch(() => {});
    }
    if (emptyAccount) {
      await emptyAccount.cleanup().catch(() => {});
    }
    if (adminUi) {
      await adminUi.context.close().catch(() => {});
    }
    await disposeSession(adminSession);
  }
});
