// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('admin can assign permission groups to user via UI @regression @admin', async ({ page }) => {
  const groups = [
    { group_id: 101, group_name: 'viewer', description: 'viewer' },
    { group_id: 102, group_name: 'uploader', description: 'uploader' },
  ];

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
      group_ids: [102],
      group_name: null,
      permission_groups: [{ group_id: 102, group_name: 'uploader' }],
      created_at_ms: Date.now(),
      last_login_at_ms: null,
    },
  ];

  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(users),
    });
  });

  await mockJson(page, '**/api/permission-groups', { ok: true, data: groups });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E鍏徃' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E閮ㄩ棬' }]);

  let capturedUpdate = null;
  await page.route('**/api/users/*', async (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    capturedUpdate = route.request().postDataJSON();

    const userId = route.request().url().split('/').pop();
    const u = users.find((x) => x.user_id === userId);
    if (u) {
      u.group_ids = Array.isArray(capturedUpdate?.group_ids) ? capturedUpdate.group_ids : [];
      u.permission_groups = u.group_ids
        .map((gid) => groups.find((g) => g.group_id === gid))
        .filter(Boolean)
        .map((g) => ({ group_id: g.group_id, group_name: g.group_name }));
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(u || users[0]),
    });
  });

  await page.goto('/users');

  await page.getByTestId('users-edit-groups-u_1').click();
  await expect(page.getByTestId('users-group-modal')).toBeVisible();

  await expect(page.getByTestId('users-group-checkbox-102')).toBeChecked();
  await page.getByTestId('users-group-checkbox-101').check();
  await page.getByTestId('users-group-save').click();

  expect(capturedUpdate).toBeTruthy();
  expect(capturedUpdate.group_ids).toEqual([102, 101]);

  await expect(page.getByTestId('users-group-modal')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_1').getByText('viewer')).toBeVisible();
});
