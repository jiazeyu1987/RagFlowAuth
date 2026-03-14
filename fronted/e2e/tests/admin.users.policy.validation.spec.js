// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('users policy modal validates ranges and blocks invalid submit @regression @admin', async ({ page }) => {
  const users = [
    {
      user_id: 'u_1',
      username: 'alice',
      email: 'alice@example.com',
      company_id: 1,
      company_name: 'E2E Company',
      department_id: 10,
      department_name: 'E2E Department',
      role: 'viewer',
      status: 'active',
      group_id: null,
      group_ids: [],
      group_name: null,
      permission_groups: [],
      max_login_sessions: 3,
      idle_timeout_minutes: 120,
      active_session_count: 0,
      active_session_last_activity_at_ms: null,
      created_at_ms: Date.now(),
      last_login_at_ms: null,
    },
  ];

  let putCount = 0;

  await page.route('**/api/users**', async (route) => {
    const req = route.request();
    if (req.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users) });
      return;
    }
    if (req.method() === 'PUT') {
      putCount += 1;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users[0]) });
      return;
    }
    await route.fallback();
  });

  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E Company' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E Department' }]);

  await page.goto('/users');
  await expect(page.getByTestId('users-row-u_1')).toBeVisible();

  await page.getByTestId('users-edit-policy-u_1').click();
  await expect(page.getByTestId('users-policy-modal')).toBeVisible();

  await page.getByTestId('users-policy-max-login-sessions').fill('0');
  await page.getByTestId('users-policy-save').click();
  await expect(page.getByTestId('users-policy-error')).toBeVisible();
  await expect(page.getByTestId('users-policy-modal')).toBeVisible();
  expect(putCount).toBe(0);

  await page.getByTestId('users-policy-max-login-sessions').fill('3');
  await page.getByTestId('users-policy-idle-timeout').fill('50000');
  await page.getByTestId('users-policy-save').click();
  await expect(page.getByTestId('users-policy-error')).toBeVisible();
  await expect(page.getByTestId('users-policy-modal')).toBeVisible();
  expect(putCount).toBe(0);
});
