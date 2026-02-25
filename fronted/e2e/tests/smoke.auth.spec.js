// @ts-check
const { test, expect } = require('@playwright/test');

test('login rejects wrong password @smoke', async ({ page }) => {
  await page.goto('/login');

  await page.getByTestId('login-username').fill('admin');
  await page.getByTestId('login-password').fill('wrong-password');
  await page.getByTestId('login-submit').click();

  await expect(page.getByTestId('login-error')).toBeVisible();
});

test('login works via UI @smoke', async ({ page }) => {
  await page.goto('/login');

  await page.getByTestId('login-username').fill(process.env.E2E_ADMIN_USER || 'admin');
  await page.getByTestId('login-password').fill(process.env.E2E_ADMIN_PASS || 'admin123');
  await page.getByTestId('login-submit').click();

  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByTestId('layout-sidebar')).toBeVisible();
});
