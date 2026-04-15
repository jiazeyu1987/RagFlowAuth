// @ts-check
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { test, expect } = require('@playwright/test');
const { loadBootstrapSummary } = require('../helpers/bootstrapSummary');
const { loginApiAs, FRONTEND_BASE_URL } = require('../helpers/docRealFlow');
const { openSessionPage } = require('../helpers/docSessionPage');
const { poll } = require('../helpers/documentFlow');

const summary = loadBootstrapSummary();
const PDF_SOURCE_PATH = 'C:\\Users\\BJB110\\Desktop\\文件控制流程初稿.pdf';
const DEFAULT_PASSWORD = process.env.E2E_ADMIN_PASS || 'admin123';

test.use({ video: 'on' });
test.describe.configure({ mode: 'serial' });

function requireExistingPdfSource() {
  if (!fs.existsSync(PDF_SOURCE_PATH)) {
    throw new Error(`pdf_source_missing:${PDF_SOURCE_PATH}`);
  }
  return PDF_SOURCE_PATH;
}

function createPdfCopies(prefix) {
  const sourcePath = requireExistingPdfSource();
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), `${prefix}-`));
  const v1Path = path.join(tmpDir, `${prefix}-v1.pdf`);
  const v2Path = path.join(tmpDir, `${prefix}-v2.pdf`);
  fs.copyFileSync(sourcePath, v1Path);
  fs.copyFileSync(sourcePath, v2Path);
  return {
    tmpDir,
    v1Path,
    v2Path,
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

async function upsertDocumentTypeWorkflow(session, documentType, steps) {
  const response = await session.api.put(
    `/api/quality-system/doc-control/workflows/${encodeURIComponent(documentType)}`,
    {
      headers: session.headers,
      data: {
        name: `PDF Flow ${documentType}`,
        steps,
      },
    }
  );
  const payload = await readJson(response, `upsert workflow failed for ${documentType}`);
  expect(String(payload?.workflow?.document_type || '')).toBe(documentType);
  return payload.workflow;
}

async function getControlledDocument(session, controlledDocumentId) {
  const response = await session.api.get(
    `/api/quality-system/doc-control/documents/${encodeURIComponent(controlledDocumentId)}`,
    { headers: session.headers }
  );
  const payload = await readJson(response, `get controlled document failed for ${controlledDocumentId}`);
  return payload.document;
}

async function listAssignmentsForRevision(session, controlledRevisionId, { timeoutMs = 60_000 } = {}) {
  return poll(async () => {
    const response = await session.api.get('/api/training-compliance/assignments?limit=200', {
      headers: session.headers,
    });
    if (!response.ok()) {
      return null;
    }
    const payload = await response.json().catch(() => ({}));
    const items = Array.isArray(payload?.items) ? payload.items : [];
    const matches = items.filter(
      (item) => String(item?.controlled_revision_id || '').trim() === String(controlledRevisionId || '').trim()
    );
    return matches.length > 0 ? matches : null;
  }, { timeoutMs, intervalMs: 1_500 });
}

async function openDocumentControl(page) {
  await page.goto(`${FRONTEND_BASE_URL}/quality-system/doc-control`);
  await expect(page.getByTestId('document-control-page')).toBeVisible();
}

async function searchAndSelectDocument(page, { docCode, controlledDocumentId }) {
  await openDocumentControl(page);
  await page.getByTestId('document-control-filter-doc-code').fill(docCode);
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'GET'
    && response.url().includes('/api/quality-system/doc-control/documents?')
  );
  await page.getByTestId('document-control-search').click();
  await responsePromise;
  const row = page.getByTestId(`document-control-row-${controlledDocumentId}`);
  await expect(row).toBeVisible({ timeout: 60_000 });
  await row.click();
  await expect(page.getByTestId('document-control-detail-doc-code')).toContainText(docCode);
}

async function createControlledDocument(page, {
  docCode,
  title,
  documentType,
  targetKbId,
  productName,
  registrationRef,
  changeSummary,
  filePath,
}) {
  await openDocumentControl(page);
  await page.getByTestId('document-control-create-doc-code').fill(docCode);
  await page.getByTestId('document-control-create-title').fill(title);
  await page.getByTestId('document-control-create-document-type').fill(documentType);
  await page.getByTestId('document-control-create-target-kb').fill(targetKbId);
  await page.getByTestId('document-control-create-product-name').fill(productName);
  await page.getByTestId('document-control-create-registration-ref').fill(registrationRef);
  await page.getByTestId('document-control-create-change-summary').fill(changeSummary);
  await page.getByTestId('document-control-create-file').setInputFiles(filePath);

  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes('/api/quality-system/doc-control/documents')
  );
  await page.getByTestId('document-control-create-submit').click();
  const response = await responsePromise;
  const payload = await readJson(response, 'create controlled document failed');
  await expect(page.getByTestId('document-control-success')).toContainText('Controlled document created');
  return payload.document;
}

