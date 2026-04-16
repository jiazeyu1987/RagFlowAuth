// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, mockAuthMe } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

const authCapabilities = {
  users: { manage: { scope: 'all', targets: [] } },
  kb_documents: {
    view: { scope: 'all', targets: [] },
    upload: { scope: 'all', targets: [] },
    review: { scope: 'all', targets: [] },
    approve: { scope: 'all', targets: [] },
    reject: { scope: 'all', targets: [] },
    delete: { scope: 'all', targets: [] },
    download: { scope: 'all', targets: [] },
    copy: { scope: 'all', targets: [] },
  },
  ragflow_documents: {
    view: { scope: 'all', targets: [] },
    preview: { scope: 'all', targets: [] },
    delete: { scope: 'all', targets: [] },
    download: { scope: 'all', targets: [] },
    copy: { scope: 'all', targets: [] },
  },
  kb_directory: { manage: { scope: 'all', targets: [] } },
  kbs_config: { view: { scope: 'all', targets: [] } },
  tools: { view: { scope: 'all', targets: [] } },
  chats: { view: { scope: 'all', targets: [] } },
  quality_system: {
    view: { scope: 'all', targets: [] },
    manage: { scope: 'all', targets: [] },
  },
  document_control: {
    create: { scope: 'all', targets: [] },
    review: { scope: 'all', targets: [] },
    approve: { scope: 'all', targets: [] },
    effective: { scope: 'all', targets: [] },
    publish: { scope: 'all', targets: [] },
    obsolete: { scope: 'all', targets: [] },
    export: { scope: 'all', targets: [] },
  },
  audit_events: {
    view: { scope: 'all', targets: [] },
  },
};

