// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('admin can create user via UI @regression @admin', async ({ page }) => {
  const users = [];

  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(users),
    });
  });

  await mockJson(page, '**/api/permission-groups', {
    ok: true,
    data: [{ group_id: 101, group_name: 'viewer', description: 'viewer' }],
  });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E公司' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E部门' }]);

  let capturedCreateBody = null;
  await page.route('**/api/users', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedCreateBody = route.request().postDataJSON();

    const created = {
      user_id: `u_${Date.now()}`,
      username: capturedCreateBody.username,
      email: capturedCreateBody.email || null,
      company_id: capturedCreateBody.company_id,
      company_name: 'E2E公司',
      department_id: capturedCreateBody.department_id,
      department_name: 'E2E部门',
      group_id: null,
      group_ids: capturedCreateBody.group_ids || [],
      group_name: null,
      permission_groups: [{ group_id: 101, group_name: 'viewer' }],
      role: capturedCreateBody.role || 'viewer',
      status: capturedCreateBody.status || 'active',
      created_at_ms: Date.now(),
      last_login_at_ms: null,
    };
    users.unshift(created);

    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify(created),
    });
  });

  await page.goto('/users');

  await page.getByTestId('users-create-open').click();

  const username = `e2e_user_${Date.now()}`;
  await page.getByTestId('users-create-username').fill(username);
  await page.getByTestId('users-create-password').fill('Passw0rd!123');
  await page.getByTestId('users-create-email').fill('e2e@example.com');
  await page.getByTestId('users-create-company').selectOption('1');
  await page.getByTestId('users-create-department').selectOption('10');
  await page.getByTestId('users-create-group-101').check();
  await page.getByTestId('users-create-submit').click();

  expect(capturedCreateBody).toBeTruthy();
  expect(capturedCreateBody.username).toBe(username);
  expect(capturedCreateBody.company_id).toBe(1);
  expect(capturedCreateBody.department_id).toBe(10);
  expect(capturedCreateBody.group_ids).toEqual([101]);

  await expect(page.getByText(username, { exact: true })).toBeVisible();
});
