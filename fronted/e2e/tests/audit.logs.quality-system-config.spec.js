// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, mockAuthMe } = require('../helpers/auth');

function toMs(iso) {
  return new Date(iso).getTime();
}

adminTest('audit logs shows and filters quality system config events @regression @audit', async ({ page }) => {
  await mockAuthMe(page);

  const companies = [{ id: 1, name: 'company-a' }];
  const departments = [{ id: 10, company_id: 1, name: 'dept-rd', path_name: 'company-a / dept-rd' }];
  const events = [
    {
      id: 1,
      action: 'quality_system_position_assignments_update',
      actor: 'u_admin',
      username: 'admin',
      company_id: 1,
      company_name: 'company-a',
      department_id: 10,
      department_name: 'dept-rd',
      created_at_ms: toMs('2026-04-16T09:00:00'),
      source: 'quality_system_config',
      resource_id: 'QA',
      event_type: 'config_change',
      reason: 'Assign QA owners',
    },
    {
      id: 2,
      action: 'quality_system_file_category_create',
      actor: 'u_admin',
      username: 'admin',
      company_id: 1,
      company_name: 'company-a',
      department_id: 10,
      department_name: 'dept-rd',
      created_at_ms: toMs('2026-04-16T10:00:00'),
      source: 'quality_system_config',
      resource_id: '新增文件小类',
      event_type: 'config_change',
      reason: 'Add custom category',
    },
    {
      id: 3,
      action: 'document_upload',
      actor: 'u_admin',
      username: 'admin',
      company_id: 1,
      company_name: 'company-a',
      department_id: 10,
      department_name: 'dept-rd',
      created_at_ms: toMs('2026-04-16T11:00:00'),
      source: 'knowledge',
      filename: 'upload-a.pdf',
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
    const req = route.request();
    if (req.method() !== 'GET') return route.fallback();
    const url = new URL(req.url());
    const action = String(url.searchParams.get('action') || '').trim();
    const source = String(url.searchParams.get('source') || '').trim();
    const resourceId = String(url.searchParams.get('resource_id') || '').trim();

    let filtered = events.slice();
    if (action) filtered = filtered.filter((item) => item.action === action);
    if (source) filtered = filtered.filter((item) => item.source === source);
    if (resourceId) filtered = filtered.filter((item) => item.resource_id === resourceId);

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total: filtered.length, items: filtered }),
    });
  });

  await page.goto('/logs');
  await expect(page.getByTestId('audit-logs-page')).toBeVisible();
  await expect(page.getByTestId('audit-total')).toHaveText('3');
  await expect(page.getByTestId('audit-table')).toContainText('更新体系岗位分配');
  await expect(page.getByTestId('audit-table')).toContainText('新增体系文件小类');
  await expect(page.getByTestId('audit-table')).toContainText('体系配置');

  await page.getByTestId('audit-filter-source').selectOption('quality_system_config');
  await page.getByTestId('audit-apply').click();
  await expect(page.getByTestId('audit-total')).toHaveText('2');
  await expect(page.getByTestId('audit-table')).toContainText('QA');
  await expect(page.getByTestId('audit-table')).toContainText('新增文件小类');

  await page.getByTestId('audit-filter-action').selectOption('quality_system_file_category_create');
  await page.getByTestId('audit-filter-resource-id').fill('新增文件小类');
  await page.getByTestId('audit-apply').click();
  await expect(page.getByTestId('audit-total')).toHaveText('1');
  await expect(page.getByTestId('audit-table')).toContainText('新增体系文件小类');
  await expect(page.getByTestId('audit-table')).not.toContainText('更新体系岗位分配');
});