adminTest('document control shows matrix preview and generated approval chain @regression @docs', async ({
  page,
}) => {
  await mockAuthMe(page, { capabilities: authCapabilities });
  await mockJson(page, '**/api/inbox**', { items: [], total: 0, unread_count: 0 });

  const state = {
    document: {
      controlled_document_id: 'doc-1',
      doc_code: 'DHF-001',
      title: '设计验证方案',
      document_type: 'dhf',
      file_subtype: '设计验证方案/报告',
      target_kb_id: 'kb-1',
      product_name: '产品 A',
      registration_ref: 'REG-001',
      current_revision: {
        controlled_revision_id: 'rev-1',
        controlled_document_id: 'doc-1',
        revision_no: 1,
        status: 'draft',
        filename: 'design-validation.pdf',
        kb_doc_id: 'kb-doc-1',
        approval_request_id: null,
        approval_round: 0,
        current_approval_step_no: null,
        current_approval_step_name: null,
        file_subtype: '设计验证方案/报告',
        matrix_snapshot: null,
        position_snapshot: null,
      },
      effective_revision: null,
      revisions: [
        {
          controlled_revision_id: 'rev-1',
          controlled_document_id: 'doc-1',
          revision_no: 1,
          status: 'draft',
          filename: 'design-validation.pdf',
          kb_doc_id: 'kb-doc-1',
          approval_request_id: null,
          approval_round: 0,
          current_approval_step_no: null,
          current_approval_step_name: null,
          file_subtype: '设计验证方案/报告',
          matrix_snapshot: null,
          position_snapshot: null,
        },
      ],
    },
  };

  let submitPayload = null;

  await page.route('**/api/quality-system/doc-control/documents?**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [state.document] }),
    });
  });

  await page.route('**/api/quality-system/doc-control/documents/doc-1', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ document: state.document }),
    });
  });

  await page.route('**/api/admin/quality-system-config', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        positions: [],
        file_categories: [{ id: 1, name: '设计验证方案/报告', is_active: true }],
      }),
    });
  });

  await page.route('**/api/quality-system/doc-control/revisions/rev-1/matrix-preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        result: {
          file_subtype: '设计验证方案/报告',
          compiler_check: {
            position_name: '项目负责人',
            matched: true,
            matched_user_ids: ['u_admin'],
          },
          signoff_steps: [
            {
              step_name: 'cosign',
              step_semantic: 'signoff',
              position_name: '???????',
              approvers: [{ user_id: 'u-mgr-1', full_name: 'Direct Manager' }],
            },
            {
              step_name: 'cosign',
              step_semantic: 'signoff',
              position_name: 'QA',
              approvers: [{ user_id: 'u-qa-1', full_name: 'QA Reviewer' }],
            },
            {
              step_name: 'standardize_review',
              step_semantic: 'signoff',
              position_name: '文档管理员',
              approvers: [{ user_id: 'u-doc-1', full_name: 'Doc Admin' }],
            },
          ],
          approval_steps: [
            {
              step_name: 'approve',
              step_semantic: 'approval',
              position_name: '编制部门负责人或授权代表',
              approvers: [{ user_id: 'u-approver-1', full_name: 'Final Approver' }],
            },
          ],
        },
      }),
    });
  });

  await page.route('**/api/quality-system/doc-control/revisions/rev-1/approval/submit', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    submitPayload = route.request().postDataJSON();
    state.document = {
      ...state.document,
      current_revision: {
        ...state.document.current_revision,
        status: 'approval_in_progress',
        approval_request_id: 'oa-1',
        approval_round: 1,
        current_approval_step_no: 1,
        current_approval_step_name: 'cosign',
        matrix_snapshot: { file_subtype: '设计验证方案/报告' },
        position_snapshot: { positions: { QA: ['u-qa-1'] } },
      },
      revisions: [
        {
          ...state.document.revisions[0],
          status: 'approval_in_progress',
          approval_request_id: 'oa-1',
          approval_round: 1,
          current_approval_step_no: 1,
          current_approval_step_name: 'cosign',
          matrix_snapshot: { file_subtype: '设计验证方案/报告' },
          position_snapshot: { positions: { QA: ['u-qa-1'] } },
        },
      ],
    };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ document: state.document }),
    });
  });

  await page.route('**/api/operation-approvals/requests/oa-1', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        request_id: 'oa-1',
        current_step_no: 1,
        steps: [
          {
            step_no: 1,
            step_name: 'cosign',
            status: 'active',
            approvers: [{ approver_user_id: 'u-qa-1', approver_full_name: 'QA Reviewer', status: 'pending' }],
          },
        ],
        workflow_snapshot: {
          mode: 'approval_matrix',
          steps: [
            {
              step_no: 1,
              step_name: 'cosign',
              step_semantic: 'signoff',
              position_name: 'QA',
              members: [{ user_id: 'u-qa-1', full_name: 'QA Reviewer' }],
            },
            {
              step_no: 2,
              step_name: 'approve',
              step_semantic: 'approval',
              position_name: '编制部门负责人或授权代表',
              members: [{ user_id: 'u-approver-1', full_name: 'Final Approver' }],
            },
          ],
        },
      }),
    });
  });

  await page.goto('/quality-system/doc-control');

  await expect(page.getByTestId('document-control-matrix-preview')).toBeVisible();
  await expect(page.getByTestId('document-control-matrix-preview-compiler')).toContainText('项目负责人');
  await expect(page.getByTestId('document-control-matrix-preview-signoff')).toContainText('QA');
  await expect(page.getByTestId('document-control-matrix-preview-signoff')).toContainText('文档管理员');
  await expect(page.getByTestId('document-control-matrix-preview-approval')).toContainText(
    '编制部门负责人或授权代表'
  );
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).toContainText('Direct Manager');
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).toContainText('QA Reviewer');
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).toContainText('Final Approver');

  await page.getByTestId('document-control-approval-note').fill('submit with matrix preview');
  await page.getByTestId('document-control-approval-submit').click();

  expect(submitPayload).toEqual({ note: 'submit with matrix preview' });

  await expect(page.getByTestId('document-control-workspace-status')).toContainText('approval in progress');
  await expect(page.getByTestId('document-control-approval-pending-approvers')).toContainText('QA Reviewer');
  await expect(page.getByTestId('document-control-approval-step-semantic')).toContainText('signoff');
  await expect(page.getByTestId('document-control-approval-step-position')).toContainText('QA');
  await expect(page.getByTestId('document-control-approval-step-approvers')).toContainText('QA Reviewer');
});
