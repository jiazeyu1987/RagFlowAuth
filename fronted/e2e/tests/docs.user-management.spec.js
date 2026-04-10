// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { openSessionPage } = require('../helpers/docSessionPage');
const { FRONTEND_BASE_URL } = require('../helpers/docRealFlow');
const {
  deleteUserById,
  ensureUserDeletedByUsername,
  findUserByUsername,
  getUser,
  loginApiAs,
  normalizeToolIds,
  readUserEnvelope,
  tryLoginApi,
  updateUserTools,
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
const bootstrapSubAdminUsername = summary.users.sub_admin.username;
const GRANTED_TOOL_IDS = ['paper_download', 'patent_download', 'package_drawing', 'nhsa_code_search'];
const ASSIGNED_SUBSET_TOOL_IDS = ['paper_download', 'package_drawing'];
const FORBIDDEN_EXTRA_TOOL_ID = 'drug_admin';
const MANAGED_SUB_ADMIN_EMPLOYEE_USER_ID = 'doc_login_user';
const MANAGED_SUB_ADMIN_FULL_NAME = 'Doc Login User';

function sortToolIds(rawValue) {
  return normalizeToolIds(rawValue).slice().sort();
}

test('User management covers real create, reset password, disable/enable, login effects, and sub-admin tool assignment boundaries @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  const username = summary?.users?.user_management_target?.username || 'doc_user_management_user';
  const displayName = summary?.users?.user_management_target?.full_name || 'Doc User Management User';
  const initialPassword = uniquePassword('DocUserInit');
  const resetPassword = uniquePassword('DocUserReset');
  const managedSubAdminUsername = uniqueUsername('doc_user_management_sub_admin');
  const managedSubAdminPassword = uniquePassword('DocSubAdmin');

  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let subAdminSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let adminUi = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let subAdminUi = null;
  let createdUserId = '';
  let createdSubAdminId = '';

  try {
    adminSession = await loginApiAs(adminUsername, adminPassword);
    await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, username);
    await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, managedSubAdminUsername);

    const viewerUser = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      summary.users.viewer.username
    );
    const subAdminUser = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      bootstrapSubAdminUsername
    );
    expect(viewerUser).toBeTruthy();
    expect(subAdminUser).toBeTruthy();
    const bootstrapSubAdminId = String(subAdminUser?.user_id || '').trim();
    expect(bootstrapSubAdminId).toBeTruthy();
    const bootstrapSubAdmin = await getUser(adminSession.api, adminSession.headers, bootstrapSubAdminId);

    const createSubAdminResponse = await adminSession.api.post('/api/users', {
      headers: adminSession.headers,
      data: {
        username: managedSubAdminUsername,
        employee_user_id: MANAGED_SUB_ADMIN_EMPLOYEE_USER_ID,
        password: managedSubAdminPassword,
        full_name: MANAGED_SUB_ADMIN_FULL_NAME,
        role: 'sub_admin',
        company_id: bootstrapSubAdmin.company_id || viewerUser.company_id,
        department_id: bootstrapSubAdmin.department_id || viewerUser.department_id,
        managed_kb_root_node_id: bootstrapSubAdmin.managed_kb_root_node_id,
        tool_ids: [],
        status: 'active',
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      },
    });
    if (!createSubAdminResponse.ok()) {
      const body = await createSubAdminResponse.text().catch(() => '');
      throw new Error(`create sub-admin failed for ${managedSubAdminUsername}: ${createSubAdminResponse.status()} ${body}`.trim());
    }
    const createSubAdminBody = await createSubAdminResponse.json();
    createdSubAdminId = String(
      readUserEnvelope(createSubAdminBody, `create sub-admin returned invalid payload for ${managedSubAdminUsername}`).user_id || ''
    ).trim();
    expect(createdSubAdminId).toBeTruthy();

    const grantToolResponse = await updateUserTools(
      adminSession.api,
      adminSession.headers,
      createdSubAdminId,
      GRANTED_TOOL_IDS
    );
    if (!grantToolResponse.ok()) {
      const body = await grantToolResponse.text().catch(() => '');
      throw new Error(`grant sub-admin tools failed for ${createdSubAdminId}: ${grantToolResponse.status()} ${body}`.trim());
    }
    const grantedSubAdmin = await getUser(adminSession.api, adminSession.headers, createdSubAdminId);
    expect(sortToolIds(grantedSubAdmin?.tool_ids)).toEqual(sortToolIds(GRANTED_TOOL_IDS));

    const createResponse = await adminSession.api.post('/api/users', {
      headers: adminSession.headers,
      data: {
        username,
        employee_user_id: username,
        password: initialPassword,
        full_name: displayName,
        role: 'viewer',
        manager_user_id: createdSubAdminId,
        company_id: bootstrapSubAdmin.company_id || viewerUser.company_id,
        department_id: bootstrapSubAdmin.department_id || viewerUser.department_id,
        status: 'active',
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      },
    });
    if (!createResponse.ok()) {
      const body = await createResponse.text().catch(() => '');
      throw new Error(`create user failed for ${username}: ${createResponse.status()} ${body}`.trim());
    }
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

    subAdminSession = await loginApiAs(managedSubAdminUsername, managedSubAdminPassword);
    expect(sortToolIds(subAdminSession.user?.permissions?.accessible_tools)).toEqual(sortToolIds(GRANTED_TOOL_IDS));

    subAdminUi = await openSessionPage(browser, subAdminSession);
    const subAdminPage = subAdminUi.page;
    await subAdminPage.goto(`${FRONTEND_BASE_URL}/users`);
    await expect(subAdminPage.getByTestId('users-management-layout')).toBeVisible();
    await subAdminPage.reload();
    await expect(subAdminPage.getByTestId(`users-row-${createdUserId}`)).toBeVisible();

    await subAdminPage.getByTestId(`users-edit-tools-${createdUserId}`).click();
    await expect(subAdminPage.getByTestId('users-tool-modal')).toBeVisible();
    for (const toolId of GRANTED_TOOL_IDS) {
      await expect(subAdminPage.getByTestId(`users-tool-checkbox-${toolId}`)).toBeVisible();
    }
    await expect(subAdminPage.getByTestId(`users-tool-checkbox-${FORBIDDEN_EXTRA_TOOL_ID}`)).toHaveCount(0);

    for (const toolId of ASSIGNED_SUBSET_TOOL_IDS) {
      await subAdminPage.getByTestId(`users-tool-checkbox-${toolId}`).check();
    }
    const assignToolResponsePromise = subAdminPage.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes(`/api/users/${encodeURIComponent(createdUserId)}`)
    ));
    await subAdminPage.getByTestId('users-tool-save').click();
    await expect((await assignToolResponsePromise).ok()).toBeTruthy();
    await expect(subAdminPage.getByTestId('users-tool-modal')).toHaveCount(0);

    const assignedManagedUser = await getUser(adminSession.api, adminSession.headers, createdUserId);
    expect(sortToolIds(assignedManagedUser?.tool_ids)).toEqual(sortToolIds(ASSIGNED_SUBSET_TOOL_IDS));

    const forbiddenToolResponse = await updateUserTools(
      subAdminSession.api,
      subAdminSession.headers,
      createdUserId,
      [...GRANTED_TOOL_IDS, FORBIDDEN_EXTRA_TOOL_ID]
    );
    expect(forbiddenToolResponse.ok()).toBeFalsy();
    expect(forbiddenToolResponse.status()).toBe(403);
    const forbiddenPayload = await forbiddenToolResponse.json().catch(() => ({}));
    expect(String(forbiddenPayload?.detail || '')).toContain('tool_out_of_management_scope');

    const managedUserAfterForbiddenRequest = await getUser(adminSession.api, adminSession.headers, createdUserId);
    expect(sortToolIds(managedUserAfterForbiddenRequest?.tool_ids)).toEqual(sortToolIds(ASSIGNED_SUBSET_TOOL_IDS));
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
      if (createdSubAdminId) {
        await deleteUserById(adminSession.api, adminSession.headers, createdSubAdminId).catch(() => {});
      } else {
        await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, managedSubAdminUsername).catch(() => {});
      }
    }
    if (subAdminUi) await subAdminUi.context.close();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (adminUi) await adminUi.context.close();
    if (adminSession) await adminSession.api.dispose();
  }
});
