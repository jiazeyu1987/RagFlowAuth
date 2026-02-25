// @ts-check
const { test, expect } = require('@playwright/test');
const { adminStorageStatePath } = require('../helpers/auth');

test.use({ storageState: adminStorageStatePath });

test('uploader can upload but cannot access admin management routes @regression @rbac', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_uploader',
        username: 'uploader',
        role: 'viewer',
        status: 'active',
        permission_groups: [{ group_id: 11, group_name: 'uploader' }],
        permissions: { can_upload: true, can_review: false, can_download: false, can_delete: false },
      }),
    });
  });
  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: ['ds1'] }) });
  });
  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'e2e_access_token', token_type: 'bearer' }) });
  });
  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: 'kb-one' }] }),
    });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('chat-page')).toBeVisible();
  await expect(page.getByTestId('nav-upload')).toBeVisible();
  await expect(page.getByTestId('nav-documents')).toHaveCount(0);
  await expect(page.getByTestId('nav-users')).toHaveCount(0);
  await expect(page.getByTestId('nav-permission-groups')).toHaveCount(0);
  await expect(page.getByTestId('nav-org-directory')).toHaveCount(0);

  await page.goto('/upload');
  await expect(page.getByTestId('upload-submit')).toBeVisible();

  await page.goto('/users');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();

  await page.goto('/permission-groups');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});

