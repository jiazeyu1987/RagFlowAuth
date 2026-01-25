// @ts-check
const path = require('node:path');
const { test: base } = require('@playwright/test');

const authDir = path.resolve(__dirname, '..', '.auth');

const adminStorageStatePath = path.join(authDir, 'admin.json');
const viewerStorageStatePath = path.join(authDir, 'viewer.json');

const ADMIN_USER = {
  user_id: 'e2e_admin',
  username: 'admin',
  email: 'admin@example.com',
  role: 'admin',
  status: 'active',
  group_id: 1,
  group_ids: [1],
  permission_groups: [{ group_id: 1, group_name: 'admin' }],
  scopes: [],
  permissions: { can_upload: true, can_review: true, can_download: true, can_delete: true },
  accessible_kbs: [],
  accessible_kb_ids: [],
  accessible_chats: [],
};

const VIEWER_USER = {
  user_id: 'e2e_viewer',
  username: 'viewer',
  email: null,
  role: 'viewer',
  status: 'active',
  group_id: 2,
  group_ids: [2],
  permission_groups: [{ group_id: 2, group_name: 'viewer' }],
  scopes: [],
  permissions: { can_upload: false, can_review: false, can_download: true, can_delete: false },
  accessible_kbs: [],
  accessible_kb_ids: [],
  accessible_chats: [],
};

async function stabilizeAuthRoutes(page, user) {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) });
  });

  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: [] }) });
  });

  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: 'e2e_access_token', token_type: 'bearer' }),
    });
  });
}

const adminTest = base.extend({
  context: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: adminStorageStatePath });
    await use(context);
    await context.close();
  },
  page: async ({ context }, use) => {
    const page = await context.newPage();
    await stabilizeAuthRoutes(page, ADMIN_USER);
    await use(page);
    await page.close();
  },
});

const viewerTest = base.extend({
  context: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: viewerStorageStatePath });
    await use(context);
    await context.close();
  },
  page: async ({ context }, use) => {
    const page = await context.newPage();
    await stabilizeAuthRoutes(page, VIEWER_USER);
    await use(page);
    await page.close();
  },
});

module.exports = {
  adminStorageStatePath,
  viewerStorageStatePath,
  adminTest,
  viewerTest,
};
