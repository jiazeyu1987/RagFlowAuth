// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { loginApiAs, openLoggedInPage, FRONTEND_BASE_URL } = require('../helpers/docRealFlow');
const { preflightAdmin } = require('../helpers/integration');

const summary = loadBootstrapSummary();
const DEFAULT_PASSWORD = process.env.E2E_ADMIN_PASS || 'admin123';
const FILE_SUBTYPE = '\u6280\u672f\u8c03\u7814\u62a5\u544a';
const USAGE_SCOPE_FILE_SUBTYPE = '\u68c0\u9a8c\u7528\u5de5\u88c5\u6a21\u5177\u7ef4\u62a4\u4fdd\u517b\u89c4\u8303';

test.describe.configure({ mode: 'serial' });

function createPdfCopy(prefix) {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
  const filePath = path.join(tmpDir, `${prefix}.pdf`);
  fs.writeFileSync(
    filePath,
    Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n', 'utf8')
  );
  return {
    filePath,
    cleanup() {
      try {
        fs.rmSync(tmpDir, { recursive: true, force: true });
      } catch {
        // noop
      }
    },
  };
}

async function readJson(response, fallbackMessage) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${fallbackMessage}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

async function loadConfig(session) {
  const response = await session.api.get('/api/admin/quality-system-config', { headers: session.headers });
  return readJson(response, 'load quality system config failed');
}

async function putAssignments(session, positionId, userIds, reason) {
  const response = await session.api.put(
    `/api/admin/quality-system-config/positions/${positionId}/assignments`,
    {
      headers: session.headers,
      data: { user_ids: userIds, change_reason: reason },
    }
  );
  return readJson(response, `save assignments failed for position ${positionId}`);
}

async function listAssignableUsers(session) {
  const response = await session.api.get('/api/admin/quality-system-config/users?limit=200', {
    headers: session.headers,
  });
  return readJson(response, 'load assignable users failed');
}

async function approveRevisionStep(session, revisionId, note) {
  const response = await session.api.post(
    `/api/quality-system/doc-control/revisions/${encodeURIComponent(revisionId)}/approval/approve`,
    {
      headers: session.headers,
      data: { note },
    }
  );
  return readJson(response, `approve revision step failed for ${revisionId}`);
}

async function createControlledDocumentViaApi(session, payload) {
  const response = await session.api.post('/api/quality-system/doc-control/documents', {
    headers: session.headers,
    multipart: {
      doc_code: payload.docCode,
      title: payload.title,
      document_type: payload.documentType,
      file_subtype: payload.fileSubtype,
      target_kb_id: payload.targetKbId,
      product_name: payload.productName,
      registration_ref: payload.registrationRef || '',
      change_summary: payload.changeSummary || '',
      file: {
        name: path.basename(payload.filePath),
        mimeType: 'application/pdf',
        buffer: fs.readFileSync(payload.filePath),
      },
    },
  });
  return readJson(response, `create controlled document via api failed for ${payload.docCode}`);
}

function findNameByKeywords(items, keywords) {
  const list = Array.isArray(items) ? items : [];
  const terms = (Array.isArray(keywords) ? keywords : [keywords])
    .map((item) => String(item || '').trim())
    .filter(Boolean);
  return list.find((item) => {
    const name = String(item?.name || '').trim();
    return terms.every((term) => name.includes(term));
  }) || null;
}

async function waitForFileSubtypeOption(page, value) {
  const select = page.getByTestId('document-control-create-file-subtype');
  await expect(select).toBeVisible();
  await expect.poll(async () => {
    return await select.evaluate((node, expected) => (
      Array.from(node.options).some((option) => String(option.value) === String(expected))
    ), value);
  }).toBe(true);
}

