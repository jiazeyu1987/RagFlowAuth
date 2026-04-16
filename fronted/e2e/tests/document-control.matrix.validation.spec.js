// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, mockAuthMe } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

const authCapabilities = {
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
};

function baseDocument(overrides = {}) {
  return {
    controlled_document_id: 'doc-1',
    doc_code: 'DMR-001',
    title: '产品技术要求',
    document_type: 'dmr',
    file_subtype: '产品技术要求',
    target_kb_id: 'kb-1',
    product_name: '产品 A',
    registration_ref: '',
    current_revision: {
      controlled_revision_id: 'rev-1',
      controlled_document_id: 'doc-1',
      revision_no: 1,
      status: 'draft',
      filename: 'doc.pdf',
      kb_doc_id: 'kb-doc-1',
      approval_request_id: null,
      approval_round: 0,
      current_approval_step_no: null,
      current_approval_step_name: null,
      file_subtype: '产品技术要求',
      matrix_snapshot: null,
      position_snapshot: null,
    },
    effective_revision: null,
    revisions: [],
    ...overrides,
  };
}

async function mockBaseDocApis(page, document) {
  await mockAuthMe(page, { capabilities: authCapabilities });
  await mockJson(page, '**/api/inbox**', { items: [], total: 0, unread_count: 0 });
  await page.route('**/api/quality-system/doc-control/documents?**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [document] }),
    });
  });
  await page.route('**/api/quality-system/doc-control/documents/doc-1', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ document }),
    });
  });
  await page.route('**/api/admin/quality-system-config', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        positions: [],
        file_categories: [
          { id: 1, name: '产品技术要求', is_active: true },
          { id: 2, name: '设计验证方案/报告', is_active: true },
        ],
      }),
    });
  });
}

adminTest('document control requires file subtype before create @regression @docs', async ({ page }) => {
  await mockBaseDocApis(page, baseDocument());

  let createCount = 0;
  await page.route('**/api/quality-system/doc-control/documents', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    createCount += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
  });
  await page.route('**/api/quality-system/doc-control/revisions/rev-1/matrix-preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        result: {
          file_subtype: '产品技术要求',
          compiler_check: { position_name: '项目负责人', matched: true, matched_user_ids: ['u_admin'] },
          signoff_steps: [],
          approval_steps: [],
        },
      }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await page.getByTestId('document-control-create-doc-code').fill('DOC-NEW-1');
  await page.getByTestId('document-control-create-title').fill('新文件');
  await page.getByTestId('document-control-create-document-type').fill('dmr');
  await page.getByTestId('document-control-create-target-kb').fill('Quality KB');
  await page.getByTestId('document-control-create-product-name').fill('产品 B');
  await page.setInputFiles(
    '[data-testid="document-control-create-file"]',
    {
      name: 'new.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 validation'),
    }
  );
  await page.getByTestId('document-control-create-submit').click();

  expect(createCount).toBe(0);
  await expect(page.getByTestId('document-control-error')).toContainText('Please select a file subtype.');
});

adminTest('document control omits registration signoff when registration ref is empty @regression @docs', async ({
  page,
}) => {
  await mockBaseDocApis(
    page,
    baseDocument({
      file_subtype: '产品技术要求',
      current_revision: {
        controlled_revision_id: 'rev-1',
        controlled_document_id: 'doc-1',
        revision_no: 1,
        status: 'draft',
        filename: 'doc.pdf',
        kb_doc_id: 'kb-doc-1',
        approval_request_id: null,
        approval_round: 0,
        current_approval_step_no: null,
        current_approval_step_name: null,
        file_subtype: '产品技术要求',
        matrix_snapshot: null,
        position_snapshot: null,
      },
    })
  );

  await page.route('**/api/quality-system/doc-control/revisions/rev-1/matrix-preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        result: {
          file_subtype: '产品技术要求',
          compiler_check: { position_name: '项目负责人', matched: true, matched_user_ids: ['u_admin'] },
          signoff_steps: [
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
              approvers: [{ user_id: 'u-app-1', full_name: 'Approver One' }],
            },
          ],
        },
      }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await expect(page.getByTestId('document-control-matrix-preview')).toBeVisible();
  await expect(page.getByTestId('document-control-matrix-preview-signoff')).toContainText('QA');
  await expect(page.getByTestId('document-control-matrix-preview-signoff')).toContainText('文档管理员');
  await expect(page.getByTestId('document-control-matrix-preview-signoff')).not.toContainText('注册');
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).toContainText('QA Reviewer');
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).not.toContainText('Reg');
});


adminTest('document control previews combined compiler and approver positions from matrix html @regression @docs', async ({
  page,
}) => {
  await mockBaseDocApis(
    page,
    baseDocument({
      title: '?????',
      file_subtype: '?????',
      registration_ref: '',
      current_revision: {
        controlled_revision_id: 'rev-1',
        controlled_document_id: 'doc-1',
        revision_no: 1,
        status: 'draft',
        filename: 'plan.pdf',
        kb_doc_id: 'kb-doc-1',
        approval_request_id: null,
        approval_round: 0,
        current_approval_step_no: null,
        current_approval_step_name: null,
        file_subtype: '?????',
        matrix_snapshot: null,
        position_snapshot: null,
      },
    })
  );

  await page.route('**/api/admin/quality-system-config', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        positions: [],
        file_categories: [{ id: 3, name: '?????', is_active: true }],
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
          file_subtype: '?????',
          compiler_check: {
            position_name: '??????????',
            matched: true,
            matched_user_ids: ['u_admin'],
          },
          signoff_steps: [
            {
              step_name: 'cosign',
              step_semantic: 'signoff',
              position_name: 'QA',
              approvers: [{ user_id: 'u-qa-1', full_name: 'QA Reviewer' }],
            },
            {
              step_name: 'standardize_review',
              step_semantic: 'signoff',
              position_name: '?????',
              approvers: [{ user_id: 'u-doc-1', full_name: 'Doc Admin' }],
            },
          ],
          approval_steps: [
            {
              step_name: 'approve',
              step_semantic: 'approval',
              position_name: '???????????',
              approvers: [
                { user_id: 'u-rd-1', full_name: 'RD Head' },
                { user_id: 'u-gm-1', full_name: 'General Manager' },
              ],
            },
          ],
        },
      }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await expect(page.getByTestId('document-control-matrix-preview-compiler')).toContainText('??????????');
  await expect(page.getByTestId('document-control-matrix-preview-approval')).toContainText('???????????');
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).toContainText('RD Head');
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).toContainText('General Manager');
});


