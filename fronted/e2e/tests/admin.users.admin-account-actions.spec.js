// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('admin account row only shows reset-password action @regression @admin', async ({ page }) => {
  const users = [
    {
      user_id: 'u_admin',
      username: 'admin',
      email: 'admin@example.com',
      company_id: 1,
      company_name: 'E2E公司',
      department_id: 10,
      department_name: 'E2E部门',
      role: 'admin',
      status: 'active',
      group_id: 1,
      group_ids: [1],
      group_name: 'admin',
      permission_groups: [{ group_id: 1, group_name: 'admin' }],
      created_at_ms: Date.now(),
      last_login_at_ms: null,
    },
    {
      user_id: 'u_1',
      username: 'alice',
      email: 'alice@example.com',
      company_id: 1,
      company_name: 'E2E公司',
      department_id: 10,
      department_name: 'E2E部门',
      role: 'viewer',
      status: 'active',
      group_id: null,
      group_ids: [],
      group_name: null,
      permission_groups: [],
      created_at_ms: Date.now(),
      last_login_at_ms: null,
    },
  ];

  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users) });
  });

  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E公司' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E部门' }]);

  await page.goto('/users');

  await expect(page.getByTestId('users-row-u_admin')).toBeVisible();
  await expect(page.getByTestId('users-reset-password-u_admin')).toBeVisible();
  await expect(page.getByTestId('users-edit-policy-u_admin')).toHaveCount(0);
  await expect(page.getByTestId('users-edit-groups-u_admin')).toHaveCount(0);
  await expect(page.getByTestId('users-toggle-status-u_admin')).toHaveCount(0);
  await expect(page.getByTestId('users-delete-u_admin')).toHaveCount(0);

  await expect(page.getByTestId('users-edit-policy-u_1')).toBeVisible();
  await expect(page.getByTestId('users-edit-groups-u_1')).toBeVisible();
  await expect(page.getByTestId('users-toggle-status-u_1')).toBeVisible();
  await expect(page.getByTestId('users-delete-u_1')).toBeVisible();
});
