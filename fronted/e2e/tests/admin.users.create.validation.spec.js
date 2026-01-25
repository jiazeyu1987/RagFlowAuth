// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('user create requires company/department @regression @admin', async ({ page }) => {
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', [{ id: 1, name: 'E2E鍏徃' }]);
  await mockJson(page, '**/api/org/departments', [{ id: 10, name: 'E2E閮ㄩ棬' }]);

  let capturedCreateBody = null;
  await page.route('**/api/users', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    capturedCreateBody = route.request().postDataJSON();
    await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ user_id: 'u_new' }) });
  });

  await page.goto('/users');
  await page.getByTestId('users-create-open').click();

  await page.getByTestId('users-create-username').fill(`e2e_user_${Date.now()}`);
  await page.getByTestId('users-create-password').fill('Passw0rd!123');
  await page.getByTestId('users-create-email').fill('e2e@example.com');

  // Do not select required company/department; the browser should block form submission.
  await page.getByTestId('users-create-submit').click();
  await page.waitForTimeout(300);

  expect(capturedCreateBody).toBeNull();
  await expect(page.getByTestId('users-create-form')).toBeVisible();
});

