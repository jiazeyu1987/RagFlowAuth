// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { loginApiAs, FRONTEND_BASE_URL } = require('../helpers/docRealFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const { poll } = require('../helpers/documentFlow');
const {
  deleteUserById,
  readUserEnvelope,
  uniquePassword,
  uniqueUsername,
} = require('../helpers/userLifecycleFlow');

const summary = loadBootstrapSummary();
const PDF_SOURCE_PATH = 'C:\\Users\\BJB110\\Desktop\\文件控制流程初稿.pdf';
const DEFAULT_PASSWORD = process.env.E2E_ADMIN_PASS || 'admin123';

function requireExistingPdfSource() {
  if (!fs.existsSync(PDF_SOURCE_PATH)) {
    throw new Error(`pdf_source_missing:${PDF_SOURCE_PATH}`);
  }
  return PDF_SOURCE_PATH;
}

function createPdfCopy(prefix) {
  const sourcePath = requireExistingPdfSource();
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
  const filePath = path.join(tmpDir, `${prefix}.pdf`);
  fs.copyFileSync(sourcePath, filePath);
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

async function upsertDocumentTypeWorkflow(session, documentType, approverUserId, timeoutMinutes = 1) {
  const response = await session.api.put(
    `/api/quality-system/doc-control/workflows/${encodeURIComponent(documentType)}`,
    {
      headers: session.headers,
      data: {
        name: `Edge Branches ${documentType}`,
        steps: [
          {
            step_type: 'cosign',
            approval_rule: 'all',
            approver_user_ids: [String(approverUserId)],
            timeout_reminder_minutes: timeoutMinutes,
            member_source: 'fixed',
          },
          {
            step_type: 'approve',
            approval_rule: 'all',
            approver_user_ids: [String(approverUserId)],
            timeout_reminder_minutes: Math.max(timeoutMinutes, 5),
            member_source: 'fixed',
          },
          {
            step_type: 'standardize_review',
            approval_rule: 'all',
            approver_user_ids: [String(approverUserId)],
            timeout_reminder_minutes: Math.max(timeoutMinutes, 5),
            member_source: 'fixed',
          },
        ],
      },
    }
  );
  return readJson(response, `upsert workflow failed for ${documentType}`);
}

async function createTempAdminUser(session, { companyId, departmentId, employeeUserId, fullName }) {
  const username = uniqueUsername('doc_control_edge_admin');
  const password = uniquePassword('DocControlEdgeAdmin');
  const response = await session.api.post('/api/users', {
    headers: session.headers,
    data: {
      username,
      employee_user_id: employeeUserId,
      password,
      full_name: fullName,
      role: 'admin',
      company_id: companyId,
      department_id: departmentId,
      status: 'active',
      max_login_sessions: 3,
      idle_timeout_minutes: 120,
    },
  });
  const payload = await readJson(response, `create temp admin failed: ${username}`);
  const user = readUserEnvelope(payload, `create temp admin returned invalid payload: ${username}`);
  return {
    username,
    password,
    userId: String(user.user_id || '').trim(),
  };
}

async function getControlledDocument(session, controlledDocumentId) {
  const response = await session.api.get(
    `/api/quality-system/doc-control/documents/${encodeURIComponent(controlledDocumentId)}`,
    { headers: session.headers }
  );
  const payload = await readJson(response, `get controlled document failed: ${controlledDocumentId}`);
  return payload.document;
}

async function openDocumentControl(page) {
  await page.goto(`${FRONTEND_BASE_URL}/quality-system/doc-control`);
  await expect(page.getByTestId('document-control-page')).toBeVisible();
}

async function searchAndSelectDocument(page, docCode, controlledDocumentId) {
  await openDocumentControl(page);
  await page.getByTestId('document-control-filter-doc-code').fill(docCode);
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'GET'
    && response.url().includes('/api/quality-system/doc-control/documents?')
  ));
  await page.getByTestId('document-control-search').click();
  await responsePromise;
  const row = page.getByTestId(`document-control-row-${controlledDocumentId}`);
  await expect(row).toBeVisible({ timeout: 60_000 });
  await row.click();
  await expect(page.getByTestId('document-control-detail-doc-code')).toContainText(docCode);
}

