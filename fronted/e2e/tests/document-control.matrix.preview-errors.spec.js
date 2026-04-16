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

const documentPayload = {
  controlled_document_id: 'doc-err-1',
  doc_code: 'DHF-ERR-001',
  title: '矩阵错误校验',
  document_type: 'dhf',
  file_subtype: '设计验证方案/报告',
  target_kb_id: 'kb-1',
  product_name: '产品 A',
  registration_ref: 'REG-001',
  current_revision: {
    controlled_revision_id: 'rev-err-1',
    controlled_document_id: 'doc-err-1',
    revision_no: 1,
    status: 'draft',
    filename: 'err.pdf',
    kb_doc_id: 'kb-doc-err-1',
    approval_request_id: null,
    approval_round: 0,
    current_approval_step_no: null,
    current_approval_step_name: null,
    file_subtype: '设计验证方案/报告',
    matrix_snapshot: null,
    position_snapshot: null,
  },
  effective_revision: null,
  revisions: [],
};

async function mockBase(page) {
  await mockAuthMe(page, { capabilities: authCapabilities });
  await mockJson(page, '**/api/inbox**', { items: [], total: 0, unread_count: 0 });
  await page.route('**/api/quality-system/doc-control/documents?**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [documentPayload] }),
    });
  });
  await page.route('**/api/quality-system/doc-control/documents/doc-err-1', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ document: documentPayload }),
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
}

adminTest('document control shows compiler mismatch preview error @regression @docs', async ({ page }) => {
  await mockBase(page);
  await page.route('**/api/quality-system/doc-control/revisions/rev-err-1/matrix-preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'document_control_matrix_compiler_mismatch' }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await expect(page.getByTestId('document-control-matrix-preview-error')).toContainText(
    'The current user does not match the compiler role required by the approval matrix.'
  );
});

adminTest('document control shows unassigned position preview error @regression @docs', async ({ page }) => {
  await mockBase(page);
  await page.route('**/api/quality-system/doc-control/revisions/rev-err-1/matrix-preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'document_control_matrix_position_unassigned:QA' }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await expect(page.getByTestId('document-control-matrix-preview-error')).toContainText(
    'A required approval position has no assigned active users.'
  );
});

adminTest('document control shows matrix missing preview error @regression @docs', async ({ page }) => {
  await mockBase(page);
  await page.route('**/api/quality-system/doc-control/revisions/rev-err-1/matrix-preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'document_control_matrix_missing' }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await expect(page.getByTestId('document-control-matrix-preview-error')).toContainText(
    'The approval matrix is unavailable. Please contact an administrator.'
  );
});


adminTest('document control blocks approval submit when matrix remark requires usage scope @regression @docs', async ({ page }) => {
  await mockBase(page);
  await page.route('**/api/quality-system/doc-control/documents?**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const document = {
      ...documentPayload,
      title: '?????????????',
      file_subtype: '?????????????',
      current_revision: {
        ...documentPayload.current_revision,
        file_subtype: '?????????????',
      },
    };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [document] }),
    });
  });
  await page.route('**/api/quality-system/doc-control/documents/doc-err-1', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const document = {
      ...documentPayload,
      title: '?????????????',
      file_subtype: '?????????????',
      current_revision: {
        ...documentPayload.current_revision,
        file_subtype: '?????????????',
      },
    };
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
        file_categories: [{ id: 9, name: '?????????????', is_active: true }],
      }),
    });
  });
  await page.route('**/api/quality-system/doc-control/revisions/rev-err-1/matrix-preview', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'document_control_matrix_usage_scope_required' }),
    });
  });

  await page.goto('/quality-system/doc-control');
  await expect(page.getByTestId('document-control-matrix-preview-error')).toContainText(
    'This file subtype requires usage scope data before the approval matrix can be resolved.'
  );
  await expect(page.getByTestId('document-control-approval-submit')).toBeDisabled();
});
