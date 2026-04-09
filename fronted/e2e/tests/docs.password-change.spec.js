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
} = require('../helpers/userLifecycleFlow');

const summary = loadBootstrapSummary();
const adminUsername =
  process.env.E2E_ADMIN_USER
  || summary?.users?.company_admin?.username
  || summary.users.admin.username;
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';

test('Change password page uses real old/new password flow and login verification @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  const username = summary?.users?.password_change_target?.username || 'doc_password_change_user';
  const fullName = summary?.users?.password_change_target?.full_name || 'Doc Password Change User';
  const initialPassword = uniquePassword('DocPwdInit');
  const changedPassword = uniquePassword('DocPwdChanged');

  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let userSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let userUi = null;
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
        employee_user_id: username,
        password: initialPassword,
        full_name: fullName,
        role: 'viewer',
        manager_user_id: subAdminUser.user_id,
        company_id: viewerUser.company_id,
        department_id: viewerUser.department_id,
        status: 'active',
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      },
    });
    if (!createResponse.ok()) {
      const body = await createResponse.text().catch(() => '');
      throw new Error(`create password-change user failed for ${username}: ${createResponse.status()} ${body}`.trim());
    }
    const createBody = await createResponse.json();
    createdUserId = String(
      readUserEnvelope(createBody, `create password-change user returned invalid payload for ${username}`).user_id || ''
    ).trim();
    expect(createdUserId).toBeTruthy();

    userSession = await loginApiAs(username, initialPassword);
    userUi = await openSessionPage(browser, userSession);
    const page = userUi.page;

    await page.goto(`${FRONTEND_BASE_URL}/change-password`);
    await expect(page.getByTestId('change-password-old')).toBeVisible();
    await page.getByTestId('change-password-old').fill(initialPassword);
    await page.getByTestId('change-password-new').fill(changedPassword);
    await page.getByTestId('change-password-confirm').fill(changedPassword);

    const changeResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes('/api/auth/password')
    ));
    await page.getByTestId('change-password-submit').click();
    await expect((await changeResponsePromise).ok()).toBeTruthy();
    await expect(page.getByTestId('change-password-success')).toContainText('密码修改成功');

    const newLogin = await tryLoginApi(username, changedPassword);
    if (!newLogin.ok) {
      throw new Error(
        `new password login failed: status=${newLogin.status} body=${JSON.stringify(newLogin.body || {})}`
      );
    }

    const oldLogin = await tryLoginApi(username, initialPassword);
    expect(oldLogin.ok).toBeFalsy();
  } finally {
    if (userUi) await userUi.context.close();
    if (userSession) await userSession.api.dispose();
    if (adminSession) {
      if (createdUserId) {
        await deleteUserById(adminSession.api, adminSession.headers, createdUserId);
      } else {
        await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, username);
      }
    }
    if (adminSession) await adminSession.api.dispose();
  }
});