test('real backend matrix flow generates and executes approval chain @integration', async ({ browser }) => {
  test.setTimeout(240_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const timestamp = Date.now();
  const docCode = `MATRIX-REAL-${timestamp}`;
  const title = `Matrix Real Flow ${timestamp}`;
  const targetKbId = String(summary?.knowledge?.dataset?.id || '').trim();
  if (!targetKbId) test.fail(true, 'bootstrap dataset id missing');

  const pdf = createPdfCopy(`matrix-real-${timestamp}`);

  let adminSession;
    let subAdminSession;
    let operatorSession;
    let adminUi;
    let subAdminUi;
  const originalAssignments = new Map();

  try {
    adminSession = await loginApiAs(summary.users.admin.username, DEFAULT_PASSWORD);
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, DEFAULT_PASSWORD);
    operatorSession = await loginApiAs(summary.users.operator.username, DEFAULT_PASSWORD);

    const config = await loadConfig(adminSession);
    const assignableUsers = await listAssignableUsers(adminSession);
    const requiredPositions = [
      '指定人员',
      'QMS',
      '编制部门负责人或授权代表',
    ];
    const positionsByName = new Map((config.positions || []).map((item) => [String(item.name), item]));
    const assignableByUsername = new Map((assignableUsers || []).map((item) => [String(item.username), item]));
    for (const name of requiredPositions) {
      if (!positionsByName.has(name)) {
        test.fail(true, `matrix position missing in config: ${name}`);
      }
    }

    const subAdminAssignable = assignableByUsername.get(summary.users.sub_admin.username);
    const operatorAssignable = assignableByUsername.get(summary.users.operator.username);

    if (!operatorAssignable || !subAdminAssignable) {
      test.skip(true, 'required assignable users missing from real quality system config users endpoint');
    }

    const assignmentPlan = [
      { name: '指定人员', userIds: [subAdminAssignable.user_id] },
      { name: 'QMS', userIds: [operatorAssignable.user_id] },
      { name: '编制部门负责人或授权代表', userIds: [operatorAssignable.user_id] },
    ];

    for (const item of assignmentPlan) {
      const position = positionsByName.get(item.name);
      originalAssignments.set(
        item.name,
        (position.assigned_users || []).map((user) => String(user.user_id))
      );
      await putAssignments(adminSession, position.id, item.userIds, `real matrix e2e setup ${timestamp}`);
    }

    subAdminUi = await openLoggedInPage(browser, summary.users.sub_admin.username, DEFAULT_PASSWORD);
    const operatorPage = subAdminUi.page;

    await operatorPage.goto(`${FRONTEND_BASE_URL}/quality-system/doc-control`);
    await expect(operatorPage.getByTestId('document-control-page')).toBeVisible();

    await operatorPage.getByTestId('document-control-create-doc-code').fill(docCode);
    await operatorPage.getByTestId('document-control-create-title').fill(title);
    await operatorPage.getByTestId('document-control-create-document-type').fill('dhf');
    await waitForFileSubtypeOption(operatorPage, FILE_SUBTYPE);
    await operatorPage.getByTestId('document-control-create-file-subtype').selectOption(FILE_SUBTYPE);
    await operatorPage.getByTestId('document-control-create-target-kb').fill(targetKbId);
    await operatorPage.getByTestId('document-control-create-product-name').fill('Matrix Product');
    await operatorPage.getByTestId('document-control-create-registration-ref').fill(`REG-${timestamp}`);
    await operatorPage.setInputFiles('[data-testid="document-control-create-file"]', pdf.filePath);

    const createResponsePromise = operatorPage.waitForResponse((response) =>
      response.request().method() === 'POST'
      && response.url().includes('/api/quality-system/doc-control/documents')
    );
    await operatorPage.getByTestId('document-control-create-submit').click();
    const createPayload = await readJson(await createResponsePromise, 'create controlled document failed');
    const createdDocument = createPayload.document;
    const revisionId = String(createdDocument?.current_revision?.controlled_revision_id || '').trim();
    expect(revisionId).toBeTruthy();

    await expect(operatorPage.getByTestId('document-control-success')).toContainText('Controlled document created');
    await expect(operatorPage.getByTestId('document-control-matrix-preview')).toBeVisible();
    await expect(operatorPage.getByTestId('document-control-matrix-preview-signoff')).toContainText('QMS');
    await expect(operatorPage.getByTestId('document-control-matrix-preview-compiler')).toContainText('项目负责人或指定人员');
    await expect(operatorPage.getByTestId('document-control-matrix-preview-approval')).toContainText(
      '编制部门负责人或授权代表'
    );

    const submitResponsePromise = operatorPage.waitForResponse((response) =>
      response.request().method() === 'POST'
      && response.url().includes(`/api/quality-system/doc-control/revisions/${encodeURIComponent(revisionId)}/approval/submit`)
    );
    await operatorPage.getByTestId('document-control-approval-submit').click();
    await readJson(await submitResponsePromise, 'submit revision for approval failed');
    await expect(operatorPage.getByTestId('document-control-workspace-status')).toContainText('approval in progress');
    await expect(operatorPage.getByTestId('document-control-approval-step-position')).toContainText('QMS');

    await approveRevisionStep(operatorSession, revisionId, 'qms approve');
    await operatorPage.reload();
    await expect(operatorPage.getByTestId('document-control-approval-step-position')).toContainText(
      '编制部门负责人或授权代表'
    );

    await approveRevisionStep(operatorSession, revisionId, 'final approve');

    await operatorPage.reload();
    await expect(operatorPage.getByTestId('document-control-workspace-status')).toContainText('approved pending effective');

    adminUi = await openLoggedInPage(browser, summary.users.admin.username, DEFAULT_PASSWORD);
    const adminPage = adminUi.page;
    await adminPage.goto(`${FRONTEND_BASE_URL}/logs`);
    await expect(adminPage.getByTestId('audit-logs-page')).toBeVisible();
    await adminPage.getByTestId('audit-filter-source').selectOption('document_control');
    await adminPage.getByTestId('audit-filter-action').selectOption('document_control_transition');
    await adminPage.getByTestId('audit-filter-resource-id').fill(revisionId);
    await adminPage.getByTestId('audit-apply').click();
    await expect(adminPage.getByTestId('audit-total')).not.toHaveText('0', { timeout: 30000 });
    await expect(adminPage.getByTestId('audit-table')).toContainText('文控审批流转');
    await expect(adminPage.getByTestId('audit-table')).toContainText(FILE_SUBTYPE);
  } finally {
    if (adminSession) {
      try {
        const config = await loadConfig(adminSession);
        const positionsByName = new Map((config.positions || []).map((item) => [String(item.name), item]));
        for (const [name, userIds] of originalAssignments.entries()) {
          const position = positionsByName.get(name);
          if (!position) continue;
          await putAssignments(adminSession, position.id, userIds, `real matrix e2e cleanup ${timestamp}`);
        }
      } catch {
        // noop: cleanup best effort in test environment
      }
    }
    if (adminUi) await adminUi.context.close();
    if (subAdminUi) await subAdminUi.context.close();
    if (adminSession) await adminSession.api.dispose();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (operatorSession) await operatorSession.api.dispose();
    pdf.cleanup();
  }
});



