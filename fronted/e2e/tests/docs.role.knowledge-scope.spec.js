// @ts-check
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { createTempTextFixture } = require('../helpers/documentFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const {
  FRONTEND_BASE_URL,
  approveOperationRequestViaApi,
  listDatasets,
  loginApiAs,
  openBrowserDataset,
  pollSearchToken,
  toSafeId,
  uploadKnowledgeFileViaApi,
  waitForBrowserDocument,
  waitForOperationRequest,
} = require('../helpers/docRealFlow');

const summary = loadBootstrapSummary();
const adminPassword = process.env.E2E_ADMIN_PASS || 'admin123';
const subAdminPassword = process.env.E2E_SUB_ADMIN_PASS || adminPassword;
const reviewerPassword = process.env.E2E_REVIEWER_PASS || adminPassword;
const viewerPassword = process.env.E2E_VIEWER_PASS || adminPassword;
const uploaderPassword = process.env.E2E_UPLOADER_PASS || adminPassword;

async function readJson(response, message) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${message}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

async function createDirectory(api, headers, { name, parentId }) {
  const response = await api.post('/api/knowledge/directories', {
    headers,
    data: { name, parent_id: parentId || null },
  });
  const payload = await readJson(response, `create directory failed for ${name}`);
  const nodeId = String(payload?.node?.id || '').trim();
  if (!nodeId) {
    throw new Error(`create directory did not return node id for ${name}`);
  }
  return payload.node;
}

async function createDataset(api, headers, { name, nodeId }) {
  const response = await api.post('/api/datasets', {
    headers,
    data: { name, node_id: nodeId || null },
  });
  const payload = await readJson(response, `create dataset failed for ${name}`);
  const datasetId = String(payload?.dataset?.id || '').trim();
  if (!datasetId) {
    throw new Error(`create dataset did not return dataset id for ${name}`);
  }
  return payload.dataset;
}

async function createPermissionGroup(api, headers, payload) {
  const response = await api.post('/api/permission-groups', { headers, data: payload });
  const body = await readJson(response, `create permission group failed for ${payload.group_name}`);
  const groupId = Number(body?.data?.group_id || 0);
  if (!Number.isInteger(groupId) || groupId <= 0) {
    throw new Error(`create permission group did not return group_id for ${payload.group_name}`);
  }
  return groupId;
}

async function deletePermissionGroup(api, headers, groupId) {
  const response = await api.delete(`/api/permission-groups/${groupId}`, { headers });
  await readJson(response, `delete permission group failed for ${groupId}`);
}

async function getUser(api, headers, userId) {
  const response = await api.get(`/api/users/${encodeURIComponent(userId)}`, { headers });
  return readJson(response, `get user failed for ${userId}`);
}

async function updateUserGroups(api, headers, userId, groupIds) {
  const response = await api.put(`/api/users/${encodeURIComponent(userId)}`, {
    headers,
    data: { group_ids: groupIds },
  });
  return readJson(response, `update user groups failed for ${userId}`);
}

