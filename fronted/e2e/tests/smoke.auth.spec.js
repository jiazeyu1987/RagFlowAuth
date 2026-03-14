// @ts-check
const { test, expect } = require('@playwright/test');

test('login rejects wrong password @smoke', async ({ page }) => {
  await page.route('**/api/auth/login', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'invalid_credentials' }),
    });
  });

  await page.goto('/login');

  await page.getByTestId('login-username').fill('admin');
  await page.getByTestId('login-password').fill('wrong-password');
  await page.getByTestId('login-submit').click();

  await expect(page.getByTestId('login-error')).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});

test('login works via UI @smoke', async ({ page }) => {
  await page.route('**/api/auth/login', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'e2e_access_token',
        refresh_token: 'e2e_refresh_token',
        token_type: 'bearer',
      }),
    });
  });

  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_admin',
        username: 'admin',
        role: 'admin',
        status: 'active',
        permissions: {
          can_upload: true,
          can_review: true,
          can_download: true,
          can_delete: true,
        },
      }),
    });
  });

  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: ['ds1'] }) });
  });

  await page.goto('/login');

  await page.getByTestId('login-username').fill(process.env.E2E_ADMIN_USER || 'admin');
  await page.getByTestId('login-password').fill(process.env.E2E_ADMIN_PASS || 'admin123');
  await page.getByTestId('login-submit').click();

  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByTestId('layout-sidebar')).toBeVisible();
});
