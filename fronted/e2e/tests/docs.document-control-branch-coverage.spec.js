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
    tmpDir,
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

async function upsertDocumentTypeWorkflow(session, documentType, approverUserId) {
  const response = await session.api.put(
    `/api/quality-system/doc-control/workflows/${encodeURIComponent(documentType)}`,
    {
      headers: session.headers,
      data: {
        name: `Branch Coverage ${documentType}`,
        steps: [
          {
            step_type: 'cosign',
            approval_rule: 'all',
            approver_user_ids: [String(approverUserId)],
            timeout_reminder_minutes: 1,
            member_source: 'fixed',
          },
          {
            step_type: 'approve',
            approval_rule: 'all',
            approver_user_ids: [String(approverUserId)],
            timeout_reminder_minutes: 5,
            member_source: 'fixed',
          },
          {
            step_type: 'standardize_review',
            approval_rule: 'all',
            approver_user_ids: [String(approverUserId)],
            timeout_reminder_minutes: 5,
            member_source: 'fixed',
          },
        ],
      },
    }
  );
  return readJson(response, `upsert workflow failed for ${documentType}`);
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

async function rejectRevisionViaApi(session, controlledRevisionId, note) {
  const response = await session.api.post(
    `/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/approval/reject`,
    {
      headers: session.headers,
      data: { note: note || null },
    }
  );
  const body = await readJson(response, `reject revision failed: ${controlledRevisionId}`);
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

async function saveTrainingGate(page, controlledRevisionId, { trainingRequired, departmentIds }) {
  const checkbox = page.getByTestId('document-control-training-required');
  await expect(checkbox).toBeVisible();
  if ((await checkbox.isChecked()) !== Boolean(trainingRequired)) {
    await checkbox.click();
  }
  await page.getByTestId('document-control-training-departments').fill(
    Array.isArray(departmentIds) ? departmentIds.join(', ') : ''
  );
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'PUT'
    && response.url().includes(`/api/training-compliance/revisions/${encodeURIComponent(controlledRevisionId)}/gate`)
  ));
  await page.getByTestId('document-control-training-gate-save').click();
  const response = await responsePromise;
  const body = await readJson(response, `save training gate failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Training gate saved');
  return body.gate;
}

async function generateTrainingAssignments(page, controlledRevisionId, { assigneeUserIds, minReadMinutes }) {
  await page.getByTestId('document-control-training-assignees').fill(assigneeUserIds.join(', '));
  await page.getByTestId('document-control-training-generate-departments').fill('');
  await page.getByTestId('document-control-training-min-read-minutes').fill(String(minReadMinutes));
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes('/api/training-compliance/assignments/generate')
  ));
  await page.getByTestId('document-control-training-generate').click();
  const response = await responsePromise;
  const body = await readJson(response, `generate training assignments failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Training assignments generated');
  return Array.isArray(body?.items) ? body.items : [];
}

async function saveDistributionDepartments(page, departmentIds) {
  await page.getByTestId('document-control-distribution-departments').fill(departmentIds.join(', '));
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'PUT'
    && response.url().includes('/api/quality-system/doc-control/documents/')
    && response.url().includes('/distribution-departments')
  ));
  await page.getByTestId('document-control-distribution-save').click();
  const response = await responsePromise;
  const body = await readJson(response, 'save distribution departments failed');
  await expect(page.getByTestId('document-control-success')).toContainText('Distribution departments saved');
  return Array.isArray(body?.department_ids) ? body.department_ids : [];
}

