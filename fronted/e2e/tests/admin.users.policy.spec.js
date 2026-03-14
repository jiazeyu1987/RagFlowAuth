// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('users policy modal updates session limit and idle timeout @regression @admin', async ({ page }) => {
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
      max_login_sessions: 3,
      idle_timeout_minutes: 120,
      active_session_count: 0,
      active_session_last_activity_at_ms: null,
      created_at_ms: Date.now(),
      last_login_at_ms: null,
    },
  ];

  /** @type {{ max_login_sessions?: number, idle_timeout_minutes?: number } | null} */
  let lastUpdate = null;

  await page.route('**/api/users**', async (route) => {
    const req = route.request();
    if (req.method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users) });
      return;
    }
    if (req.method() === 'PUT') {
      const body = JSON.parse(req.postData() || '{}');
      lastUpdate = body;
      users[0] = {
        ...users[0],
        max_login_sessions: Number(body.max_login_sessions || users[0].max_login_sessions),
        idle_timeout_minutes: Number(body.idle_timeout_minutes || users[0].idle_timeout_minutes),
      };
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users[0]) });
      return;
    }
    await route.fallback();
  });

  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E公司' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E部门' }]);

  await page.goto('/users');
  await expect(page.getByTestId('users-row-u_1')).toBeVisible();

  await page.getByTestId('users-edit-policy-u_1').click();
  await expect(page.getByTestId('users-policy-modal')).toBeVisible();

  await page.getByTestId('users-policy-max-login-sessions').fill('7');
  await page.getByTestId('users-policy-idle-timeout').fill('45');
  await page.getByTestId('users-policy-save').click();

  await expect(page.getByTestId('users-policy-modal')).toHaveCount(0);
  await expect(page.getByTestId('users-row-u_1')).toContainText('7');
  await expect(page.getByTestId('users-row-u_1')).toContainText('45');

  expect(lastUpdate).toEqual({
    max_login_sessions: 7,
    idle_timeout_minutes: 45,
  });
});
