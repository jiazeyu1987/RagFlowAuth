// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { openSessionPage } = require('../helpers/docSessionPage');
const {
  createPermissionGroup,
  deletePermissionGroup,
  getUser,
  loginApiAs,
  normalizeGroupIds,
  updateUserGroups,
} = require('../helpers/permissionGroupsFlow');

const summary = loadBootstrapSummary();
const FRONTEND_BASE_URL = process.env.E2E_FRONTEND_BASE_URL || 'http://127.0.0.1:33002';
const subAdminPassword = process.env.E2E_SUB_ADMIN_PASS || process.env.E2E_ADMIN_PASS || 'admin123';
const viewerPassword = process.env.E2E_VIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

test('Role permission menu shows real menu and route changes after permission group rebinding @doc-e2e', async ({ browser }) => {
  test.setTimeout(180_000);
  const stamp = Date.now();
  const groupName = `doc_pg_menu_${stamp}`;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let subAdminSession = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let viewerSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let subAdminUi = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let viewerUi = null;
  /** @type {number[]} */
  let originalViewerGroups = [];
  let createdGroupId = 0;

  try {
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, subAdminPassword);
    viewerSession = await loginApiAs(summary.users.viewer.username, viewerPassword);

    const viewerDetail = await getUser(subAdminSession.api, subAdminSession.headers, summary.users.viewer.user_id);
    originalViewerGroups = normalizeGroupIds(viewerDetail?.group_ids);

    createdGroupId = await createPermissionGroup(subAdminSession.api, subAdminSession.headers, {
      group_name: groupName,
      description: 'Doc e2e permission menu effect',
      accessible_kbs: [],
      can_upload: true,
      can_download: false,
      can_delete: false,
      can_view_kb_config: false,
      can_view_tools: false,
    });

    await updateUserGroups(
      subAdminSession.api,
      subAdminSession.headers,
      summary.users.viewer.user_id,
      [createdGroupId]
    );

    await viewerSession.api.dispose();
    viewerSession = await loginApiAs(summary.users.viewer.username, viewerPassword);

    subAdminUi = await openSessionPage(browser, subAdminSession);
    await subAdminUi.page.goto(`${FRONTEND_BASE_URL}/`);
    await expect(subAdminUi.page.getByTestId('nav-permission-groups')).toBeVisible();

    viewerUi = await openSessionPage(browser, viewerSession);
    await viewerUi.page.goto(`${FRONTEND_BASE_URL}/`);
    await expect(viewerUi.page.getByTestId('layout-sidebar')).toBeVisible();
    await expect(viewerUi.page.getByTestId('nav-upload')).toBeVisible();
    await expect(viewerUi.page.getByTestId('nav-permission-groups')).toHaveCount(0);
    await expect(viewerUi.page.getByTestId('nav-users')).toHaveCount(0);

    await viewerUi.page.goto(`${FRONTEND_BASE_URL}/upload`);
    await expect(viewerUi.page).toHaveURL(/\/upload$/);
    await expect(viewerUi.page.getByTestId('knowledge-upload-page')).toBeVisible();

    await viewerUi.page.goto(`${FRONTEND_BASE_URL}/permission-groups`);
    await expect(viewerUi.page).toHaveURL(/\/unauthorized$/);
    await expect(viewerUi.page.getByTestId('unauthorized-title')).toBeVisible();
  } finally {
    if (subAdminSession) {
      await updateUserGroups(
        subAdminSession.api,
        subAdminSession.headers,
        summary.users.viewer.user_id,
        originalViewerGroups
      ).catch(() => {});
      if (createdGroupId > 0) {
        await deletePermissionGroup(subAdminSession.api, subAdminSession.headers, createdGroupId).catch(() => {});
      }
    }

    if (subAdminUi) await subAdminUi.context.close();
    if (viewerUi) await viewerUi.context.close();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (viewerSession) await viewerSession.api.dispose();
  }
});
