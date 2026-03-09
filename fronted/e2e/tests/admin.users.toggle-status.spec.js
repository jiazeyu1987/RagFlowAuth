// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('users can be disabled and re-enabled from table actions @regression @admin', async ({ page }) => {
  const users = [
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
    const req = route.request();
    if (req.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users) });
      return;
    }
    if (req.method() === 'PUT') {
      const url = new URL(req.url());
      const userId = url.pathname.split('/').filter(Boolean).pop();
      const body = JSON.parse(req.postData() || '{}');
      const idx = users.findIndex((u) => u.user_id === userId);
      if (idx >= 0 && typeof body.status === 'string') {
        users[idx] = { ...users[idx], status: body.status };
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users[idx]) });
        return;
      }
      await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'user_not_found' }) });
      return;
    }
    await route.fallback();
  });

  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E公司' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E部门' }]);

  await page.goto('/users');

  await expect(page.getByTestId('users-row-u_1')).toBeVisible();
  await expect(page.getByTestId('users-toggle-status-u_1')).toHaveText('禁用');
  await expect(page.getByTestId('users-row-u_1').getByText('激活')).toBeVisible();

  await page.getByTestId('users-toggle-status-u_1').click();
  await expect(page.getByTestId('users-toggle-status-u_1')).toHaveText('解禁');
  await expect(page.getByTestId('users-row-u_1').getByText('停用')).toBeVisible();

  await page.getByTestId('users-toggle-status-u_1').click();
  await expect(page.getByTestId('users-toggle-status-u_1')).toHaveText('禁用');
  await expect(page.getByTestId('users-row-u_1').getByText('激活')).toBeVisible();
});

