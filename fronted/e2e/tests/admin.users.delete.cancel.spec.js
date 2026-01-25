// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('users delete confirm can be cancelled @regression @admin', async ({ page }) => {
  const users = [
    {
      user_id: 'u_1',
      username: 'bob',
      email: 'bob@example.com',
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

  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E鍏徃' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E閮ㄩ棬' }]);

  let deleteCalled = false;
  await page.route('**/api/users/*', async (route) => {
    if (route.request().method() !== 'DELETE') return route.fallback();
    deleteCalled = true;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/users');
  await expect(page.getByTestId('users-row-u_1')).toBeVisible();

  page.once('dialog', async (dialog) => {
    await dialog.dismiss();
  });
  await page.getByTestId('users-delete-u_1').click();

  // Give the click a moment to propagate; confirm-dismiss should prevent the request.
  await page.waitForTimeout(300);
  expect(deleteCalled).toBeFalsy();
  await expect(page.getByTestId('users-row-u_1')).toBeVisible();
});

