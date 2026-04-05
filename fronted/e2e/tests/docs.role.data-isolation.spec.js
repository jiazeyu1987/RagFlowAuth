// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { createTempTextFixture } = require('../helpers/documentFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const {
  FRONTEND_BASE_URL,
  approveOperationRequestViaApi,
  loginApiAs,
  pollSearchToken,
  uploadKnowledgeFileViaApi,
  waitForOperationRequest,
} = require('../helpers/docRealFlow');
const {
  createDataset,
  createDirectory,
  createPermissionGroup,
  deletePermissionGroup,
  expectUnauthorizedRoute,
  getUser,
  updateUserGroups,
} = require('../helpers/searchChatFlow');

const summary = loadBootstrapSummary();
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
const subAdminPassword = process.env.E2E_SUB_ADMIN_PASS || adminPassword;
const reviewerPassword = process.env.E2E_REVIEWER_PASS || adminPassword;
const viewerPassword = process.env.E2E_VIEWER_PASS || adminPassword;
const uploaderPassword = process.env.E2E_UPLOADER_PASS || adminPassword;

test('Doc Role: real route guard and search/chat data isolation across accounts @doc-e2e', async ({ browser }) => {
  test.setTimeout(420_000);

  const stamp = Date.now();
  const dirAName = `doc_role_iso_dir_a_${stamp}`;
  const dirBName = `doc_role_iso_dir_b_${stamp}`;
  const kbAName = `doc_role_iso_kb_a_${stamp}`;
  const kbBName = `doc_role_iso_kb_b_${stamp}`;
  const groupAName = `doc_role_iso_group_a_${stamp}`;
  const groupBName = `doc_role_iso_group_b_${stamp}`;
  const docAFx = createTempTextFixture('doc-role-iso-a');
  const docBFx = createTempTextFixture('doc-role-iso-b');

  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let subAdminSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let reviewerSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let viewerSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let uploaderSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let uploaderUi = null;
  /** @type {number[]} */
  let originalViewerGroups = [];
  /** @type {number[]} */
  let originalUploaderGroups = [];
  /** @type {number[]} */
  const createdGroupIds = [];

  try {
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, subAdminPassword);
    reviewerSession = await loginApiAs(summary.users.reviewer.username, reviewerPassword);
    viewerSession = await loginApiAs(summary.users.viewer.username, viewerPassword);
    uploaderSession = await loginApiAs(summary.users.uploader.username, uploaderPassword);

    const viewerUser = await getUser(subAdminSession.api, subAdminSession.headers, summary.users.viewer.user_id);
    const uploaderUser = await getUser(subAdminSession.api, subAdminSession.headers, summary.users.uploader.user_id);
    originalViewerGroups = Array.isArray(viewerUser?.group_ids)
      ? viewerUser.group_ids.map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0)
      : [];
    originalUploaderGroups = Array.isArray(uploaderUser?.group_ids)
      ? uploaderUser.group_ids.map((id) => Number(id)).filter((id) => Number.isInteger(id) && id > 0)
      : [];

    const dirA = await createDirectory(subAdminSession.api, subAdminSession.headers, {
      name: dirAName,
      parentId: summary.knowledge.managed_root_node_id,
    });
    const dirB = await createDirectory(subAdminSession.api, subAdminSession.headers, {
      name: dirBName,
      parentId: summary.knowledge.managed_root_node_id,
    });
    const datasetA = await createDataset(subAdminSession.api, subAdminSession.headers, {
      name: kbAName,
      nodeId: dirA.id,
    });
    const datasetB = await createDataset(subAdminSession.api, subAdminSession.headers, {
      name: kbBName,
      nodeId: dirB.id,
    });

    const uploadA = await uploadKnowledgeFileViaApi(subAdminSession.api, subAdminSession.headers, {
      kbRef: String(datasetA.id),
      filePath: docAFx.filePath,
      mimeType: 'text/plain',
    });
    const requestA = String(uploadA?.request_id || '').trim();
    expect(requestA).toBeTruthy();
    await approveOperationRequestViaApi(reviewerSession.api, reviewerSession.headers, {
      requestId: requestA,
      password: reviewerPassword,
      meaning: 'Role iso A approval',
      reason: `Approve ${docAFx.filename}`,
    });
    const executedA = await waitForOperationRequest(
      reviewerSession.api,
      reviewerSession.headers,
      requestA,
      (detail) => (
        ['executed', 'execution_failed', 'rejected', 'withdrawn'].includes(String(detail?.status || ''))
          ? detail
          : null
      ),
      { timeoutMs: 240_000, intervalMs: 2_000 }
    );
    expect(String(executedA?.status || '')).toBe('executed');

    const uploadB = await uploadKnowledgeFileViaApi(subAdminSession.api, subAdminSession.headers, {
      kbRef: String(datasetB.id),
      filePath: docBFx.filePath,
      mimeType: 'text/plain',
    });
    const requestB = String(uploadB?.request_id || '').trim();
    expect(requestB).toBeTruthy();
    await approveOperationRequestViaApi(reviewerSession.api, reviewerSession.headers, {
      requestId: requestB,
      password: reviewerPassword,
      meaning: 'Role iso B approval',
      reason: `Approve ${docBFx.filename}`,
    });
    const executedB = await waitForOperationRequest(
      reviewerSession.api,
      reviewerSession.headers,
      requestB,
      (detail) => (
        ['executed', 'execution_failed', 'rejected', 'withdrawn'].includes(String(detail?.status || ''))
          ? detail
          : null
      ),
      { timeoutMs: 240_000, intervalMs: 2_000 }
    );
    expect(String(executedB?.status || '')).toBe('executed');

    const groupAId = await createPermissionGroup(subAdminSession.api, subAdminSession.headers, {
      group_name: groupAName,
      description: 'Role data isolation group A',
      accessible_kbs: [String(datasetA.id)],
      can_upload: true,
      can_download: true,
      can_view_kb_config: false,
      can_view_tools: false,
    });
    createdGroupIds.push(groupAId);
    const groupBId = await createPermissionGroup(subAdminSession.api, subAdminSession.headers, {
      group_name: groupBName,
      description: 'Role data isolation group B',
      accessible_kbs: [String(datasetB.id)],
      can_upload: true,
      can_download: true,
      can_view_kb_config: false,
      can_view_tools: false,
    });
    createdGroupIds.push(groupBId);

    await updateUserGroups(subAdminSession.api, subAdminSession.headers, summary.users.viewer.user_id, [groupAId]);
    await updateUserGroups(subAdminSession.api, subAdminSession.headers, summary.users.uploader.user_id, [groupBId]);

    await viewerSession.api.dispose();
    await uploaderSession.api.dispose();
    viewerSession = await loginApiAs(summary.users.viewer.username, viewerPassword);
    uploaderSession = await loginApiAs(summary.users.uploader.username, uploaderPassword);

    const viewerSearchOwn = await pollSearchToken(viewerSession.api, viewerSession.headers, {
      question: docAFx.token,
      datasetIds: [String(datasetA.id)],
      token: docAFx.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    expect(viewerSearchOwn.ok, viewerSearchOwn.lastError || JSON.stringify(viewerSearchOwn.lastPayload || {})).toBeTruthy();
    const viewerSearchOther = await pollSearchToken(viewerSession.api, viewerSession.headers, {
      question: docBFx.token,
      datasetIds: [String(datasetA.id)],
      token: docBFx.token,
      expectFound: false,
      timeoutMs: 40_000,
    });
    expect(viewerSearchOther.ok, viewerSearchOther.lastError || JSON.stringify(viewerSearchOther.lastPayload || {})).toBeTruthy();

    const uploaderSearchOwn = await pollSearchToken(uploaderSession.api, uploaderSession.headers, {
      question: docBFx.token,
      datasetIds: [String(datasetB.id)],
      token: docBFx.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    expect(uploaderSearchOwn.ok, uploaderSearchOwn.lastError || JSON.stringify(uploaderSearchOwn.lastPayload || {})).toBeTruthy();
    const uploaderSearchOther = await pollSearchToken(uploaderSession.api, uploaderSession.headers, {
      question: docAFx.token,
      datasetIds: [String(datasetB.id)],
      token: docAFx.token,
      expectFound: false,
      timeoutMs: 40_000,
    });
    expect(uploaderSearchOther.ok, uploaderSearchOther.lastError || JSON.stringify(uploaderSearchOther.lastPayload || {})).toBeTruthy();

    uploaderUi = await openSessionPage(browser, uploaderSession);
    await expectUnauthorizedRoute(uploaderUi.page, '/users');
  } finally {
    if (subAdminSession) {
      await updateUserGroups(subAdminSession.api, subAdminSession.headers, summary.users.viewer.user_id, originalViewerGroups);
      await updateUserGroups(subAdminSession.api, subAdminSession.headers, summary.users.uploader.user_id, originalUploaderGroups);
      for (const groupId of createdGroupIds.reverse()) {
        await deletePermissionGroup(subAdminSession.api, subAdminSession.headers, groupId);
      }
    }
    if (uploaderUi) await uploaderUi.context.close();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (reviewerSession) await reviewerSession.api.dispose();
    if (viewerSession) await viewerSession.api.dispose();
    if (uploaderSession) await uploaderSession.api.dispose();
    docAFx.cleanup();
    docBFx.cleanup();
  }
});
