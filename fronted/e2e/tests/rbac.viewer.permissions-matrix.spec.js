// @ts-check
const { expect } = require('@playwright/test');
const { viewerTest } = require('../helpers/auth');

viewerTest('viewer sidebar only shows allowed entries and blocks admin routes @regression @rbac', async ({ page }) => {
  await page.goto('/chat');
  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByTestId('chat-page')).toBeVisible();

  // Hidden menu entries for viewer.
  await expect(page.getByTestId('nav-upload')).toHaveCount(0);
  await expect(page.getByTestId('nav-documents')).toHaveCount(0);
  await expect(page.getByTestId('nav-users')).toHaveCount(0);
  await expect(page.getByTestId('nav-permission-groups')).toHaveCount(0);
  await expect(page.getByTestId('nav-org-directory')).toHaveCount(0);
  await expect(page.getByTestId('nav-data-security')).toHaveCount(0);
  await expect(page.getByTestId('nav-logs')).toHaveCount(0);

  // Explicit route guards.
  await page.goto('/users');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();

  await page.goto('/logs');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});

