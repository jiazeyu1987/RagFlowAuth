// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('logout clears local auth and navigates to /login @regression @auth', async ({ page }) => {
  let logoutCalls = 0;

  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'refresh disabled in logout test' }) });
  });

  await page.route('**/api/auth/logout', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    logoutCalls += 1;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.goto('/');
  await expect(page.getByTestId('layout-sidebar')).toBeVisible();

  await Promise.all([
    page.waitForResponse((r) => r.url().includes('/api/auth/logout') && r.request().method() === 'POST'),
    page.getByTestId('layout-logout').click(),
  ]);

  await page.waitForURL(/\/login$/, { timeout: 30_000 });
  await expect(page.getByTestId('login-submit')).toBeVisible();

  expect(logoutCalls).toBe(1);

  const authState = await page.evaluate(() => ({
    accessToken: localStorage.getItem('accessToken'),
    refreshToken: localStorage.getItem('refreshToken'),
    legacyAuthToken: localStorage.getItem('authToken'),
    user: localStorage.getItem('user'),
  }));
  expect(authState.accessToken).toBeNull();
  expect(authState.refreshToken).toBeNull();
  expect(authState.legacyAuthToken).toBeNull();
  expect(authState.user).toBeNull();
});
