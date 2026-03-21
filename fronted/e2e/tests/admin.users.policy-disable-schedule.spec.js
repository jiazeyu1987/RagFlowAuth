// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('users policy supports disable-until and disallow-change-password @regression @admin', async ({ page }) => {
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
      can_change_password: true,
      disable_login_enabled: false,
      disable_login_until_ms: null,
      group_id: null,
      group_ids: [],
      group_name: null,
      permission_groups: [],
      max_login_sessions: 3,
      idle_timeout_minutes: 120,
      created_at_ms: Date.now(),
      last_login_at_ms: null,
    },
  ];

  let capturedUpdateBody = null;

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
      capturedUpdateBody = body;
      const idx = users.findIndex((u) => u.user_id === userId);
      if (idx >= 0) {
        users[idx] = { ...users[idx], ...body };
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(users[idx]) });
        return;
      }
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'user_not_found' }),
      });
      return;
    }
    await route.fallback();
  });

  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E公司' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E部门' }]);

  await page.goto('/users');
  await page.getByTestId('users-edit-policy-u_1').click();
  await expect(page.getByTestId('users-policy-modal')).toBeVisible();

  await page.getByTestId('users-policy-can-change-password').check();
  await page.getByTestId('users-policy-disable-account-enabled').check();
  await page.getByTestId('users-policy-disable-mode-until').check();

  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const yyyy = `${tomorrow.getFullYear()}`;
  const mm = `${tomorrow.getMonth() + 1}`.padStart(2, '0');
  const dd = `${tomorrow.getDate()}`.padStart(2, '0');
  const dateText = `${yyyy}-${mm}-${dd}`;

  await page.getByTestId('users-policy-disable-until-date').fill(dateText);
  await page.getByTestId('users-policy-save').click();

  expect(capturedUpdateBody).toBeTruthy();
  expect(capturedUpdateBody.can_change_password).toBe(false);
  expect(capturedUpdateBody.disable_login_enabled).toBe(true);
  expect(capturedUpdateBody.status).toBe('active');
  expect(typeof capturedUpdateBody.disable_login_until_ms).toBe('number');
  expect(capturedUpdateBody.disable_login_until_ms).toBeGreaterThan(Date.now());
});
