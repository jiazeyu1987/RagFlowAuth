// @ts-check
const { expect } = require('@playwright/test');
const { viewerTest } = require('../helpers/auth');

viewerTest('tools rbac: viewer cannot see nas card or access nas route @regression @rbac @tools', async ({ page }) => {
  await page.goto('/tools');

  await expect(page.getByTestId('tool-card-paper_download')).toBeVisible();
  await expect(page.getByTestId('tool-card-nas_browser')).toHaveCount(0);

  await page.goto('/tools/nas-browser');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});