async function createControlledRevision(page, filePath, changeSummary) {
  await page.getByTestId('document-control-revision-change-summary').fill(changeSummary);
  await page.getByTestId('document-control-revision-file').setInputFiles(filePath);
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes('/api/quality-system/doc-control/documents/')
    && response.url().includes('/revisions')
  );
  await page.getByTestId('document-control-revision-submit').click();
  const response = await responsePromise;
  const payload = await readJson(response, 'create controlled revision failed');
  await expect(page.getByTestId('document-control-success')).toContainText('Revision created');
  return payload.document;
}

async function submitRevisionForApproval(page, controlledRevisionId) {
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/approval/submit`
    )
  );
  await page.getByTestId('document-control-approval-submit').click();
  const response = await responsePromise;
  const payload = await readJson(response, `submit revision for approval failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Revision submitted for approval');
  return payload.document;
}

async function approveCurrentStep(page, controlledRevisionId) {
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/approval/approve`
    )
  );
  await page.getByTestId('document-control-approval-approve').click();
  const response = await responsePromise;
  const payload = await readJson(response, `approve revision step failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Approval recorded');
  return payload.document;
}

async function approveRevisionStepViaApi(session, controlledRevisionId, note) {
  const response = await session.api.post(
    `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/approval/approve`,
    {
      headers: session.headers,
      data: { note: note || null },
    }
  );
  const payload = await readJson(response, `approve revision step via api failed: ${controlledRevisionId}`);
  return payload.document;
}

async function remindOverdueApproval(page, controlledRevisionId) {
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/approval/remind-overdue`
    )
  );
  await page.getByTestId('document-control-approval-remind-overdue').click();
  const response = await responsePromise;
  const payload = await readJson(response, `remind overdue approval failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Approval overdue reminder sent');
  return payload.result;
}

async function saveTrainingGate(page, controlledRevisionId, { trainingRequired, departmentIds }) {
  const checkbox = page.getByTestId('document-control-training-required');
  await expect(checkbox).toBeVisible();
  if ((await checkbox.isChecked()) !== Boolean(trainingRequired)) {
    await checkbox.click();
  }
  await page.getByTestId('document-control-training-departments').fill(
    Array.isArray(departmentIds) ? departmentIds.join(', ') : ''
  );
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'PUT'
    && response.url().includes(`/api/training-compliance/revisions/${encodeURIComponent(controlledRevisionId)}/gate`)
  );
  await page.getByTestId('document-control-training-gate-save').click();
  const response = await responsePromise;
  const payload = await readJson(response, `save training gate failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Training gate saved');
  return payload.gate;
}

async function generateTrainingAssignments(page, controlledRevisionId, { assigneeUserIds, departmentIds = [], minReadMinutes }) {
  await page.getByTestId('document-control-training-assignees').fill(assigneeUserIds.join(', '));
  await page.getByTestId('document-control-training-generate-departments').fill(
    Array.isArray(departmentIds) ? departmentIds.join(', ') : ''
  );
  await page.getByTestId('document-control-training-min-read-minutes').fill(String(minReadMinutes));
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes('/api/training-compliance/assignments/generate')
  );
  await page.getByTestId('document-control-training-generate').click();
  const response = await responsePromise;
  const payload = await readJson(response, `generate training assignments failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Training assignments generated');
  return Array.isArray(payload?.items) ? payload.items : [];
}

async function saveDistributionDepartments(page, departmentIds) {
  await page.getByTestId('document-control-distribution-departments').fill(departmentIds.join(', '));
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'PUT'
    && response.url().includes('/api/quality-system/doc-control/documents/')
    && response.url().includes('/distribution-departments')
  );
  await page.getByTestId('document-control-distribution-save').click();
  const response = await responsePromise;
  const payload = await readJson(response, 'save distribution departments failed');
  await expect(page.getByTestId('document-control-success')).toContainText('Distribution departments saved');
  return Array.isArray(payload?.department_ids) ? payload.department_ids : [];
}

