// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { openSessionPage } = require('../helpers/docSessionPage');
const { FRONTEND_BASE_URL } = require('../helpers/docRealFlow');
const {
  deleteUserById,
  ensureUserDeletedByUsername,
  findUserByUsername,
  loginApiAs,
  readUserEnvelope,
  tryLoginApi,
  uniquePassword,
  uniqueUsername,
  waitForUserVisible,
} = require('../helpers/userLifecycleFlow');

const summary = loadBootstrapSummary();
const adminUsername =
  process.env.E2E_ADMIN_USER
  || summary?.users?.company_admin?.username
  || summary.users.admin.username;
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';

test('User management covers real create, reset password, disable/enable, and login effects @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  const username = uniqueUsername('doc_users');
  const displayName = `Doc User ${Date.now()}`;
  const initialPassword = uniquePassword('DocUserInit');
  const resetPassword = uniquePassword('DocUserReset');

  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let adminUi = null;
  let createdUserId = '';

  try {
    adminSession = await loginApiAs(adminUsername, adminPassword);
    await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, username);

    const viewerUser = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      summary.users.viewer.username
    );
    const subAdminUser = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      summary.users.sub_admin.username
    );
    expect(viewerUser).toBeTruthy();
    expect(subAdminUser).toBeTruthy();

    const createResponse = await adminSession.api.post('/api/users', {
      headers: adminSession.headers,
      data: {
        username,
        password: initialPassword,
        full_name: displayName,
        role: 'viewer',
        manager_user_id: subAdminUser.user_id,
        company_id: viewerUser.company_id,
        department_id: viewerUser.department_id,
        status: 'active',
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      },
    });
    await expect(createResponse.ok()).toBeTruthy();
    const createBody = await createResponse.json();
    createdUserId = String(
      readUserEnvelope(createBody, `create user returned invalid payload for ${username}`).user_id || ''
    ).trim();
    expect(createdUserId).toBeTruthy();

    const createdUser = await waitForUserVisible(adminSession.api, adminSession.headers, username);
    expect(createdUser).toBeTruthy();
    createdUserId = String(createdUser?.user_id || createdUserId || '');

    adminUi = await openSessionPage(browser, adminSession);
    const page = adminUi.page;
    await page.goto(`${FRONTEND_BASE_URL}/users`);
    await expect(page.getByTestId('users-management-layout')).toBeVisible();
    await page.reload();
    await expect(page.getByTestId(`users-row-${createdUserId}`)).toBeVisible();

    const resetResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes(`/api/users/${encodeURIComponent(createdUserId)}/password`)
    ));
    await page.getByTestId(`users-reset-password-${createdUserId}`).click();
    await expect(page.getByTestId('users-reset-password-modal')).toBeVisible();
    await page.getByTestId('users-reset-password-new').fill(resetPassword);
    await page.getByTestId('users-reset-password-confirm').fill(resetPassword);
    await page.getByTestId('users-reset-password-save').click();
    await expect((await resetResponsePromise).ok()).toBeTruthy();
    await expect(page.getByTestId('users-reset-password-modal')).toHaveCount(0);

    const oldLogin = await tryLoginApi(username, initialPassword);
    expect(oldLogin.ok).toBeFalsy();
    const newLogin = await tryLoginApi(username, resetPassword);
    expect(newLogin.ok).toBeTruthy();

    await page.getByTestId(`users-toggle-status-${createdUserId}`).click();
    await expect(page.getByTestId('users-disable-modal')).toBeVisible();
    const disableResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes(`/api/users/${encodeURIComponent(createdUserId)}`)
    ));
    await page.getByTestId('users-disable-mode-immediate').check();
    await page.getByTestId('users-disable-confirm').click();
    await expect((await disableResponsePromise).ok()).toBeTruthy();
    await expect(page.getByTestId('users-disable-modal')).toHaveCount(0);

    const disabledLogin = await tryLoginApi(username, resetPassword);
    expect(disabledLogin.ok).toBeFalsy();

    const enableResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes(`/api/users/${encodeURIComponent(createdUserId)}`)
    ));
    await page.getByTestId(`users-toggle-status-${createdUserId}`).click();
    await expect((await enableResponsePromise).ok()).toBeTruthy();

    const enabledLogin = await tryLoginApi(username, resetPassword);
    expect(enabledLogin.ok).toBeTruthy();
  } finally {
    if (adminSession) {
      if (!createdUserId && adminSession?.headers) {
        const found = await waitForUserVisible(adminSession.api, adminSession.headers, username, {
          timeoutMs: 2_000,
          intervalMs: 500,
        }).catch(() => null);
        createdUserId = String(found?.user_id || '');
      }
      if (createdUserId) {
        await deleteUserById(adminSession.api, adminSession.headers, createdUserId);
      } else {
        await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, username);
      }
    }
    if (adminUi) await adminUi.context.close();
    if (adminSession) await adminSession.api.dispose();
  }
});
