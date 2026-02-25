// @ts-check
const { expect } = require('@playwright/test');
const { adminTest, viewerTest } = require('../helpers/auth');

adminTest('root route redirects to chat and shell renders @regression @dashboard', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByTestId('layout-user-name')).toBeVisible();
  await expect(page.getByTestId('chat-page')).toBeVisible();
});

adminTest('admin can navigate to key routes from sidebar @regression @dashboard', async ({ page }) => {
  await page.goto('/chat');
  await page.getByTestId('nav-browser').click();
  await expect(page).toHaveURL(/\/browser$/);

  await page.getByTestId('nav-agents').click();
  await expect(page).toHaveURL(/\/agents$/);
});

viewerTest('viewer has no admin menu entries @regression @dashboard', async ({ page }) => {
  await page.goto('/chat');
  await expect(page.getByTestId('layout-user-name')).toBeVisible();

  await expect(page.getByTestId('nav-users')).toHaveCount(0);
  await expect(page.getByTestId('nav-permission-groups')).toHaveCount(0);
  await expect(page.getByTestId('nav-org-directory')).toHaveCount(0);
  await expect(page.getByTestId('nav-data-security')).toHaveCount(0);
  await expect(page.getByTestId('nav-logs')).toHaveCount(0);
});
