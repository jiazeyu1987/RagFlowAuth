// @ts-check
const { test, expect } = require('@playwright/test');

test('refresh token failure redirects to /login and clears auth @regression @auth', async ({ page }) => {
  // Keep app version in sync with AuthProvider.APP_VERSION to avoid auto-clear before exercising refresh flow.
  await page.addInitScript(() => {
    localStorage.setItem('appVersion', '6');
    localStorage.setItem('accessToken', 'e2e_expired_access');
    localStorage.setItem('refreshToken', 'e2e_invalid_refresh');
    localStorage.setItem('user', JSON.stringify({ user_id: 'e2e_user', username: 'e2e_user', role: 'admin' }));
  });

  let refreshCalls = 0;

  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Unauthorized' }) });
  });

  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    refreshCalls += 1;
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Token refresh failed' }) });
  });

  await page.goto('/');
  await page.waitForURL(/\/login$/, { timeout: 30_000 });
  await expect(page.getByTestId('login-submit')).toBeVisible();

  expect(refreshCalls).toBeGreaterThan(0);

  const authState = await page.evaluate(() => ({
    accessToken: localStorage.getItem('accessToken'),
    refreshToken: localStorage.getItem('refreshToken'),
    user: localStorage.getItem('user'),
  }));
  expect(authState.accessToken).toBeNull();
  expect(authState.refreshToken).toBeNull();
  expect(authState.user).toBeNull();
});

