// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('users list shows error on API failure @regression @admin', async ({ page }) => {
  await page.route('**/api/users**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'users list failed' }),
    });
  });

  // Keep other boot-time requests stable.
  await mockJson(page, '**/api/permission-groups', { ok: true, data: [] });
  await mockJson(page, '**/api/org/companies', []);
  await mockJson(page, '**/api/org/departments', []);

  await page.goto('/users');
  await expect(page.getByText('Error: users list failed')).toBeVisible();
});