adminTest('document control includes registration signoff when registration ref exists @regression @docs', async ({
  page,
}) => {
  await mockBaseDocApis(
    page,
    baseDocument({
      file_subtype: '\u4ea7\u54c1\u6280\u672f\u8981\u6c42',
      registration_ref: 'REG-100',
      current_revision: {
        controlled_revision_id: 'rev-1',
        controlled_document_id: 'doc-1',
        revision_no: 1,
        status: 'draft',
        filename: 'doc.pdf',
        kb_doc_id: 'kb-doc-1',
        approval_request_id: null,
        approval_round: 0,
        current_approval_step_no: null,
        current_approval_step_name: null,
        file_subtype: '\u4ea7\u54c1\u6280\u672f\u8981\u6c42',
        matrix_snapshot: null,
        position_snapshot: null,
      },
    })
  );

  await page.route('**/api/quality-system/doc-control/revisions/rev-1/matrix-preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        result: {
          file_subtype: '\u4ea7\u54c1\u6280\u672f\u8981\u6c42',
          compiler_check: { position_name: '\u9879\u76ee\u8d1f\u8d23\u4eba', matched: true, matched_user_ids: ['u_admin'] },
          signoff_steps: [
            {
              step_name: 'cosign',
              step_semantic: 'signoff',
              position_name: 'QA',
              approvers: [{ user_id: 'u-qa-1', full_name: 'QA Reviewer' }],
            },
            {
              step_name: 'cosign',
              step_semantic: 'signoff',
              position_name: '\u6ce8\u518c',
              approvers: [{ user_id: 'u-reg-1', full_name: 'Registration Reviewer' }],
            },
            {
              step_name: 'standardize_review',
              step_semantic: 'signoff',
              position_name: '\u6587\u6863\u7ba1\u7406\u5458',
              approvers: [{ user_id: 'u-doc-1', full_name: 'Doc Admin' }],
            },
          ],
          approval_steps: [
            {
              step_name: 'approve',
              step_semantic: 'approval',
              position_name: '\u7f16\u5236\u90e8\u95e8\u8d1f\u8d23\u4eba\u6216\u6388\u6743\u4ee3\u8868',
              approvers: [{ user_id: 'u-app-1', full_name: 'Approver One' }],
            },
          ],
        },
      }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await expect(page.getByTestId('document-control-matrix-preview-signoff')).toContainText('\u6ce8\u518c');
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).toContainText('Registration Reviewer');
});

adminTest('document control does not auto-include optional circle positions in preview @regression @docs', async ({
  page,
}) => {
  await mockBaseDocApis(
    page,
    baseDocument({
      title: '\u5de5\u827a\u6d41\u7a0b\u56fe',
      file_subtype: '\u5de5\u827a\u6d41\u7a0b\u56fe',
      current_revision: {
        controlled_revision_id: 'rev-1',
        controlled_document_id: 'doc-1',
        revision_no: 1,
        status: 'draft',
        filename: 'process.pdf',
        kb_doc_id: 'kb-doc-1',
        approval_request_id: null,
        approval_round: 0,
        current_approval_step_no: null,
        current_approval_step_name: null,
        file_subtype: '\u5de5\u827a\u6d41\u7a0b\u56fe',
        matrix_snapshot: null,
        position_snapshot: null,
      },
    })
  );

  await page.route('**/api/admin/quality-system-config', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        positions: [],
        file_categories: [{ id: 4, name: '\u5de5\u827a\u6d41\u7a0b\u56fe', is_active: true }],
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
          file_subtype: '\u5de5\u827a\u6d41\u7a0b\u56fe',
          compiler_check: { position_name: '\u6280\u672f\u4eba\u5458', matched: true, matched_user_ids: ['u_admin'] },
          signoff_steps: [
            {
              step_name: 'cosign',
              step_semantic: 'signoff',
              position_name: 'QMS',
              approvers: [{ user_id: 'u-qms-1', full_name: 'QMS Reviewer' }],
            },
            {
              step_name: 'standardize_review',
              step_semantic: 'signoff',
              position_name: '\u6587\u6863\u7ba1\u7406\u5458',
              approvers: [{ user_id: 'u-doc-1', full_name: 'Doc Admin' }],
            },
          ],
          approval_steps: [
            {
              step_name: 'approve',
              step_semantic: 'approval',
              position_name: '\u603b\u7ecf\u7406',
              approvers: [{ user_id: 'u-gm-1', full_name: 'General Manager' }],
            },
          ],
        },
      }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await expect(page.getByTestId('document-control-matrix-preview-signoff')).toContainText('QMS');
  await expect(page.getByTestId('document-control-matrix-preview-signoff')).not.toContainText('QC');
  await expect(page.getByTestId('document-control-matrix-preview-approvers')).not.toContainText('QC Reviewer');
});
