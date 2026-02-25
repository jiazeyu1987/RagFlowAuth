// @ts-check
const { test, expect } = require('@playwright/test');
const { adminStorageStatePath } = require('../helpers/auth');

test.use({ storageState: adminStorageStatePath });

test('reviewer can review docs but cannot access admin management routes @regression @rbac', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_reviewer',
        username: 'reviewer',
        role: 'viewer',
        status: 'active',
        permission_groups: [{ group_id: 12, group_name: 'reviewer' }],
        permissions: { can_upload: false, can_review: true, can_download: true, can_delete: false },
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
  await page.route('**/api/knowledge/documents?status=pending*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [], count: 0 }) });
  });
  await page.route('**/api/knowledge/documents?status=approved*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ documents: [], count: 0 }) });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('chat-page')).toBeVisible();
  await expect(page.getByTestId('nav-documents')).toBeVisible();
  await expect(page.getByTestId('nav-upload')).toHaveCount(0);
  await expect(page.getByTestId('nav-users')).toHaveCount(0);
  await expect(page.getByTestId('nav-permission-groups')).toHaveCount(0);
  await expect(page.getByTestId('nav-org-directory')).toHaveCount(0);

  await page.goto('/documents');
  await expect(page.getByTestId('documents-page')).toBeVisible();
  await expect(page.getByTestId('documents-tab-approve')).toBeVisible();

  await page.goto('/users');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();

  await page.goto('/permission-groups');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});

