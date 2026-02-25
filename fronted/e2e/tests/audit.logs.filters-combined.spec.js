// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

function toMs(iso) {
  return new Date(iso).getTime();
}

adminTest('audit logs supports combined filters and total count (mock) @regression @audit', async ({ page }) => {
  const companies = [
    { id: 1, name: 'company-a' },
    { id: 2, name: 'company-b' },
  ];
  const departments = [
    { id: 10, name: 'dept-rd' },
    { id: 20, name: 'dept-mkt' },
  ];

  const events = [
    {
      id: 1,
      action: 'document_upload',
      actor: 'u_admin',
      username: 'admin',
      company_id: 1,
      company_name: 'company-a',
      department_id: 10,
      department_name: 'dept-rd',
      created_at_ms: toMs('2026-02-24T10:00:00'),
      source: 'knowledge',
      filename: 'upload-a.txt',
      kb_name: 'kb-a',
    },
    {
      id: 2,
      action: 'document_delete',
      actor: 'u_admin',
      username: 'admin',
      company_id: 1,
      company_name: 'company-a',
      department_id: 10,
      department_name: 'dept-rd',
      created_at_ms: toMs('2026-02-24T11:00:00'),
      source: 'knowledge',
      filename: 'delete-a.txt',
      kb_name: 'kb-a',
    },
    {
      id: 3,
      action: 'auth_login',
      actor: 'u_viewer',
      username: 'viewer',
      company_id: 2,
      company_name: 'company-b',
      department_id: 20,
      department_name: 'dept-mkt',
      created_at_ms: toMs('2026-02-24T12:00:00'),
      source: 'auth',
      filename: '',
      kb_name: '',
    },
  ];

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
    const action = (url.searchParams.get('action') || '').trim();
    const username = (url.searchParams.get('username') || '').trim();
    const companyId = (url.searchParams.get('company_id') || '').trim();
    const departmentId = (url.searchParams.get('department_id') || '').trim();
    const fromMsRaw = (url.searchParams.get('from_ms') || '').trim();
    const toMsRaw = (url.searchParams.get('to_ms') || '').trim();
    const limit = Math.max(1, Number(url.searchParams.get('limit') || '200'));
    const offset = Math.max(0, Number(url.searchParams.get('offset') || '0'));

    let filtered = events.slice();
    if (action) filtered = filtered.filter((e) => e.action === action);
    if (username) filtered = filtered.filter((e) => e.username === username);
    if (companyId) filtered = filtered.filter((e) => String(e.company_id) === companyId);
    if (departmentId) filtered = filtered.filter((e) => String(e.department_id) === departmentId);
    if (fromMsRaw) filtered = filtered.filter((e) => e.created_at_ms >= Number(fromMsRaw));
    if (toMsRaw) filtered = filtered.filter((e) => e.created_at_ms <= Number(toMsRaw));

    const total = filtered.length;
    const items = filtered.slice(offset, offset + limit);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total, items }),
    });
  });

  await page.goto('/logs');
  await expect(page.getByTestId('audit-logs-page')).toBeVisible();
  await expect(page.getByTestId('audit-total')).toHaveText('3');
  await expect(page.getByTestId('audit-table')).toContainText('upload-a.txt');
  await expect(page.getByTestId('audit-table')).toContainText('delete-a.txt');

  await page.getByTestId('audit-filter-action').selectOption('document_upload');
  await page.getByTestId('audit-filter-company').selectOption('1');
  await page.getByTestId('audit-filter-department').selectOption('10');
  await page.getByTestId('audit-filter-username').fill('admin');
  await page.getByTestId('audit-filter-from').fill('2026-02-24T00:00');
  await page.getByTestId('audit-filter-to').fill('2026-02-24T10:30');
  await page.getByTestId('audit-apply').click();

  await expect(page.getByTestId('audit-total')).toHaveText('1');
  await expect(page.getByTestId('audit-table')).toContainText('upload-a.txt');
  await expect(page.getByTestId('audit-table')).not.toContainText('delete-a.txt');

  await page.getByTestId('audit-filter-username').fill('nobody');
  await page.getByTestId('audit-apply').click();
  await expect(page.getByTestId('audit-total')).toHaveText('0');
  await expect(page.getByTestId('audit-table')).not.toContainText('upload-a.txt');
});