async function publishRevisionExpectFailure(page, controlledRevisionId) {
  await page.getByTestId('document-control-release-mode').selectOption('automatic');
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/publish`)
  ));
  await page.getByTestId('document-control-publish').click();
  const response = await responsePromise;
  expect(response.ok()).toBeFalsy();
  return response.json().catch(() => ({}));
}

async function publishRevision(page, controlledRevisionId) {
  await page.getByTestId('document-control-release-mode').selectOption('automatic');
  const responsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes(`/api/quality-system/doc-control/revisions/${encodeURIComponent(controlledRevisionId)}/publish`)
  ));
  await page.getByTestId('document-control-publish').click();
  const response = await responsePromise;
  const body = await readJson(response, `publish revision failed: ${controlledRevisionId}`);
  await expect(page.getByTestId('document-control-success')).toContainText('Revision published');
  return body.document;
}

async function listAssignmentsForRevision(session, controlledRevisionId, { timeoutMs = 90_000 } = {}) {
  return poll(async () => {
    const response = await session.api.get('/api/training-compliance/assignments?limit=200', {
      headers: session.headers,
    });
    if (!response.ok()) return null;
    const payload = await response.json().catch(() => ({}));
    const items = Array.isArray(payload?.items) ? payload.items : [];
    const matches = items.filter((item) => String(item?.controlled_revision_id || '') === String(controlledRevisionId));
    return matches.length > 0 ? matches : null;
  }, { timeoutMs, intervalMs: 1_500 });
}

test('Document control covers reject-resubmit and training question resolution branches @doc-e2e', async ({ browser }) => {
  test.setTimeout(600_000);

  const timestamp = Date.now();
  const documentType = `pdf_branch_${timestamp}`;
  const docCode = `PDF-BRANCH-${timestamp}`;
  const title = `PDF Branch Validation ${timestamp}`;
  const departmentId = Number(summary?.org?.department?.id || 0);
  if (!Number.isInteger(departmentId) || departmentId <= 0) {
    throw new Error('bootstrap_department_id_missing');
  }

  const pdfCopy = createPdfCopy(`doc-control-branch-${timestamp}`);
  let companyAdminSession = null;
  let subAdminSession = null;
  let companyAdminUi = null;

  try {
    companyAdminSession = await loginApiAs(summary.users.company_admin.username, DEFAULT_PASSWORD);
    subAdminSession = await loginApiAs(summary.users.sub_admin.username, DEFAULT_PASSWORD);

    await upsertDocumentTypeWorkflow(companyAdminSession, documentType, subAdminSession.user.user_id);
    companyAdminUi = await openSessionPage(browser, companyAdminSession);

    const created = await createControlledDocument(companyAdminUi.page, {
      docCode,
      title,
      documentType,
      targetKbId: String(summary.knowledge.dataset.id),
      productName: 'PDF Branch Product',
      registrationRef: `REG-BRANCH-${timestamp}`,
      changeSummary: 'Branch coverage setup',
      filePath: pdfCopy.filePath,
    });

    const controlledDocumentId = String(created.controlled_document_id || '').trim();
    const revisionId = String(created.current_revision?.controlled_revision_id || '').trim();
    expect(controlledDocumentId).toBeTruthy();
    expect(revisionId).toBeTruthy();

    await searchAndSelectDocument(companyAdminUi.page, docCode, controlledDocumentId);
    await submitRevisionForApproval(companyAdminUi.page, revisionId);

    await rejectRevisionViaApi(subAdminSession, revisionId, 'Reject once to verify resubmission branch');

    await searchAndSelectDocument(companyAdminUi.page, docCode, controlledDocumentId);
    await expect(companyAdminUi.page.getByTestId('document-control-workspace-status')).toContainText('approval rejected');
    await expect(companyAdminUi.page.getByTestId('document-control-approval-submit')).toBeVisible();

    await submitRevisionForApproval(companyAdminUi.page, revisionId);
    await approveRevisionViaApi(subAdminSession, revisionId, 'Resubmitted cosign approved');
    await approveRevisionViaApi(subAdminSession, revisionId, 'Resubmitted approve approved');
    const approvedDocument = await approveRevisionViaApi(subAdminSession, revisionId, 'Resubmitted standardization approved');
    expect(String(approvedDocument.current_revision?.status || '')).toBe('approved_pending_effective');

    await searchAndSelectDocument(companyAdminUi.page, docCode, controlledDocumentId);
    await saveTrainingGate(companyAdminUi.page, revisionId, {
      trainingRequired: true,
      departmentIds: [departmentId],
    });
    await saveDistributionDepartments(companyAdminUi.page, [departmentId]);
    const assignments = await generateTrainingAssignments(companyAdminUi.page, revisionId, {
      assigneeUserIds: [String(companyAdminSession.user.user_id)],
      minReadMinutes: 1,
    });
    expect(assignments.length).toBe(1);

    const blockedPayload = await publishRevisionExpectFailure(companyAdminUi.page, revisionId);
    expect(String(blockedPayload?.detail || '')).toContain('document_control_training_in_progress');

    const revisionAssignments = await listAssignmentsForRevision(companyAdminSession, revisionId);
    if (!revisionAssignments || revisionAssignments.length === 0) {
      throw new Error(`training_assignments_missing:${revisionId}`);
    }
    const assignment = revisionAssignments[0];
    const assignmentId = String(assignment.assignment_id || '').trim();
    const questionText = `Question branch ${timestamp}`;
    const resolutionText = `Resolved branch ${timestamp}`;

    await companyAdminUi.page.goto(`${FRONTEND_BASE_URL}/quality-system/training`);
    await expect(companyAdminUi.page.getByTestId('training-ack-workspace')).toBeVisible();
    const startReadingButton = companyAdminUi.page.getByTestId(`training-ack-start-reading-${assignmentId}`);
    await expect(startReadingButton).toBeVisible({ timeout: 60_000 });
    const assignmentCard = companyAdminUi.page.locator('article').filter({ has: startReadingButton }).first();
    const questionField = assignmentCard.locator('textarea').first();
    const acknowledgeButton = assignmentCard.locator('button').nth(1);
    const questionedButton = assignmentCard.locator('button').nth(2);

    await startReadingButton.click();
    await expect(questionedButton).toBeEnabled({ timeout: 90_000 });
    await questionField.fill(questionText);

    const questionedResponsePromise = companyAdminUi.page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes(`/api/training-compliance/assignments/${encodeURIComponent(assignmentId)}/acknowledge`)
    ));
    await questionedButton.click();
    const questionedResponse = await questionedResponsePromise;
    expect(questionedResponse.ok()).toBeTruthy();

    const threadCard = companyAdminUi.page.locator('article').filter({ hasText: questionText }).last();
    await expect(threadCard).toBeVisible({ timeout: 60_000 });
    await threadCard.locator('textarea').first().fill(resolutionText);
    const resolveResponsePromise = companyAdminUi.page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes('/api/training-compliance/question-threads/')
      && response.url().includes('/resolve')
    ));
    await threadCard.getByRole('button').last().click();
    const resolveResponse = await resolveResponsePromise;
    expect(resolveResponse.ok()).toBeTruthy();

    const assignmentCardAfterResolve = companyAdminUi.page.locator('article').filter({ has: startReadingButton }).first();
    const acknowledgeButtonAfterResolve = assignmentCardAfterResolve.locator('button').nth(1);
    await expect(acknowledgeButtonAfterResolve).toBeEnabled({ timeout: 60_000 });
    const acknowledgeResponsePromise = companyAdminUi.page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && response.url().includes(`/api/training-compliance/assignments/${encodeURIComponent(assignmentId)}/acknowledge`)
    ));
    await acknowledgeButtonAfterResolve.click();
    const acknowledgeResponse = await acknowledgeResponsePromise;
    expect(acknowledgeResponse.ok()).toBeTruthy();

    await searchAndSelectDocument(companyAdminUi.page, docCode, controlledDocumentId);
    const published = await publishRevision(companyAdminUi.page, revisionId);
    expect(String(published.current_revision?.status || '')).toBe('effective');
  } finally {
    if (companyAdminUi) await companyAdminUi.context.close();
    if (subAdminSession) await subAdminSession.api.dispose();
    if (companyAdminSession) await companyAdminSession.api.dispose();
    pdfCopy.cleanup();
  }
});
