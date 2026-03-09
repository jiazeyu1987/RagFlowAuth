// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('drug admin: resolve selected province and verify all status @regression @tools @drug-admin', async ({ page }) => {
  let resolveBody = null;
  let verifyCalled = 0;

  await page.addInitScript(() => {
    window.__openedUrls = [];
    window.open = (...args) => {
      window.__openedUrls.push(String(args[0] || ''));
      return null;
    };
  });

  await page.route('**/api/drug-admin/provinces', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        validated_on: '2026-03-08',
        source: 'e2e-mock',
        provinces: [{ name: '国家药监局' }, { name: '上海市药监局' }],
      }),
    });
  });

  await page.route('**/api/drug-admin/resolve', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    resolveBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        code: 200,
        url: 'https://nmpa.gov.cn/province',
      }),
    });
  });

  await page.route('**/api/drug-admin/verify', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    verifyCalled += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total: 2,
        success: 1,
        failed: 1,
        rows: [
          { province: '国家药监局', ok: true, errors: [] },
          { province: '上海市药监局', ok: false, errors: ['timeout'] },
        ],
      }),
    });
  });

  await page.goto('/tools/drug-admin');

  await expect(page.getByTestId('drug-admin-page')).toBeVisible();
  await expect(page.locator('#drug-admin-province')).toHaveValue('国家药监局');

  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/drug-admin/resolve') && resp.request().method() === 'POST'),
    page.getByTestId('drug-admin-open-selected').click(),
  ]);

  expect(resolveBody).toEqual({ province: '国家药监局' });
  await expect
    .poll(() => page.evaluate(() => (window.__openedUrls || []).length), { timeout: 10_000 })
    .toBe(1);
  await expect
    .poll(() => page.evaluate(() => (window.__openedUrls || [])[0] || ''), { timeout: 10_000 })
    .toBe('https://nmpa.gov.cn/province');

  await Promise.all([
    page.waitForResponse((resp) => resp.url().includes('/api/drug-admin/verify') && resp.request().method() === 'POST'),
    page.getByTestId('drug-admin-verify-all').click(),
  ]);

  expect(verifyCalled).toBe(1);
  await expect(page.getByRole('cell', { name: '上海市药监局' })).toBeVisible();
  await expect(page.getByText('timeout')).toBeVisible();
});
