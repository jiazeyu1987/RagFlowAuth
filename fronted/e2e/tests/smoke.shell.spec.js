// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('app shell renders for admin @smoke @admin', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByTestId('layout-sidebar')).toBeVisible();
  await expect(page.getByTestId('layout-user-name')).toHaveText(/admin/i);
  await expect(page.getByTestId('nav-users')).toBeVisible();
  await expect(page.getByTestId('nav-upload')).toBeVisible();

  await page.getByTestId('layout-logout').click();
  await expect(page).toHaveURL(/\/login$/);
});
