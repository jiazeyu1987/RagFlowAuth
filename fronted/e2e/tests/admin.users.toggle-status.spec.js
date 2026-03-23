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

  await expect(page.getByTestId('users-row-u_1')).toBeVisible();
  await expect(page.getByTestId('users-toggle-status-u_1')).toHaveText('禁用');

  await page.getByTestId('users-toggle-status-u_1').click();
  await expect(page.getByTestId('users-disable-modal')).toBeVisible();
  await page.getByTestId('users-disable-confirm').click();
  await expect(page.getByTestId('users-disable-modal')).toHaveCount(0);
  await expect(page.getByTestId('users-toggle-status-u_1')).toHaveText('解禁');

  await page.getByTestId('users-toggle-status-u_1').click();
  await expect(page.getByTestId('users-toggle-status-u_1')).toHaveText('禁用');
});

adminTest('users can be disabled until a date from table actions @regression @admin', async ({ page }) => {
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
      disable_login_enabled: false,
      disable_login_until_ms: null,
      group_id: null,
      group_ids: [],
      group_name: null,
      permission_groups: [],
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

  await page.getByTestId('users-toggle-status-u_1').click();
  await expect(page.getByTestId('users-disable-modal')).toBeVisible();
  await page.getByTestId('users-disable-mode-until').check();

  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
  const yyyy = `${tomorrow.getFullYear()}`;
  const mm = `${tomorrow.getMonth() + 1}`.padStart(2, '0');
  const dd = `${tomorrow.getDate()}`.padStart(2, '0');
  const dateText = `${yyyy}-${mm}-${dd}`;

  await page.getByTestId('users-disable-until-date').fill(dateText);
  await page.getByTestId('users-disable-confirm').click();

  expect(capturedUpdateBody).toBeTruthy();
  expect(capturedUpdateBody.status).toBe('active');
  expect(capturedUpdateBody.disable_login_enabled).toBe(true);
  expect(typeof capturedUpdateBody.disable_login_until_ms).toBe('number');
  expect(capturedUpdateBody.disable_login_until_ms).toBeGreaterThan(Date.now());
  await expect(page.getByTestId('users-toggle-status-u_1')).toHaveText('解禁');
});