async function createControlledDocument(page, payload) {
  await openDocumentControl(page);
  await page.getByTestId('document-control-create-doc-code').fill(payload.docCode);
  await page.getByTestId('document-control-create-title').fill(payload.title);
  await page.getByTestId('document-control-create-document-type').fill(payload.documentType);
  await page.getByTestId('document-control-create-target-kb').fill(payload.targetKbId);
  await page.getByTestId('document-control-create-product-name').fill(payload.productName);
  await page.getByTestId('document-control-create-registration-ref').fill(payload.registrationRef);
  await page.getByTestId('document-control-create-change-summary').fill(payload.changeSummary);
  await page.getByTestId('document-control-create-file').setInputFiles(payload.filePath);
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes('/api/quality-system/doc-control/documents')
  ));
  await page.getByTestId('document-control-create-submit').click();
  const response = await responsePromise;
  const body = await readJson(response, 'create controlled document failed');
  await expect(page.getByTestId('document-control-success')).toContainText('Controlled document created');
  return body.document;
}

async function submitRevisionForApproval(page, controlledRevisionId) {
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/approval/submit`
    )
  ));
  await page.getByTestId('document-control-approval-submit').click();
  const response = await responsePromise;
  const body = await readJson(response, `submit revision failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Revision submitted for approval');
  return body.document;
}

