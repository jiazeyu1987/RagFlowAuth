// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('users assign groups shows error on save failure @regression @admin', async ({ page }) => {
  const groups = [{ group_id: 101, group_name: 'viewer', description: 'viewer' }];
  const users = [
    {
      user_id: 'u_1',
      username: 'alice',
      email: 'alice@example.com',
      company_id: 1,
      company_name: 'E2E鍏徃',
      department_id: 10,
      department_name: 'E2E閮ㄩ棬',
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

  await mockJson(page, '**/api/permission-groups', { ok: true, data: groups });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E鍏徃' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E閮ㄩ棬' }]);

  await page.route('**/api/users/u_1', async (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'update failed' }),
    });
  });

  await page.goto('/users');
  await page.getByTestId('users-edit-groups-u_1').click();
  await expect(page.getByTestId('users-group-modal')).toBeVisible();

  await page.getByTestId('users-group-checkbox-101').check();
  await page.getByTestId('users-group-save').click();

  await expect(page.getByText('Error: update failed')).toBeVisible();
});

