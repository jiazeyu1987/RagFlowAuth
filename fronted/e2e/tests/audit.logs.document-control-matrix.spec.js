// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, mockAuthMe } = require('../helpers/auth');

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
  document_control: {
    create: { scope: 'all', targets: [] },
    review: { scope: 'all', targets: [] },
    publish: { scope: 'all', targets: [] },
    obsolete: { scope: 'all', targets: [] },
  },
  audit_events: {
    view: { scope: 'all', targets: [] },
  },
};

adminTest('audit logs shows document control matrix transition context @regression @audit', async ({
  page,
}) => {
  await mockAuthMe(page, { capabilities: authCapabilities });

  const companies = [{ id: 1, name: 'company-a' }];
  const departments = [{ id: 10, company_id: 1, name: 'dept-rd', path_name: 'company-a / dept-rd' }];
  const events = [
    {
      id: 'audit-doc-1',
      action: 'document_control_transition',
      actor: 'u_admin',
      username: 'admin',
      company_id: 1,
      company_name: 'company-a',
      department_id: 10,
      department_name: 'dept-rd',
      created_at_ms: new Date('2026-04-16T12:00:00+08:00').getTime(),
      source: 'document_control',
      resource_id: 'rev-1',
      event_type: 'controlled_revision_submit',
      after: {
        file_subtype: '设计验证方案/报告',
        current_approval_step_name: 'cosign',
      },
      meta: {
        matrix_mode: 'approval_matrix',
      },
    },
  ];

  await page.route('**/api/inbox**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0, unread_count: 0 }) });
  });
  await page.route('**/api/org/companies', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(companies) });
  });
  await page.route('**/api/org/departments', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(departments) });
  });
  await page.route('**/api/audit/events**', async (route) => {
    const url = new URL(route.request().url());
    const source = String(url.searchParams.get('source') || '').trim();
    const action = String(url.searchParams.get('action') || '').trim();
    let filtered = events.slice();
    if (source) filtered = filtered.filter((item) => item.source === source);
    if (action) filtered = filtered.filter((item) => item.action === action);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total: filtered.length, items: filtered }),
    });
  });

  await page.goto('/logs');

  await expect(page.getByTestId('audit-table')).toContainText('文控审批流转');
  await expect(page.getByTestId('audit-table')).toContainText('文控审批');
  await expect(page.getByTestId('audit-table')).toContainText('文件小类：设计验证方案/报告');
  await expect(page.getByTestId('audit-table')).toContainText('当前步骤：cosign');
  await expect(page.getByTestId('audit-table')).toContainText('模式：approval_matrix');

  await page.getByTestId('audit-filter-source').selectOption('document_control');
  await page.getByTestId('audit-filter-action').selectOption('document_control_transition');
  await page.getByTestId('audit-apply').click();

  await expect(page.getByTestId('audit-total')).toHaveText('1');
  await expect(page.getByTestId('audit-table')).toContainText('文控审批流转');
});
