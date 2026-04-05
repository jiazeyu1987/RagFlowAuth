// @ts-check
const { expect } = require('@playwright/test');
const { docSubAdminTest } = require('../helpers/docAuth');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { createTempTextFixture } = require('../helpers/documentFlow');
const {
  FRONTEND_BASE_URL,
  approveOperationRequestViaApi,
  listDatasets,
  loginApiAs,
  toSafeId,
  uploadKnowledgeFileViaApi,
  waitForOperationRequest,
  waitForOperationRequestStatus,
  withdrawOperationRequestViaApi,
} = require('../helpers/docRealFlow');

const summary = loadBootstrapSummary();
const subAdminPassword = process.env.E2E_SUB_ADMIN_PASS || process.env.E2E_ADMIN_PASS || 'admin123';
const reviewerPassword = process.env.E2E_REVIEWER_PASS || process.env.E2E_ADMIN_PASS || 'admin123';

async function openDirectoryFromTree(page, nodeId) {
  const node = page.getByTestId(`kbs-tree-node-${toSafeId(nodeId)}`);
  await expect(node).toBeVisible();
  await node.click();
  return node;
}

docSubAdminTest('Knowledge-base config covers real directory create/rename, KB create/save, non-empty delete guard, and empty delete approval @doc-e2e', async ({ page }, testInfo) => {
  testInfo.setTimeout(300_000);

  const seedFx = createTempTextFixture('doc-kbs-non-empty');
  const stamp = Date.now();
  const createdDirName = `doc_kbs_dir_${stamp}`;
  const renamedDirName = `doc_kbs_dir_renamed_${stamp}`;
  const primaryKbName = `doc_kbs_primary_${stamp}`;
  const savedKbName = `doc_kbs_saved_${stamp}`;
  const emptyKbName = `doc_kbs_empty_${stamp}`;
  let primaryKbId = '';
  let emptyKbId = '';
  let deleteRequestId = '';
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let subAdminSession = null;
  /** @type {ReturnType<typeof loginApiAs> extends Promise<infer T> ? T : never | null} */
  let reviewerSession = null;

  try {
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, subAdminPassword);
    reviewerSession = await loginApiAs(summary.users.reviewer.username, reviewerPassword);

    await page.goto(`${FRONTEND_BASE_URL}/kbs`);
    await expect(page.getByTestId('kbs-subtab-kbs')).toBeVisible();
    await page.getByTestId('kbs-subtab-kbs').click();
    await openDirectoryFromTree(page, summary.knowledge.managed_root_node_id);

    const createDirResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes('/api/knowledge/directories')
    ));
    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('prompt');
      await dialog.accept(createdDirName);
    });
    await page.getByTestId('kbs-create-dir').click();
    const createDirResponse = await createDirResponsePromise;
    await expect(createDirResponse.ok()).toBeTruthy();
    const createDirBody = await createDirResponse.json();
    const dirId = String(createDirBody?.node?.id || '').trim();
    expect(dirId).toBeTruthy();

    const dirNode = await openDirectoryFromTree(page, dirId);

    const renameDirResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'PUT'
      && response.url().includes(`/api/knowledge/directories/${encodeURIComponent(dirId)}`)
    ));
    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('prompt');
      await dialog.accept(renamedDirName);
    });
    await page.getByTestId('kbs-rename-dir').click();
    await expect((await renameDirResponsePromise).ok()).toBeTruthy();
    await expect(dirNode).toContainText(renamedDirName);

    await page.getByTestId('kbs-create-kb').click();
    const primaryDialog = page.getByTestId('create-kb-dialog');
    await expect(primaryDialog).toBeVisible();
    await primaryDialog.getByTestId('create-kb-name-input').fill(primaryKbName);
    await primaryDialog.getByTestId('create-kb-dir-select').selectOption(dirId);

    const createPrimaryKbResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && /\/api\/datasets$/.test(new URL(response.url()).pathname)
    ));
    await primaryDialog.getByTestId('create-kb-confirm').click();
    const createPrimaryKbResponse = await createPrimaryKbResponsePromise;
    await expect(createPrimaryKbResponse.ok()).toBeTruthy();
    const createPrimaryKbBody = await createPrimaryKbResponse.json();
    primaryKbId = String(createPrimaryKbBody?.dataset?.id || '').trim();
    expect(primaryKbId).toBeTruthy();

    const primaryRow = page.getByTestId(`kbs-row-dataset-${toSafeId(primaryKbId)}`);
    await expect(primaryRow).toBeVisible();
    await primaryRow.click();

    await page.getByTestId('kbs-name-input').fill(savedKbName);
    const saveResponses = Promise.all([
      page.waitForResponse((response) => (
        response.request().method() === 'PUT'
        && response.url().includes(`/api/datasets/${encodeURIComponent(primaryKbId)}`)
      )),
      page.waitForResponse((response) => (
        response.request().method() === 'PUT'
        && response.url().includes(`/api/knowledge/directories/datasets/${encodeURIComponent(primaryKbId)}/node`)
      )),
    ]);
    await page.getByTestId('kbs-save-kb').click();
    for (const response of await saveResponses) {
      await expect(response.ok()).toBeTruthy();
    }

    await expect.poll(async () => {
      const datasets = await listDatasets(subAdminSession.api, subAdminSession.headers);
      const matched = datasets.find((dataset) => String(dataset?.id || '') === primaryKbId);
      return String(matched?.name || '');
    }, { timeout: 60_000, intervals: [500, 1_000, 2_000] }).toBe(savedKbName);

    await page.getByTestId('kbs-refresh-all').click();
    await openDirectoryFromTree(page, summary.knowledge.managed_root_node_id);
    await openDirectoryFromTree(page, dirId);
    const refreshedPrimaryRow = page.getByTestId(`kbs-row-dataset-${toSafeId(primaryKbId)}`);
    await expect(refreshedPrimaryRow).toContainText(savedKbName);

    const uploadBrief = await uploadKnowledgeFileViaApi(subAdminSession.api, subAdminSession.headers, {
      kbRef: primaryKbId,
      filePath: seedFx.filePath,
      mimeType: 'text/plain',
    });
    const uploadRequestId = String(uploadBrief?.request_id || '').trim();
    expect(uploadRequestId).toBeTruthy();

    await approveOperationRequestViaApi(reviewerSession.api, reviewerSession.headers, {
      requestId: uploadRequestId,
      password: reviewerPassword,
      meaning: 'KB config seeded document approval',
      reason: `Approve ${seedFx.filename} for KB config coverage`,
    });
    const uploadRequest = await waitForOperationRequest(
      reviewerSession.api,
      reviewerSession.headers,
      uploadRequestId,
      (detail) => (
        ['executed', 'execution_failed', 'rejected', 'withdrawn'].includes(String(detail?.status || ''))
          ? detail
          : null
      ),
      { timeoutMs: 240_000, intervalMs: 2_000 }
    );
    expect(String(uploadRequest?.status || '')).toBe('executed');

    await page.getByTestId('kbs-refresh-all').click();
    await openDirectoryFromTree(page, summary.knowledge.managed_root_node_id);
    await openDirectoryFromTree(page, dirId);
    await page.getByTestId(`kbs-row-dataset-${toSafeId(primaryKbId)}`).click();
    await expect(page.getByTestId('kbs-delete-kb')).toBeDisabled({ timeout: 60_000 });

    await page.getByTestId('kbs-create-kb').click();
    const emptyDialog = page.getByTestId('create-kb-dialog');
    await expect(emptyDialog).toBeVisible();
    await emptyDialog.getByTestId('create-kb-name-input').fill(emptyKbName);
    await emptyDialog.getByTestId('create-kb-dir-select').selectOption(dirId);

    const createEmptyKbResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && /\/api\/datasets$/.test(new URL(response.url()).pathname)
    ));
    await emptyDialog.getByTestId('create-kb-confirm').click();
    const createEmptyKbResponse = await createEmptyKbResponsePromise;
    await expect(createEmptyKbResponse.ok()).toBeTruthy();
    const createEmptyKbBody = await createEmptyKbResponse.json();
    emptyKbId = String(createEmptyKbBody?.dataset?.id || '').trim();
    expect(emptyKbId).toBeTruthy();

    const emptyRow = page.getByTestId(`kbs-row-dataset-${toSafeId(emptyKbId)}`);
    await expect(emptyRow).toBeVisible();
    await emptyRow.click();

    const deleteEmptyKbResponsePromise = page.waitForResponse((response) => (
      response.request().method() === 'DELETE'
      && response.url().includes(`/api/datasets/${encodeURIComponent(emptyKbId)}`)
    ));
    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm');
      await dialog.accept();
    });
    await page.getByTestId('kbs-delete-kb').click();
    const deleteEmptyKbResponse = await deleteEmptyKbResponsePromise;
    await expect(deleteEmptyKbResponse.ok()).toBeTruthy();
    const deleteEmptyKbBody = await deleteEmptyKbResponse.json();
    deleteRequestId = String(deleteEmptyKbBody?.request_id || '').trim();
    expect(deleteRequestId).toBeTruthy();

    await waitForOperationRequestStatus(
      subAdminSession.api,
      subAdminSession.headers,
      deleteRequestId,
      'in_approval',
      { timeoutMs: 60_000, intervalMs: 1_000 }
    );
    await expect(emptyRow).toBeVisible();
  } finally {
    if (subAdminSession && deleteRequestId) {
      await withdrawOperationRequestViaApi(subAdminSession.api, subAdminSession.headers, {
        requestId: deleteRequestId,
        reason: 'Doc KB config cleanup',
      });
    }
    if (subAdminSession) await subAdminSession.api.dispose();
    if (reviewerSession) await reviewerSession.api.dispose();
    seedFx.cleanup();
  }
});