test('Role knowledge scope shows real browser and search differences for different users @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  const stamp = Date.now();
  const dirAName = `doc_scope_dir_a_${stamp}`;
  const dirBName = `doc_scope_dir_b_${stamp}`;
  const kbAName = `doc_scope_kb_a_${stamp}`;
  const kbBName = `doc_scope_kb_b_${stamp}`;
  const groupAName = `doc_scope_group_a_${stamp}`;
  const groupBName = `doc_scope_group_b_${stamp}`;
  const docAFx = createTempTextFixture('doc-scope-a');
  const docBFx = createTempTextFixture('doc-scope-b');

  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let subAdminSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let reviewerSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let viewerSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let uploaderSession = null;
  /** @type {{ context: import('@playwright/test').BrowserContext, page: import('@playwright/test').Page } | null} */
  let viewerUi = null;
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
      ? viewerUser.group_ids.map((groupId) => Number(groupId)).filter((groupId) => Number.isInteger(groupId) && groupId > 0)
      : [];
    originalUploaderGroups = Array.isArray(uploaderUser?.group_ids)
      ? uploaderUser.group_ids.map((groupId) => Number(groupId)).filter((groupId) => Number.isInteger(groupId) && groupId > 0)
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
      meaning: 'Scope doc A approval',
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
      meaning: 'Scope doc B approval',
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
      description: 'Doc scope group A',
      accessible_kbs: [String(datasetA.id)],
      can_upload: true,
      can_download: true,
      can_view_kb_config: false,
      can_view_tools: false,
    });
    createdGroupIds.push(groupAId);

    const groupBId = await createPermissionGroup(subAdminSession.api, subAdminSession.headers, {
      group_name: groupBName,
      description: 'Doc scope group B',
      accessible_kbs: [String(datasetB.id)],
      can_upload: true,
      can_download: true,
      can_view_kb_config: false,
      can_view_tools: false,
    });
    createdGroupIds.push(groupBId);

    await updateUserGroups(
      subAdminSession.api,
      subAdminSession.headers,
      summary.users.viewer.user_id,
      [groupAId]
    );
    await updateUserGroups(
      subAdminSession.api,
      subAdminSession.headers,
      summary.users.uploader.user_id,
      [groupBId]
    );

    await viewerSession.api.dispose();
    await uploaderSession.api.dispose();
    viewerSession = await loginApiAs(summary.users.viewer.username, viewerPassword);
    uploaderSession = await loginApiAs(summary.users.uploader.username, uploaderPassword);

    const viewerDatasets = await listDatasets(viewerSession.api, viewerSession.headers);
    const uploaderDatasets = await listDatasets(uploaderSession.api, uploaderSession.headers);
    expect(viewerDatasets.map((dataset) => String(dataset.id))).toEqual([String(datasetA.id)]);
    expect(uploaderDatasets.map((dataset) => String(dataset.id))).toEqual([String(datasetB.id)]);

    viewerUi = await openSessionPage(browser, viewerSession);
    await viewerUi.page.goto(`${FRONTEND_BASE_URL}/browser`);
    await expect(viewerUi.page.getByTestId('browser-page')).toBeVisible();
    await expect(viewerUi.page.getByTestId(`browser-quick-dataset-${toSafeId(datasetA.id)}`)).toBeVisible();
    await expect(viewerUi.page.getByTestId(`browser-quick-dataset-${toSafeId(datasetB.id)}`)).toHaveCount(0);
    await openBrowserDataset(viewerUi.page, datasetA);
    await expect(await waitForBrowserDocument(viewerUi.page, {
      dataset: datasetA,
      filename: docAFx.filename,
      timeoutMs: 180_000,
    })).toContainText(docAFx.filename);

    uploaderUi = await openSessionPage(browser, uploaderSession);
    await uploaderUi.page.goto(`${FRONTEND_BASE_URL}/browser`);
    await expect(uploaderUi.page.getByTestId('browser-page')).toBeVisible();
    await expect(uploaderUi.page.getByTestId(`browser-quick-dataset-${toSafeId(datasetB.id)}`)).toBeVisible();
    await expect(uploaderUi.page.getByTestId(`browser-quick-dataset-${toSafeId(datasetA.id)}`)).toHaveCount(0);
    await openBrowserDataset(uploaderUi.page, datasetB);
    await expect(await waitForBrowserDocument(uploaderUi.page, {
      dataset: datasetB,
      filename: docBFx.filename,
      timeoutMs: 180_000,
    })).toContainText(docBFx.filename);

    const searchAOwn = await pollSearchToken(viewerSession.api, viewerSession.headers, {
      question: docAFx.token,
      datasetIds: [String(datasetA.id)],
      token: docAFx.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    expect(searchAOwn.ok, searchAOwn.lastError || JSON.stringify(searchAOwn.lastPayload || {})).toBeTruthy();

    const searchAOther = await pollSearchToken(viewerSession.api, viewerSession.headers, {
      question: docBFx.token,
      datasetIds: [String(datasetA.id)],
      token: docBFx.token,
      expectFound: false,
      timeoutMs: 30_000,
    });
    expect(searchAOther.ok, searchAOther.lastError || JSON.stringify(searchAOther.lastPayload || {})).toBeTruthy();

    const searchBOwn = await pollSearchToken(uploaderSession.api, uploaderSession.headers, {
      question: docBFx.token,
      datasetIds: [String(datasetB.id)],
      token: docBFx.token,
      expectFound: true,
      timeoutMs: 180_000,
    });
    expect(searchBOwn.ok, searchBOwn.lastError || JSON.stringify(searchBOwn.lastPayload || {})).toBeTruthy();

    const searchBOther = await pollSearchToken(uploaderSession.api, uploaderSession.headers, {
      question: docAFx.token,
      datasetIds: [String(datasetB.id)],
      token: docAFx.token,
      expectFound: false,
      timeoutMs: 30_000,
    });
    expect(searchBOther.ok, searchBOther.lastError || JSON.stringify(searchBOther.lastPayload || {})).toBeTruthy();
  } finally {
    if (subAdminSession) {
      await updateUserGroups(
        subAdminSession.api,
        subAdminSession.headers,
        summary.users.viewer.user_id,
        originalViewerGroups
      );
      await updateUserGroups(
        subAdminSession.api,
        subAdminSession.headers,
        summary.users.uploader.user_id,
        originalUploaderGroups
      );
      for (const groupId of createdGroupIds.reverse()) {
        await deletePermissionGroup(subAdminSession.api, subAdminSession.headers, groupId);
      }
    }
    if (viewerUi) await viewerUi.context.close();
    if (uploaderUi) await uploaderUi.context.close();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (reviewerSession) await reviewerSession.api.dispose();
    if (viewerSession) await viewerSession.api.dispose();
    if (uploaderSession) await uploaderSession.api.dispose();
    docAFx.cleanup();
    docBFx.cleanup();
  }
});
