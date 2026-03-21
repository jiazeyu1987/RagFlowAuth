// @ts-check
const { expect } = require('@playwright/test');
const { viewerTest } = require('../helpers/auth');

viewerTest('viewer without kbs/tools view permissions cannot see menu or access routes @regression @rbac', async ({ page }) => {
  await page.unroute('**/api/auth/me');
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_viewer_blocked',
        username: 'viewer_blocked',
        role: 'viewer',
        status: 'active',
        permissions: {
          can_upload: false,
          can_review: false,
          can_download: true,
          can_delete: false,
          can_manage_kb_directory: false,
          can_view_kb_config: false,
          can_view_tools: false,
        },
        accessible_kbs: [],
        accessible_kb_ids: [],
        accessible_chats: [],
      }),
    });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('nav-kbs')).toHaveCount(0);
  await expect(page.getByTestId('nav-tools')).toHaveCount(0);

  await page.goto('/kbs');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();

  await page.goto('/tools');
  await expect(page).toHaveURL(/\/unauthorized$/);
  await expect(page.getByTestId('unauthorized-title')).toBeVisible();
});

viewerTest('viewer with kbs/tools view permissions can access routes @regression @rbac', async ({ page }) => {
  await page.unroute('**/api/auth/me');
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_viewer_allowed',
        username: 'viewer_allowed',
        role: 'viewer',
        status: 'active',
        permissions: {
          can_upload: false,
          can_review: false,
          can_download: true,
          can_delete: false,
          can_manage_kb_directory: false,
          can_view_kb_config: true,
          can_view_tools: true,
        },
        accessible_kbs: [],
        accessible_kb_ids: [],
        accessible_chats: [],
      }),
    });
  });

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [] }) });
  });
  await page.route('**/api/knowledge/directories', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ nodes: [], datasets: [] }) });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('nav-kbs')).toBeVisible();
  await expect(page.getByTestId('nav-tools')).toBeVisible();

  await page.goto('/kbs');
  await expect(page).toHaveURL(/\/kbs$/);
  await expect(page.getByTestId('kbs-subtab-kbs')).toBeVisible();

  await page.goto('/tools');
  await expect(page).toHaveURL(/\/tools$/);
  await expect(page.getByTestId('layout-header-title')).toHaveText('实用工具');
});
