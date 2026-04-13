// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const {
  createKnowledgeDirectory,
  deleteKnowledgeDirectory,
  listKnowledgeDirectories,
} = require('../helpers/knowledgeDirectoryFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const { FRONTEND_BASE_URL, toSafeId } = require('../helpers/docRealFlow');
const {
  createPermissionGroup,
  deletePermissionGroup,
  readJson,
} = require('../helpers/permissionGroupsFlow');
const {
  deleteUserById,
  ensureUserDeletedByUsername,
  getUser,
  loginApiAs,
  readUserEnvelope,
  uniquePassword,
  uniqueUsername,
} = require('../helpers/userLifecycleFlow');

const summary = loadBootstrapSummary();
const adminUsername =
  process.env.E2E_ADMIN_USER
  || summary?.users?.company_admin?.username
  || summary.users.admin.username;
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
const creatorSubAdminUsername = summary.users.sub_admin.username;
const creatorSubAdminPassword = process.env.E2E_SUB_ADMIN_PASS || adminPassword;
const MANAGED_SUB_ADMIN_EMPLOYEE_USER_ID = 'doc_login_user';
const MANAGED_SUB_ADMIN_FULL_NAME = 'Doc Login User';

function escapeRegex(value) {
  return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function createGroupFolder(api, headers, { name, parentId = null }) {
  const response = await api.post('/api/permission-groups/folders', {
    headers,
    data: {
      name,
      parent_id: parentId,
    },
  });
  const body = await readJson(response, `create permission group folder failed for ${name}`);
  const folder = body?.folder;
  if (!folder || typeof folder !== 'object') {
    throw new Error(`create permission group folder returned invalid payload for ${name}`);
  }
  if (!String(folder.id || '').trim()) {
    throw new Error(`create permission group folder did not return folder id for ${name}`);
  }
  return folder;
}

async function deleteGroupFolder(api, headers, folderId) {
  const response = await api.delete(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`, {
    headers,
  });
  if (response.ok() || response.status() === 404) {
    return;
  }
  const body = await response.text().catch(() => '');
  throw new Error(`delete permission group folder failed for ${folderId}: ${response.status()} ${body}`.trim());
}

test('Permission groups page keeps other sub-admin assigned folders visible but read-only @doc-e2e', async ({ browser }) => {
  test.setTimeout(180_000);

  const stamp = Date.now();
  const folderName = `doc_pg_shared_folder_${stamp}`;
  const groupName = `doc_pg_shared_group_${stamp}`;
  const managedSubAdminUsername = uniqueUsername('doc_pg_visibility_sub_admin');
  const managedSubAdminPassword = uniquePassword('DocPgVisibility');

  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let creatorSession = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let managedSubAdminSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let managedSubAdminUi = null;
  let createdSubAdminId = '';
  let createdManagedRootId = '';
  let folderId = '';
  let groupId = 0;

  try {
    adminSession = await loginApiAs(adminUsername, adminPassword);
    await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, managedSubAdminUsername);

    const creatorSubAdmin = await getUser(
      adminSession.api,
      adminSession.headers,
      summary.users.sub_admin.user_id
    );
    const fallbackViewer = await getUser(
      adminSession.api,
      adminSession.headers,
      summary.users.viewer.user_id
    );
    const knowledgeTree = await listKnowledgeDirectories(adminSession.api, adminSession.headers);
    const occupiedManagedRootId = String(
      creatorSubAdmin.managed_kb_root_node_id || summary?.knowledge?.managed_root_node_id || ''
    ).trim();
    expect(occupiedManagedRootId).toBeTruthy();
    expect(
      knowledgeTree.nodes.some((node) => String(node?.id || '').trim() === occupiedManagedRootId)
    ).toBeTruthy();
    const createdManagedRoot = await createKnowledgeDirectory(adminSession.api, adminSession.headers, {
      name: `doc_pg_visibility_root_${Date.now()}`,
      parentId: null,
    });
    createdManagedRootId = String(createdManagedRoot.id || '').trim();
    expect(createdManagedRootId).toBeTruthy();

    const createSubAdminResponse = await adminSession.api.post('/api/users', {
      headers: adminSession.headers,
      data: {
        username: managedSubAdminUsername,
        employee_user_id: MANAGED_SUB_ADMIN_EMPLOYEE_USER_ID,
        password: managedSubAdminPassword,
        full_name: MANAGED_SUB_ADMIN_FULL_NAME,
        role: 'sub_admin',
        company_id: creatorSubAdmin.company_id || fallbackViewer.company_id,
        department_id: creatorSubAdmin.department_id || fallbackViewer.department_id,
        managed_kb_root_node_id: createdManagedRootId,
        tool_ids: [],
        status: 'active',
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      },
    });
    if (!createSubAdminResponse.ok()) {
      const body = await createSubAdminResponse.text().catch(() => '');
      throw new Error(
        `create sub-admin failed for ${managedSubAdminUsername}: ${createSubAdminResponse.status()} ${body}`.trim()
      );
    }
    const createSubAdminBody = await createSubAdminResponse.json();
    createdSubAdminId = String(
      readUserEnvelope(
        createSubAdminBody,
        `create sub-admin returned invalid payload for ${managedSubAdminUsername}`
      ).user_id || ''
    ).trim();
    expect(createdSubAdminId).toBeTruthy();

    creatorSession = await loginApiAs(creatorSubAdminUsername, creatorSubAdminPassword);
    const createdFolder = await createGroupFolder(creatorSession.api, creatorSession.headers, {
      name: folderName,
    });
    folderId = String(createdFolder?.id || '').trim();
    expect(folderId).toBeTruthy();

    groupId = await createPermissionGroup(creatorSession.api, creatorSession.headers, {
      group_name: groupName,
      description: 'Folder visibility across sub-admins',
      folder_id: folderId,
      can_view_kb_config: false,
      can_view_tools: false,
    });
    expect(groupId).toBeGreaterThan(0);

    managedSubAdminSession = await loginApiAs(managedSubAdminUsername, managedSubAdminPassword);
    managedSubAdminUi = await openSessionPage(browser, managedSubAdminSession);
    const { page } = managedSubAdminUi;

    const initialGroupsResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'GET'
      && /\/api\/permission-groups(?:\?|$)/.test(response.url())
    ), { timeout: 30_000 });
    const initialFoldersResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'GET'
      && /\/api\/permission-groups\/resources\/group-folders(?:\?|$)/.test(response.url())
    ), { timeout: 30_000 });
    const initialKnowledgeTreeResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'GET'
      && /\/api\/permission-groups\/resources\/knowledge-tree(?:\?|$)/.test(response.url())
    ), { timeout: 30_000 });
    const initialChatsResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'GET'
      && /\/api\/permission-groups\/resources\/chats(?:\?|$)/.test(response.url())
    ), { timeout: 30_000 });

    await page.goto(`${FRONTEND_BASE_URL}/permission-groups`);
    await expect(page.getByTestId('pg-toolbar-actions')).toBeVisible();
    await expect((await initialGroupsResponsePromise).ok()).toBeTruthy();
    await expect((await initialFoldersResponsePromise).ok()).toBeTruthy();
    await expect((await initialKnowledgeTreeResponsePromise).ok()).toBeTruthy();
    await expect((await initialChatsResponsePromise).ok()).toBeTruthy();

    const sharedFolderButton = page.getByRole('button', {
      name: new RegExp(escapeRegex(folderName)),
    }).first();
    await expect(sharedFolderButton).toBeVisible({ timeout: 30_000 });
    await sharedFolderButton.click();

    await expect(page.getByTestId('pg-tree-edit-' + toSafeId(groupId))).toHaveCount(0);
    await expect(page.getByTestId('pg-toolbar-create-folder')).toBeDisabled();
    await expect(page.getByTestId('pg-toolbar-rename-folder')).toBeDisabled();
    await expect(page.getByTestId('pg-toolbar-delete-folder')).toBeDisabled();
  } finally {
    if (managedSubAdminUi) await managedSubAdminUi.context.close();
    if (managedSubAdminSession) await managedSubAdminSession.api.dispose();

    if (creatorSession && groupId > 0) {
      await deletePermissionGroup(creatorSession.api, creatorSession.headers, groupId).catch(() => {});
    }
    if (creatorSession && folderId) {
      await deleteGroupFolder(creatorSession.api, creatorSession.headers, folderId).catch(() => {});
    }
    if (creatorSession) await creatorSession.api.dispose();

    if (adminSession) {
      if (createdSubAdminId) {
        await deleteUserById(adminSession.api, adminSession.headers, createdSubAdminId).catch(() => {});
      } else {
        await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, managedSubAdminUsername).catch(() => {});
      }
      if (createdManagedRootId) {
        await deleteKnowledgeDirectory(adminSession.api, adminSession.headers, createdManagedRootId).catch(() => {});
      }
      await adminSession.api.dispose();
    }
  }
});
