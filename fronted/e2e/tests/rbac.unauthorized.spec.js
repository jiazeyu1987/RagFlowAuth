// @ts-check
const { expect } = require('@playwright/test');
const { viewerTest } = require('../helpers/auth');

viewerTest('viewer cannot access /users @rbac', async ({ page }) => {
  await page.goto('/users');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});