async function addSignApprover(page, approverUserId) {
  await page.getByTestId('document-control-add-sign-user-id').fill(String(approverUserId));
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes('/approval/add-sign')
  ));
  await page.getByTestId('document-control-add-sign-submit').click();
  const response = await responsePromise;
  const body = await readJson(response, `add-sign failed for ${approverUserId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Additional approver added');
  return body.document;
}

async function approveRevisionViaApi(session, controlledRevisionId, note) {
  const response = await session.api.post(
    `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/approval/approve`,
    {
      headers: session.headers,
      data: { note: note || null },
    }
  );
  const body = await readJson(response, `approve revision failed: ${controlledRevisionId}`);
  return body.document;
}

test.describe.configure({ mode: 'serial' });

test('Document control add-sign branch requires the extra approver before step advancement @doc-e2e', async ({ browser }) => {
  test.setTimeout(300_000);

  const timestamp = Date.now();
  const documentType = `pdf_add_sign_${timestamp}`;
  const docCode = `PDF-ADDSIGN-${timestamp}`;
  const pdfCopy = createPdfCopy(`doc-add-sign-${timestamp}`);
  let companyAdminSession = null;
  let subAdminSession = null;
  let tempAdminSession = null;
  let companyAdminUi = null;
  let tempAdminUserId = '';

  try {
    companyAdminSession = await loginApiAs(summary.users.company_admin.username, DEFAULT_PASSWORD);
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, DEFAULT_PASSWORD);
    const tempAdmin = await createTempAdminUser(companyAdminSession, {
      companyId: Number(summary?.org?.company?.id || 0),
      departmentId: Number(summary?.org?.department?.id || 0),
      employeeUserId: 'doc_login_user',
      fullName: 'Doc Login User',
    });
    tempAdminUserId = tempAdmin.userId;
    tempAdminSession = await loginApiAs(tempAdmin.username, tempAdmin.password);

    await upsertDocumentTypeWorkflow(companyAdminSession, documentType, subAdminSession.user.user_id);
    companyAdminUi = await openSessionPage(browser, companyAdminSession);

    const created = await createControlledDocument(companyAdminUi.page, {
      docCode,
      title: `Add-sign Branch ${timestamp}`,
      documentType,
      targetKbId: String(summary.knowledge.dataset.id),
      productName: 'PDF Add Sign Product',
      registrationRef: `REG-ADDSIGN-${timestamp}`,
      changeSummary: 'Add-sign branch setup',
      filePath: pdfCopy.filePath,
    });
    const controlledDocumentId = String(created.controlled_document_id || '').trim();
    const revisionId = String(created.current_revision?.controlled_revision_id || '').trim();

    await searchAndSelectDocument(companyAdminUi.page, docCode, controlledDocumentId);
    await submitRevisionForApproval(companyAdminUi.page, revisionId);
    await addSignApprover(companyAdminUi.page, tempAdminUserId);

    const afterPrimaryApproval = await approveRevisionViaApi(
      subAdminSession,
      revisionId,
      'Primary approver completed current step after add-sign'
    );
    expect(String(afterPrimaryApproval.current_revision?.status || '')).toBe('approval_in_progress');
    expect(Number(afterPrimaryApproval.current_revision?.current_approval_step_no || 0)).toBe(1);

    const afterAddedApproval = await approveRevisionViaApi(
      tempAdminSession,
      revisionId,
      'Added approver completed the same step'
    );
    expect(String(afterAddedApproval.current_revision?.status || '')).toBe('approval_in_progress');
    expect(Number(afterAddedApproval.current_revision?.current_approval_step_no || 0)).toBe(2);
  } finally {
    if (companyAdminUi) await companyAdminUi.context.close();
    if (tempAdminSession) await tempAdminSession.api.dispose();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (companyAdminSession && tempAdminUserId) {
      await deleteUserById(companyAdminSession.api, companyAdminSession.headers, tempAdminUserId).catch(() => {});
    }
    if (companyAdminSession) await companyAdminSession.api.dispose();
    pdfCopy.cleanup();
  }
});

test('Document control scheduler automatically marks overdue approval reminders without manual click @doc-e2e', async ({ browser }) => {
  test.setTimeout(360_000);

  const timestamp = Date.now();
  const documentType = `pdf_scheduler_${timestamp}`;
  const docCode = `PDF-SCHED-${timestamp}`;
  const pdfCopy = createPdfCopy(`doc-scheduler-${timestamp}`);
  let companyAdminSession = null;
  let subAdminSession = null;
  let companyAdminUi = null;

  try {
    companyAdminSession = await loginApiAs(summary.users.company_admin.username, DEFAULT_PASSWORD);
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, DEFAULT_PASSWORD);

    await upsertDocumentTypeWorkflow(
      companyAdminSession,
      documentType,
      subAdminSession.user.user_id,
      1
    );
    companyAdminUi = await openSessionPage(browser, companyAdminSession);

    const created = await createControlledDocument(companyAdminUi.page, {
      docCode,
      title: `Scheduler Branch ${timestamp}`,
      documentType,
      targetKbId: String(summary.knowledge.dataset.id),
      productName: 'PDF Scheduler Product',
      registrationRef: `REG-SCHED-${timestamp}`,
      changeSummary: 'Scheduler reminder setup',
      filePath: pdfCopy.filePath,
    });
    const controlledDocumentId = String(created.controlled_document_id || '').trim();
    const revisionId = String(created.current_revision?.controlled_revision_id || '').trim();

    await searchAndSelectDocument(companyAdminUi.page, docCode, controlledDocumentId);
    await submitRevisionForApproval(companyAdminUi.page, revisionId);

    const remindedDocument = await poll(async () => {
      const document = await getControlledDocument(companyAdminSession, controlledDocumentId);
      const revision = document?.current_revision || null;
      if (
        String(revision?.controlled_revision_id || '') === revisionId
        && Number(revision?.current_approval_step_last_reminded_at_ms || 0) > 0
      ) {
        return document;
      }
      return null;
    }, { timeoutMs: 170_000, intervalMs: 5_000 });

    if (!remindedDocument) {
      throw new Error(`scheduler_reminder_not_observed:${revisionId}`);
    }
    expect(Number(remindedDocument.current_revision?.current_approval_step_overdue_at_ms || 0)).toBeGreaterThan(0);
    expect(Number(remindedDocument.current_revision?.current_approval_step_last_reminded_at_ms || 0)).toBeGreaterThan(0);
  } finally {
    if (companyAdminUi) await companyAdminUi.context.close();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (companyAdminSession) await companyAdminSession.api.dispose();
    pdfCopy.cleanup();
  }
});
