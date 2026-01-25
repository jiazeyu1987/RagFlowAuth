// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('admin can edit/delete org directory and filter audit (mocked) @regression @admin', async ({ page }) => {
  const companies = [];
  const departments = [];
  const audit = [];
  let auditSeq = 1;

  const pushAudit = (entry) => {
    audit.unshift({ id: `a_${auditSeq++}`, created_at_ms: Date.now(), actor_username: 'admin', actor_user_id: 'u_admin', ...entry });
  };

  await page.route('**/api/org/companies**', async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(companies) });
    }

    if (method === 'POST' && url.pathname.endsWith('/api/org/companies')) {
      const body = route.request().postDataJSON();
      const created = { id: companies.length + 1, name: body.name, updated_at_ms: Date.now() };
      companies.push(created);
      pushAudit({ entity_type: 'company', action: 'create', before_name: null, after_name: created.name });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created) });
    }

    if (method === 'PUT') {
      const id = Number(url.pathname.split('/').pop());
      const body = route.request().postDataJSON();
      const found = companies.find((c) => c.id === id);
      if (!found) return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) });
      const before = found.name;
      found.name = body.name;
      found.updated_at_ms = Date.now();
      pushAudit({ entity_type: 'company', action: 'update', before_name: before, after_name: found.name });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(found) });
    }

    if (method === 'DELETE') {
      const id = Number(url.pathname.split('/').pop());
      const idx = companies.findIndex((c) => c.id === id);
      if (idx === -1) return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) });
      const [removed] = companies.splice(idx, 1);
      pushAudit({ entity_type: 'company', action: 'delete', before_name: removed.name, after_name: null });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }

    return route.fallback();
  });

  await page.route('**/api/org/departments**', async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(departments) });
    }

    if (method === 'POST' && url.pathname.endsWith('/api/org/departments')) {
      const body = route.request().postDataJSON();
      const created = { id: departments.length + 1, name: body.name, updated_at_ms: Date.now() };
      departments.push(created);
      pushAudit({ entity_type: 'department', action: 'create', before_name: null, after_name: created.name });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created) });
    }

    if (method === 'PUT') {
      const id = Number(url.pathname.split('/').pop());
      const body = route.request().postDataJSON();
      const found = departments.find((d) => d.id === id);
      if (!found) return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) });
      const before = found.name;
      found.name = body.name;
      found.updated_at_ms = Date.now();
      pushAudit({ entity_type: 'department', action: 'update', before_name: before, after_name: found.name });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(found) });
    }

    if (method === 'DELETE') {
      const id = Number(url.pathname.split('/').pop());
      const idx = departments.findIndex((d) => d.id === id);
      if (idx === -1) return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) });
      const [removed] = departments.splice(idx, 1);
      pushAudit({ entity_type: 'department', action: 'delete', before_name: removed.name, after_name: null });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }

    return route.fallback();
  });

  await page.route('**/api/org/audit**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = new URL(route.request().url());
    const entityType = url.searchParams.get('entity_type') || '';
    const action = url.searchParams.get('action') || '';
    const filtered = audit.filter((l) => (!entityType || l.entity_type === entityType) && (!action || l.action === action));
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(filtered) });
  });

  await page.goto('/org-directory');

  await page.getByTestId('org-company-name').fill('E2E公司');
  await page.getByTestId('org-company-add').click();
  await expect(page.getByText('E2E公司', { exact: true })).toBeVisible();

  await page.getByTestId('org-tab-departments').click();
  await page.getByTestId('org-department-name').fill('E2E部门');
  await page.getByTestId('org-department-add').click();
  await expect(page.getByText('E2E部门', { exact: true })).toBeVisible();

  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('prompt');
    await dialog.accept('E2E公司-改');
  });
  await page.getByTestId('org-tab-companies').click();
  await page.getByTestId('org-company-edit-1').click();
  await expect(page.getByText('E2E公司-改', { exact: true })).toBeVisible();

  page.once('dialog', async (dialog) => {
    expect(dialog.type()).toBe('confirm');
    await dialog.accept();
  });
  await page.getByTestId('org-tab-departments').click();
  await page.getByTestId('org-department-delete-1').click();
  await expect(page.getByTestId('org-department-row-1')).toHaveCount(0);

  await page.getByTestId('org-tab-audit').click();
  await page.getByTestId('org-audit-refresh').click();
  await expect(page.getByText('E2E公司-改')).toBeVisible();
  await expect(page.getByText('删除：E2E部门')).toBeVisible();

  await page.getByTestId('org-audit-entity-type').selectOption('company');
  await page.getByTestId('org-audit-action').selectOption('update');
  await page.getByTestId('org-audit-refresh').click();
  await expect(page.locator('[data-testid^="org-audit-row-"]')).toHaveCount(1);
  await expect(page.getByText('E2E公司 → E2E公司-改')).toBeVisible();
});
