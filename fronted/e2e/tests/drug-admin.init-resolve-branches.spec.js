// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('drug admin: provinces init loading failure branch @regression @tools @drug-admin', async ({ page }) => {
  await page.route('**/api/drug-admin/provinces', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'provinces_load_failed_test' }),
    });
  });

  await page.goto('/tools/drug-admin');
  await expect(page.getByText('provinces_load_failed_test')).toBeVisible();
});

adminTest('drug admin: resolve ok=false shows unreachable and errors without opening url @regression @tools @drug-admin', async ({ page }) => {
  await page.addInitScript(() => {
    window.__openedUrls = [];
    window.open = (...args) => {
      window.__openedUrls.push(String(args[0] || ''));
      return null;
    };
  });

  await page.route('**/api/drug-admin/provinces', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
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
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: false,
        code: 503,
        errors: ['timeout'],
      }),
    });
  });

  await page.goto('/tools/drug-admin');
  await page.getByTestId('drug-admin-open-selected').click();

  await expect(page.getByText('is not reachable now')).toBeVisible();
  await expect(page.getByText('Latest resolve errors')).toBeVisible();
  await expect(page.getByText('timeout')).toBeVisible();

  const opened = await page.evaluate(() => window.__openedUrls || []);
  expect(opened.length).toBe(0);
});
