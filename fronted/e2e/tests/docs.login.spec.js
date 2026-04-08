// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const {
  deleteUserById,
  findUserByUsername,
  loginApiAs,
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

test('Doc login supports failure messaging and success flow @doc-e2e', async ({ page }) => {
  test.setTimeout(180_000);

  const username = uniqueUsername('doc_login');
  const password = uniquePassword('DocLogin');

  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  let createdUserId = '';

  try {
    adminSession = await loginApiAs(adminUsername, adminPassword);
    const viewerUser = summary?.users?.viewer;
    const subAdminUser = summary?.users?.sub_admin;
    if (!viewerUser?.username || !subAdminUser?.username) {
      throw new Error('bootstrap_summary_missing_user_roles');
    }

    const viewer = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      viewerUser.username
    );
    if (!viewer?.company_id) {
      throw new Error('viewer_user_missing_company_id');
    }

    const manager = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      subAdminUser.username
    );
    if (!manager?.user_id) {
      throw new Error('sub_admin_user_missing');
    }

    const createResponse = await adminSession.api.post('/api/users', {
      headers: adminSession.headers,
      data: {
        username,
        password,
        full_name: `Doc Login User ${Date.now()}`,
        role: 'viewer',
        manager_user_id: manager.user_id,
        company_id: viewer.company_id,
        department_id: viewer.department_id,
        status: 'active',
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      },
    });
    if (!createResponse.ok()) {
      const body = await createResponse.text().catch(() => '');
      throw new Error(`create_user_failed:${createResponse.status()} ${body}`.trim());
    }
    const createdBody = await createResponse.json();
    createdUserId = String(createdBody?.user_id || '').trim();
    if (!createdUserId) {
      const createdUser = await waitForUserVisible(adminSession.api, adminSession.headers, username, {
        timeoutMs: 10_000,
        intervalMs: 1_000,
      });
      createdUserId = String(createdUser?.user_id || '').trim();
    }
    if (!createdUserId) {
      throw new Error('create_user_missing_id');
    }

    await page.goto('/login');
    await page.getByTestId('login-username').fill(username);
    await page.getByTestId('login-password').fill(`${password}-wrong`);
    await page.getByTestId('login-submit').click();
    await expect(page.getByTestId('login-error')).toBeVisible();
    await expect(page.getByTestId('login-error')).not.toHaveText('');

    await page.getByTestId('login-username').fill(username);
    await page.getByTestId('login-password').fill(password);
    await page.getByTestId('login-submit').click();
    await expect(page).toHaveURL(/\/chat$/);
    await expect(page.getByTestId('layout-sidebar')).toBeVisible();
  } finally {
    if (adminSession && createdUserId) {
      await deleteUserById(adminSession.api, adminSession.headers, createdUserId);
    }
    if (adminSession) {
      await adminSession.api.dispose();
    }
  }
});
