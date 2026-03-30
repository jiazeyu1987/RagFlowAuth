// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('admin create user shows duplicate username error @regression @admin', async ({ page }) => {
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await mockJson(page, '**/api/permission-groups', {
    ok: true,
    data: [{ group_id: 101, group_name: 'viewer', description: 'viewer' }],
  });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E公司' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E部门' }]);

  await page.route('**/api/users', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'username_already_exists' }),
    });
  });

  await page.goto('/users');
  await page.getByTestId('users-create-open').click();
  await page.getByTestId('users-create-full-name').fill('Admin Duplicate');
  await page.getByTestId('users-create-username').fill('admin');
  await page.getByTestId('users-create-password').fill('Passw0rd!123');
  await page.getByTestId('users-create-company').selectOption('1');
  await page.getByTestId('users-create-department').selectOption('10');
  await page.getByTestId('users-create-group-101').check();
  await page.getByTestId('users-create-submit').click();

  await expect(page.getByTestId('users-create-error')).toHaveText('用户名已存在');
  await expect(page.getByTestId('users-create-form')).toBeVisible();
});
