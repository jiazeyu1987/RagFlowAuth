// @ts-check
const { test, expect } = require('@playwright/test');

test('session timeout on business API redirects to /login and clears auth @regression @auth', async ({ page }) => {
  await page.addInitScript(() => {
    if (String(window.location?.pathname || '') === '/login') return;
    localStorage.setItem('appVersion', '6');
    localStorage.setItem('accessToken', 'e2e_access_token');
    localStorage.setItem('refreshToken', 'e2e_refresh_token');
    localStorage.setItem(
      'user',
      JSON.stringify({
        user_id: 'e2e_admin',
        username: 'admin',
        role: 'admin',
        permissions: { can_upload: true, can_review: true, can_download: true, can_delete: true },
      })
    );
  });

  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'e2e_admin',
        username: 'admin',
        role: 'admin',
        permissions: { can_upload: true, can_review: true, can_download: true, can_delete: true },
      }),
    });
  });

  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: [] }) });
  });

  let chatsMyCalls = 0;
  let expired = false;
  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    chatsMyCalls += 1;
    if (!expired) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats: [] }) });
      return;
    }
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'session_invalid:expired' }) });
  });

  let refreshCalls = 0;
  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    refreshCalls += 1;
    if (!expired) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'e2e_access_token_after_refresh', token_type: 'bearer' }),
      });
      return;
    }
    await route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Token refresh failed' }) });
  });

  await page.goto('/chat');
  await page.waitForURL(/\/chat$/, { timeout: 30_000 });
  await expect(page.getByTestId('chat-page')).toBeVisible();
  expect(chatsMyCalls).toBeGreaterThanOrEqual(1);

  expired = true;
  await page.reload().catch(() => {});
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
