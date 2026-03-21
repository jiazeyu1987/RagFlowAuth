// @ts-check
const { test, expect } = require('@playwright/test');

test('disabled account shows blocked login message @regression @auth', async ({ page }) => {
  await page.route('**/api/auth/login', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 403,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'account_disabled' }),
    });
  });

  await page.goto('/login');
  await page.getByTestId('login-username').fill('disabled-user');
  await page.getByTestId('login-password').fill('password123');
  await page.getByTestId('login-submit').click();

  await expect(page.getByTestId('login-error')).toBeVisible();
  await expect(page.getByTestId('login-error')).not.toHaveText('');
});
