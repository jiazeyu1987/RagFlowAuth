// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('drug admin resolve and verify failures show error messages @regression @tools @drug-admin', async ({ page }) => {
  await page.route('**/api/drug-admin/provinces', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        validated_on: '2026-03-08',
        source: 'e2e-mock',
        provinces: [{ name: '国家药监局' }],
      }),
    });
  });

  await page.route('**/api/drug-admin/resolve', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'resolve_failed_test' }) });
  });

  await page.route('**/api/drug-admin/verify', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'verify_failed_test' }) });
  });

  await page.goto('/tools/drug-admin');
  await expect(page.getByTestId('drug-admin-page')).toBeVisible();

  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/drug-admin/resolve' && resp.request().method() === 'POST'),
    page.getByTestId('drug-admin-open-selected').click(),
  ]);
  await expect(page.getByText('resolve_failed_test')).toBeVisible();

  await Promise.all([
    page.waitForResponse((resp) => new URL(resp.url()).pathname === '/api/drug-admin/verify' && resp.request().method() === 'POST'),
    page.getByTestId('drug-admin-verify-all').click(),
  ]);
  await expect(page.getByText('verify_failed_test')).toBeVisible();
});