test('real backend matrix flow disables submit when matrix remark requires usage scope @integration', async ({ browser }) => {
  test.setTimeout(180_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const timestamp = Date.now();
  const docCode = `MATRIX-USAGE-${timestamp}`;
  const title = `Matrix Usage Scope ${timestamp}`;
  const targetKbId = String(summary?.knowledge?.dataset?.id || '').trim();
  if (!targetKbId) test.fail(true, 'bootstrap dataset id missing');

  const pdf = createPdfCopy(`matrix-usage-${timestamp}`);
  let adminSession;
  let subAdminSession;
  let subAdminUi;
  const originalAssignments = new Map();

  try {
    adminSession = await loginApiAs(summary.users.admin.username, DEFAULT_PASSWORD);
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, DEFAULT_PASSWORD);

    const config = await loadConfig(adminSession);
    const assignableUsers = await listAssignableUsers(adminSession);
    const positionsByName = new Map((config.positions || []).map((item) => [String(item.name), item]));
    const assignableByUsername = new Map((assignableUsers || []).map((item) => [String(item.username), item]));
    const subAdminAssignable = assignableByUsername.get(summary.users.sub_admin.username);
    if (!subAdminAssignable) {
      test.skip(true, 'sub_admin not available in assignable users endpoint');
    }

    const equipmentPosition = positionsByName.get('\u8bbe\u5907\u4eba\u5458') || findNameByKeywords(config.positions, ['??']);
    const usageScopeCategory =
      (config.file_categories || []).find((item) => String(item?.name || '') === USAGE_SCOPE_FILE_SUBTYPE)
      || findNameByKeywords(config.file_categories, ['???', '??????']);
    if (!equipmentPosition || !usageScopeCategory) {
      test.skip(true, 'usage-scope file category or equipment position missing in real quality system config');
    }

    for (const position of config.positions || []) {
      originalAssignments.set(
        String(position.name),
        (position.assigned_users || []).map((user) => String(user.user_id))
      );
      await putAssignments(
        adminSession,
        position.id,
        [subAdminAssignable.user_id],
        `real matrix usage-scope setup ${String(position.name)} ${timestamp}`
      );
    }

    subAdminUi = await openLoggedInPage(browser, summary.users.sub_admin.username, DEFAULT_PASSWORD);
    const page = subAdminUi.page;

    await page.goto(`${FRONTEND_BASE_URL}/quality-system/doc-control`);
    await expect(page.getByTestId('document-control-page')).toBeVisible();

    const created = await createControlledDocumentViaApi(subAdminSession, {
      docCode,
      title,
      documentType: 'dmr',
      fileSubtype: String(usageScopeCategory.name),
      targetKbId,
      productName: 'Usage Scope Product',
      registrationRef: '',
      changeSummary: 'usage scope validation',
      filePath: pdf.filePath,
    });
    const createdDocumentId = String(created?.document?.controlled_document_id || '').trim();
    const createdRevisionId = String(created?.document?.current_revision?.controlled_revision_id || '').trim();
    expect(createdDocumentId).toBeTruthy();
    expect(createdRevisionId).toBeTruthy();

    const previewResponse = await subAdminSession.api.get(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(createdRevisionId)}/matrix-preview`,
      { headers: subAdminSession.headers }
    );
    const previewPayload = await previewResponse.json().catch(() => ({}));
    console.log('usage_scope_preview_status', previewResponse.status(), 'payload', JSON.stringify(previewPayload));

    await page.getByTestId('document-control-filter-doc-code').fill(docCode);
    const searchResponse = page.waitForResponse((response) =>
      response.request().method() === 'GET'
      && response.url().includes('/api/quality-system/doc-control/documents?')
    );
    await page.getByTestId('document-control-search').click();
    await searchResponse;
    await page.getByTestId(`document-control-row-${createdDocumentId}`).click();

    await expect(page.getByTestId('document-control-matrix-preview-error')).toContainText(
      'This file subtype requires usage scope data before the approval matrix can be resolved.'
    );
    await expect(page.getByTestId('document-control-approval-submit')).toBeDisabled();
  } finally {
    if (adminSession) {
      try {
        const config = await loadConfig(adminSession);
        const positionsByName = new Map((config.positions || []).map((item) => [String(item.name), item]));
        for (const [name, userIds] of originalAssignments.entries()) {
          const position = positionsByName.get(name) || findNameByKeywords(config.positions, [name]);
          if (!position) continue;
          await putAssignments(adminSession, position.id, userIds, `real matrix usage-scope cleanup ${timestamp}`);
        }
      } catch {
        // noop: cleanup best effort in test environment
      }
    }
    if (subAdminUi) await subAdminUi.context.close();
    if (adminSession) await adminSession.api.dispose();
    if (subAdminSession) await subAdminSession.api.dispose();
    pdf.cleanup();
  }
});
