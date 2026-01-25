// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('permission groups handles resources API failures gracefully @regression @admin', async ({ page }) => {
  const groups = [
    {
      group_id: 1,
      group_name: 'admin',
      description: 'system admin',
      accessible_kbs: [],
      accessible_chats: [],
      can_upload: true,
      can_review: true,
      can_download: true,
      can_delete: true,
      is_system: 1,
      user_count: 1,
    },
  ];

  await page.route('**/api/permission-groups', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, data: groups }) });
  });

  await page.route('**/api/permission-groups/resources/knowledge-bases', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'kb service down' }) });
  });
  await page.route('**/api/permission-groups/resources/chats', async (route) => {
    await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'chat service down' }) });
  });

  await page.goto('/permission-groups');

  await page.getByTestId('pg-create-open').click();
  await expect(page.getByTestId('pg-modal')).toBeVisible();
  await expect(page.getByTestId('pg-form-kb-empty')).toBeVisible();
  await expect(page.getByTestId('pg-form-chat-empty')).toBeVisible();
  await page.getByTestId('pg-form-cancel').click();
});

