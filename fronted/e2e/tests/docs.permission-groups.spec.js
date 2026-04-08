// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { openSessionPage } = require('../helpers/docSessionPage');
const { toSafeId } = require('../helpers/docRealFlow');
const { loginApiAs } = require('../helpers/permissionGroupsFlow');

const summary = loadBootstrapSummary();
const FRONTEND_BASE_URL = process.env.E2E_FRONTEND_BASE_URL || 'http://127.0.0.1:33002';
const subAdminPassword = process.env.E2E_SUB_ADMIN_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

function escapeRegex(value) {
  return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

test('Permission groups page covers real folder create/rename/delete and group create/edit/delete @doc-e2e', async ({ browser }) => {
  test.setTimeout(180_000);
  const stamp = Date.now();
  const folderName = `doc_pg_folder_${stamp}`;
  const renamedFolderName = `doc_pg_folder_renamed_${stamp}`;
  const groupName = `doc_pg_group_${stamp}`;
  const updatedDescription = `updated description ${stamp}`;
  let folderId = '';
  let groupId = 0;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let subAdminSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let subAdminUi = null;

  try {
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, subAdminPassword);
    subAdminUi = await openSessionPage(browser, subAdminSession);
    const { page } = subAdminUi;
    await page.goto(`${FRONTEND_BASE_URL}/permission-groups`);
    await expect(page.getByTestId('pg-toolbar-actions')).toBeVisible();
    await expect(page.getByTestId('pg-create-open')).toBeVisible();

    const createFolderResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && /\/api\/permission-groups\/folders(?:\?|$)/.test(response.url())
    ), { timeout: 20_000 });
    page.once('dialog', async (dialog) => {
      await dialog.accept(folderName);
    });
    await page.getByTestId('pg-toolbar-create-folder').click();
    const createFolderResponse = await createFolderResponsePromise;
    await expect(createFolderResponse.ok()).toBeTruthy();
    const createFolderBody = await createFolderResponse.json();
    folderId = String(createFolderBody?.folder?.id || '').trim();
    expect(folderId).toBeTruthy();
    await expect(
      page.getByRole('button', { name: new RegExp(escapeRegex(folderName)) }).first()
    ).toBeVisible();

    await page.getByRole('button', { name: new RegExp(escapeRegex(folderName)) }).first().click();
    await expect(page.getByTestId('pg-toolbar-rename-folder')).toBeEnabled();
    await expect(page.getByTestId('pg-toolbar-delete-folder')).toBeEnabled();

    const renameFolderResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`)
    ), { timeout: 20_000 });
    page.once('dialog', async (dialog) => {
      await dialog.accept(renamedFolderName);
    });
    await page.getByTestId('pg-toolbar-rename-folder').click();
    await expect((await renameFolderResponsePromise).ok()).toBeTruthy();
    await expect(
      page.getByRole('button', { name: new RegExp(escapeRegex(renamedFolderName)) }).first()
    ).toBeVisible();

    await page.getByTestId('pg-create-open').click();
    await page.getByTestId('pg-form-group-name').fill(groupName);
    await page.getByTestId('pg-form-description').fill(`created description ${stamp}`);
    await page.getByTestId('pg-form-can-upload').check();

    const createGroupResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && /\/api\/permission-groups(?:\?|$)/.test(response.url())
    ), { timeout: 20_000 });
    await page.getByTestId('pg-form-submit').click();
    const createGroupResponse = await createGroupResponsePromise;
    await expect(createGroupResponse.ok()).toBeTruthy();
    const createGroupBody = await createGroupResponse.json();
    groupId = Number(createGroupBody?.result?.group_id || 0);
    expect(groupId).toBeGreaterThan(0);
    await expect(page.getByTestId(`pg-tree-edit-${toSafeId(groupId)}`)).toBeVisible();

    await page.getByTestId(`pg-tree-edit-${toSafeId(groupId)}`).click();
    await expect(page.getByTestId('pg-form-group-name')).toHaveValue(groupName);
    await page.getByTestId('pg-form-description').fill(updatedDescription);
    await page.getByTestId('pg-form-can-upload').uncheck();
    await page.getByTestId('pg-form-can-delete').check();

    const updateGroupResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes(`/api/permission-groups/${groupId}`)
    ), { timeout: 20_000 });
    await page.getByTestId('pg-form-submit').click();
    await expect((await updateGroupResponsePromise).ok()).toBeTruthy();

    await page.getByTestId(`pg-tree-edit-${toSafeId(groupId)}`).click();
    await expect(page.getByTestId('pg-form-description')).toHaveValue(updatedDescription);
    await expect(page.getByTestId('pg-form-can-upload')).not.toBeChecked();
    await expect(page.getByTestId('pg-form-can-delete')).toBeChecked();

    const deleteGroupResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'DELETE'
      && response.url().includes(`/api/permission-groups/${groupId}`)
    ), { timeout: 20_000 });
    await page.getByTestId(`pg-tree-delete-${toSafeId(groupId)}`).click();
    await page.getByTestId('pg-delete-confirm').click();
    await expect((await deleteGroupResponsePromise).ok()).toBeTruthy();
    await expect(page.getByTestId(`pg-tree-edit-${toSafeId(groupId)}`)).toHaveCount(0);
    groupId = 0;

    await page.getByRole('button', { name: new RegExp(escapeRegex(renamedFolderName)) }).first().click();
    await expect(page.getByTestId('pg-toolbar-delete-folder')).toBeEnabled();
    const deleteFolderResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'DELETE'
      && response.url().includes(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`)
    ), { timeout: 20_000 });
    page.once('dialog', async (dialog) => {
      await dialog.accept();
    });
    await page.getByTestId('pg-toolbar-delete-folder').click();
    await expect((await deleteFolderResponsePromise).ok()).toBeTruthy();
    await expect(
      page.getByRole('button', { name: new RegExp(escapeRegex(renamedFolderName)) }).first()
    ).toHaveCount(0);
    folderId = '';
  } finally {
    if (subAdminUi) {
      await subAdminUi.context.close();
    }
    if (subAdminSession && groupId > 0) {
      await subAdminSession.api.delete(`/api/permission-groups/${groupId}`, {
        headers: subAdminSession.headers,
      }).catch(() => {});
    }
    if (subAdminSession && folderId) {
      await subAdminSession.api.delete(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`, {
        headers: subAdminSession.headers,
      }).catch(() => {});
    }
    if (subAdminSession) {
      await subAdminSession.api.dispose();
    }
  }
});
