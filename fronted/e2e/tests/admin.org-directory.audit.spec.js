// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('admin can create company/department and see audit (mocked) @regression @admin', async ({ page }) => {
  const companies = [];
  const departments = [];
  const audit = [];

  await page.route('**/api/org/companies', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(companies) });
    }
    if (method === 'POST') {
      const body = route.request().postDataJSON();
      const created = { id: companies.length + 1, name: body.name, updated_at_ms: Date.now() };
      companies.push(created);
      audit.unshift({
        id: `a_${Date.now()}`,
        entity_type: 'company',
        action: 'create',
        before_name: null,
        after_name: created.name,
        actor_username: 'admin',
        actor_user_id: 'u_admin',
        created_at_ms: Date.now(),
      });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created) });
    }
    return route.fallback();
  });

  await page.route('**/api/org/departments', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(departments) });
    }
    if (method === 'POST') {
      const body = route.request().postDataJSON();
      const created = { id: departments.length + 1, name: body.name, updated_at_ms: Date.now() };
      departments.push(created);
      audit.unshift({
        id: `a_${Date.now()}`,
        entity_type: 'department',
        action: 'create',
        before_name: null,
        after_name: created.name,
        actor_username: 'admin',
        actor_user_id: 'u_admin',
        created_at_ms: Date.now(),
      });
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created) });
    }
    return route.fallback();
  });

  await page.route('**/api/org/audit**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(audit) });
  });

  await page.goto('/org-directory');

  const companyName = 'E2E公司';
  await page.getByTestId('org-company-name').fill(companyName);
  await page.getByTestId('org-company-add').click();
  await expect(page.getByText(companyName, { exact: true })).toBeVisible();

  const departmentName = 'E2E部门';
  await page.getByTestId('org-tab-departments').click();
  await page.getByTestId('org-department-name').fill(departmentName);
  await page.getByTestId('org-department-add').click();
  await expect(page.getByText(departmentName, { exact: true })).toBeVisible();

  await page.getByTestId('org-tab-audit').click();
  await expect(page.getByText(companyName)).toBeVisible();
  await expect(page.getByText(departmentName)).toBeVisible();
});