async function publishRevision(page, controlledRevisionId, releaseMode, { expectSuccess = true } = {}) {
  await page.getByTestId('document-control-release-mode').selectOption(releaseMode);
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes(`/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/publish`)
  );
  await page.getByTestId('document-control-publish').click();
  const response = await responsePromise;
  if (expectSuccess) {
    const payload = await readJson(response, `publish revision failed: ${controlledRevisionId}`);
    await expect(page.getByTestId('document-control-success')).toContainText('Revision published');
    return payload.document;
  }
  const payload = await response.json().catch(() => ({}));
  expect(response.ok()).toBeFalsy();
  await expect(page.getByTestId('document-control-error')).toBeVisible();
  return payload;
}

async function completeManualRelease(page, controlledRevisionId) {
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/publish/manual-archive-complete`
    )
  );
  await page.getByTestId('document-control-manual-release-complete').click();
  const response = await responsePromise;
  const payload = await readJson(response, `manual release completion failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Manual archive release completed');
  return payload.document;
}

async function confirmDepartmentAck(page, controlledRevisionId, departmentId) {
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/department-acks/${departmentId}/confirm`
    )
  );
  await page.getByTestId(`document-control-department-ack-confirm-${departmentId}`).click();
  const response = await responsePromise;
  const payload = await readJson(response, `department acknowledgment failed: ${controlledRevisionId}/${departmentId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Department acknowledgment recorded');
  return payload.ack;
}

async function initiateObsolete(page, controlledRevisionId, { reason, retentionUntilMs }) {
  await page.getByTestId('document-control-obsolete-reason').fill(reason);
  await page.getByTestId('document-control-obsolete-retention-until-ms').fill(String(retentionUntilMs));
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/obsolete/initiate`
    )
  );
  await page.getByTestId('document-control-obsolete-initiate').click();
  const response = await responsePromise;
  const payload = await readJson(response, `obsolete initiate failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Obsolete request initiated');
  return payload.document;
}

async function approveObsolete(page, controlledRevisionId) {
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === 'POST'
    && response.url().includes(
      `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/obsolete/approve`
    )
  );
  await page.getByTestId('document-control-obsolete-approve').click();
  const response = await responsePromise;
  const payload = await readJson(response, `obsolete approve failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Obsolete request approved');
  return payload.document;
}

async function approveObsoleteViaApi(session, controlledRevisionId, note) {
  const response = await session.api.post(
    `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/obsolete/approve`,
    {
      headers: session.headers,
      data: { note: note || null },
    }
  );
  const payload = await readJson(response, `obsolete approve via api failed: ${controlledRevisionId}`);
  return payload.document;
}

test('PDF document-control flow covers approval, training gate, release, department ack, obsolete, and destruction @doc-e2e', async ({ browser }) => {
  test.setTimeout(900_000);

  const timestamp = Date.now();
  const documentType = `pdf_flow_${timestamp}`;
  const docCode = `PDF-E2E-${timestamp}`;
  const title = `PDF Flow Validation ${timestamp}`;
  const departmentId = Number(summary?.org?.department?.id || 0);
  if (!Number.isInteger(departmentId) || departmentId <= 0) {
    throw new Error('bootstrap_department_id_missing');
  }
  const videoDir = path.resolve(
    process.env.E2E_OUTPUT_DIR || path.join('D:\\ProjectPackage\\RagflowAuth', 'output', 'playwright', 'document-control-pdf-flow'),
    'videos'
  );
  fs.mkdirSync(videoDir, { recursive: true });

  const pdfCopies = createPdfCopies(`doc-control-pdf-flow-${timestamp}`);
  let companyAdminSession = null;
  let subAdminSession = null;
  let operatorSession = null;
  let companyAdminUi = null;
  let operatorUi = null;

  try {
    companyAdminSession = await loginApiAs(summary.users.company_admin.username, DEFAULT_PASSWORD);
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, DEFAULT_PASSWORD);
    operatorSession = await loginApiAs(summary.users.operator.username, DEFAULT_PASSWORD);

    await upsertDocumentTypeWorkflow(companyAdminSession, documentType, [
      {
        step_type: 'cosign',
        approval_rule: 'all',
        approver_user_ids: [String(subAdminSession.user.user_id)],
        timeout_reminder_minutes: 1,
        member_source: 'fixed',
      },
      {
        step_type: 'approve',
        approval_rule: 'all',
        approver_user_ids: [String(subAdminSession.user.user_id)],
        timeout_reminder_minutes: 5,
        member_source: 'fixed',
      },
      {
        step_type: 'standardize_review',
        approval_rule: 'all',
        approver_user_ids: [String(subAdminSession.user.user_id)],
        timeout_reminder_minutes: 5,
        member_source: 'fixed',
      },
    ]);

    companyAdminUi = await openSessionPage(browser, companyAdminSession, {
      recordVideo: { dir: videoDir },
    });
    operatorUi = await openSessionPage(browser, operatorSession, {
      recordVideo: { dir: videoDir },
    });

    const v1Document = await createControlledDocument(companyAdminUi.page, {
      docCode,
      title,
      documentType,
      targetKbId: String(summary.knowledge.dataset.id),
      productName: 'PDF E2E Product',
      registrationRef: `REG-${timestamp}`,
      changeSummary: 'Initial controlled document created from the PDF flow draft',
      filePath: pdfCopies.v1Path,
    });
    const controlledDocumentId = String(v1Document.controlled_document_id || '').trim();
    const v1RevisionId = String(v1Document.current_revision?.controlled_revision_id || '').trim();
    expect(controlledDocumentId).toBeTruthy();
    expect(v1RevisionId).toBeTruthy();

    await searchAndSelectDocument(companyAdminUi.page, { docCode, controlledDocumentId });
    await submitRevisionForApproval(companyAdminUi.page, v1RevisionId);

    await approveRevisionStepViaApi(subAdminSession, v1RevisionId, 'Cosign via approver API');
    await approveRevisionStepViaApi(subAdminSession, v1RevisionId, 'Approval via approver API');
    const v1ApprovedDocument = await approveRevisionStepViaApi(
      subAdminSession,
      v1RevisionId,
      'Standardization review via approver API'
    );
    expect(String(v1ApprovedDocument.current_revision?.status || '')).toBe('approved_pending_effective');

    await searchAndSelectDocument(companyAdminUi.page, { docCode, controlledDocumentId });
    await saveTrainingGate(companyAdminUi.page, v1RevisionId, {
      trainingRequired: false,
      departmentIds: [departmentId],
    });
    await saveDistributionDepartments(companyAdminUi.page, [departmentId]);
    const v1PublishedDocument = await publishRevision(companyAdminUi.page, v1RevisionId, 'automatic');
    expect(String(v1PublishedDocument.current_revision?.status || '')).toBe('effective');
    await expect(
      companyAdminUi.page.getByTestId(`document-control-department-ack-confirm-${departmentId}`)
    ).toBeVisible({ timeout: 60_000 });

    await createControlledRevision(companyAdminUi.page, pdfCopies.v2Path, 'Revision 2 adds the full gated release path');
    const afterRevisionCreate = await getControlledDocument(companyAdminSession, controlledDocumentId);
    const v2Revision = (afterRevisionCreate.revisions || []).find(
      (item) => Number(item?.revision_no) === 2
    );
    if (!v2Revision) {
      throw new Error('revision_2_not_found');
    }
    const v2RevisionId = String(v2Revision.controlled_revision_id || '').trim();
    expect(v2RevisionId).toBeTruthy();

    await searchAndSelectDocument(companyAdminUi.page, { docCode, controlledDocumentId });
    await submitRevisionForApproval(companyAdminUi.page, v2RevisionId);

    await companyAdminUi.page.waitForTimeout(65_000);
    const reminderResult = await remindOverdueApproval(companyAdminUi.page, v2RevisionId);
    expect(Boolean(reminderResult?.overdue)).toBeTruthy();

    await approveRevisionStepViaApi(subAdminSession, v2RevisionId, 'V2 cosign via approver API');
    await approveRevisionStepViaApi(subAdminSession, v2RevisionId, 'V2 approve via approver API');
    await approveRevisionStepViaApi(subAdminSession, v2RevisionId, 'V2 standardize via approver API');

    await searchAndSelectDocument(companyAdminUi.page, { docCode, controlledDocumentId });
    await saveTrainingGate(companyAdminUi.page, v2RevisionId, {
      trainingRequired: true,
      departmentIds: [departmentId],
    });
    const generatedAssignments = await generateTrainingAssignments(companyAdminUi.page, v2RevisionId, {
      assigneeUserIds: [String(companyAdminSession.user.user_id)],
      departmentIds: [],
      minReadMinutes: 1,
    });
    expect(generatedAssignments.length).toBe(1);
    const blockedPublishPayload = await publishRevision(companyAdminUi.page, v2RevisionId, 'manual_by_doc_control', {
      expectSuccess: false,
    });
    expect(String(blockedPublishPayload?.detail || '')).toContain('document_control_training_in_progress');

    const companyAdminAssignments = await listAssignmentsForRevision(companyAdminSession, v2RevisionId, { timeoutMs: 90_000 });
    if (!companyAdminAssignments || companyAdminAssignments.length === 0) {
      throw new Error(`training_assignments_missing:${v2RevisionId}`);
    }
    const companyAdminAssignment = companyAdminAssignments.find(
      (item) => String(item?.assignee_user_id || '').trim() === String(companyAdminSession.user.user_id)
    ) || companyAdminAssignments[0];
    const assignmentId = String(companyAdminAssignment.assignment_id || '').trim();
    expect(assignmentId).toBeTruthy();

    await companyAdminUi.page.goto(`${FRONTEND_BASE_URL}/quality-system/training`);
    await expect(companyAdminUi.page.getByTestId('training-ack-workspace')).toBeVisible();
    const startReadingButton = companyAdminUi.page.getByTestId(`training-ack-start-reading-${assignmentId}`);
    await expect(startReadingButton).toBeVisible({ timeout: 60_000 });
    const assignmentCard = companyAdminUi.page.locator('article').filter({ has: startReadingButton }).first();
    const acknowledgeButton = assignmentCard.locator('button').nth(1);
    await startReadingButton.click();
    await expect(acknowledgeButton).toBeEnabled({ timeout: 90_000 });
    const acknowledgeResponsePromise = companyAdminUi.page.waitForResponse((response) =>
      response.request().method() === 'POST'
      && response.url().includes(`/api/training-compliance/assignments/${encodeURIComponent(assignmentId)}/acknowledge`)
    );
    await acknowledgeButton.click();
    const acknowledgeResponse = await acknowledgeResponsePromise;
    await readJson(acknowledgeResponse, `acknowledge training assignment failed: ${assignmentId}`);

    await searchAndSelectDocument(companyAdminUi.page, { docCode, controlledDocumentId });
    const v2PublishedDocument = await publishRevision(companyAdminUi.page, v2RevisionId, 'manual_by_doc_control');
    expect(String(v2PublishedDocument.current_revision?.status || '')).toBe('effective');
    await expect(companyAdminUi.page.getByTestId('document-control-manual-release-complete')).toBeVisible({ timeout: 60_000 });
    await expect(
      companyAdminUi.page.getByTestId(`document-control-department-ack-confirm-${departmentId}`)
    ).toHaveCount(0);

    await completeManualRelease(companyAdminUi.page, v2RevisionId);
    await expect(
      companyAdminUi.page.getByTestId(`document-control-department-ack-confirm-${departmentId}`)
    ).toBeVisible({ timeout: 60_000 });
    await confirmDepartmentAck(companyAdminUi.page, v2RevisionId, departmentId);

    const v2Detail = await getControlledDocument(companyAdminSession, controlledDocumentId);
    const revisionStatuses = new Map(
      (Array.isArray(v2Detail.revisions) ? v2Detail.revisions : []).map((item) => [
        Number(item.revision_no),
        String(item.status || ''),
      ])
    );
    expect(revisionStatuses.get(1)).toBe('superseded');
    expect(revisionStatuses.get(2)).toBe('effective');

    const retentionUntilMs = Date.now() + 10_000;
    await initiateObsolete(companyAdminUi.page, v2RevisionId, {
      reason: 'E2E obsolete and destruction validation',
      retentionUntilMs,
    });
    await approveObsoleteViaApi(subAdminSession, v2RevisionId, 'Obsolete approval via api');
    await searchAndSelectDocument(companyAdminUi.page, { docCode, controlledDocumentId });

    const finalRevision = await poll(async () => {
      const detail = await getControlledDocument(companyAdminSession, controlledDocumentId);
      const revision = (Array.isArray(detail.revisions) ? detail.revisions : []).find(
        (item) => String(item.controlled_revision_id || '').trim() === v2RevisionId
      );
      if (!revision) {
        return null;
      }
      return Number(revision?.destruction_confirmed_at_ms || 0) > 0 ? revision : null;
    }, { timeoutMs: 30_000, intervalMs: 2_000 });

    expect(finalRevision).toBeTruthy();
    expect(String(finalRevision?.status || '')).toBe('obsolete');
    expect(Number(finalRevision?.destruction_confirmed_at_ms || 0)).toBeGreaterThan(0);
  } finally {
    if (companyAdminUi) await companyAdminUi.context.close();
    if (operatorUi) await operatorUi.context.close();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (operatorSession) await operatorSession.api.dispose();
    if (companyAdminSession) await companyAdminSession.api.dispose();
    pdfCopies.cleanup();
  }
});
