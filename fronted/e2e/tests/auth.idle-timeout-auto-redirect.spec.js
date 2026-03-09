// @ts-check
const { test, expect } = require('@playwright/test');

test('idle timeout auto-redirects to /login without API activity @regression @auth', async ({ page }) => {
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
        idle_timeout_minutes: 0.02,
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
        idle_timeout_minutes: 0.02,
        permissions: { can_upload: true, can_review: true, can_download: true, can_delete: true },
      }),
    });
  });

  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: [] }) });
  });

  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats: [] }) });
  });

  await page.goto('/chat');
  await page.waitForURL(/\/chat$/, { timeout: 30_000 });
  await expect(page.getByTestId('chat-page')).toBeVisible();

  await page.waitForURL(/\/login$/, { timeout: 15_000 });
  await expect(page.getByTestId('login-submit')).toBeVisible();
});
