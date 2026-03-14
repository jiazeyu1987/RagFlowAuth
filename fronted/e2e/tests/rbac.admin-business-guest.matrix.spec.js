// @ts-check
const { test, expect } = require('@playwright/test');
const { adminTest, viewerTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('rbac matrix: admin can see admin nav and access users management @regression @rbac', async ({ page }) => {
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });
  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', []);
  await mockJson(page, '**/api/org/departments', []);

  await page.goto('/chat');
  await expect(page.getByTestId('chat-page')).toBeVisible();
  await expect(page.getByTestId('nav-users')).toBeVisible();
  await expect(page.getByTestId('nav-permission-groups')).toBeVisible();
  await expect(page.getByTestId('nav-org-directory')).toBeVisible();
  await expect(page.getByTestId('nav-logs')).toBeVisible();

  await page.goto('/users');
  await expect(page).toHaveURL(/\/users$/);
  await expect(page.getByTestId('users-create-open')).toBeVisible();
});

viewerTest('rbac matrix: business user can use chat but is blocked from admin routes @regression @rbac', async ({ page }) => {
  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ chats: [] }),
    });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('chat-page')).toBeVisible();
  await expect(page.getByTestId('nav-users')).toHaveCount(0);
  await expect(page.getByTestId('nav-permission-groups')).toHaveCount(0);
  await expect(page.getByTestId('nav-org-directory')).toHaveCount(0);
  await expect(page.getByTestId('nav-logs')).toHaveCount(0);

  await page.goto('/users');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();

  await page.goto('/permission-groups');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});

test('rbac matrix: guest is redirected to login for protected routes @regression @rbac', async ({ page }) => {
  await page.goto('/chat');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByTestId('login-submit')).toBeVisible();

  await page.goto('/users');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByTestId('login-submit')).toBeVisible();
});
