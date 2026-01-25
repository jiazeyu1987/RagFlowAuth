// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('admin can CRUD permission groups via UI @regression @admin', async ({ page }) => {
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
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, data: groups }),
      });
    }
    if (method === 'POST') {
      const body = route.request().postDataJSON();
      const created = {
        group_id: 200 + groups.length,
        is_system: 0,
        user_count: 0,
        ...body,
      };
      groups.push(created);
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, data: { group_id: created.group_id } }) });
    }
    return route.fallback();
  });

  await page.route('**/api/permission-groups/*', async (route) => {
    const url = route.request().url();
    const idStr = url.split('/api/permission-groups/')[1];
    const groupId = Number(String(idStr).split('?')[0]);
    const method = route.request().method();

    if (method === 'PUT') {
      const body = route.request().postDataJSON();
      const idx = groups.findIndex((g) => g.group_id === groupId);
      if (idx >= 0) groups[idx] = { ...groups[idx], ...body };
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }

    if (method === 'DELETE') {
      const idx = groups.findIndex((g) => g.group_id === groupId);
      if (idx >= 0) groups.splice(idx, 1);
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }

    return route.fallback();
  });

  await mockJson(page, '**/api/permission-groups/resources/knowledge-bases', { ok: true, data: [] });
  await mockJson(page, '**/api/permission-groups/resources/chats', { ok: true, data: [] });

  await page.goto('/permission-groups');

  await page.getByTestId('pg-create-open').click();
  await page.getByTestId('pg-form-group-name').fill('e2e_group');
  await page.getByTestId('pg-form-description').fill('created by e2e');
  await page.getByTestId('pg-form-can-upload').check();
  await page.getByTestId('pg-form-can-review').uncheck();
  await page.getByTestId('pg-form-can-download').check();
  await page.getByTestId('pg-form-can-delete').check();
  await page.getByTestId('pg-form-submit').click();

  await expect(page.getByText('e2e_group', { exact: true })).toBeVisible();

  const createdGroupId = groups.find((g) => g.group_name === 'e2e_group')?.group_id;
  expect(createdGroupId).toBeTruthy();

  await page.getByTestId(`pg-edit-${createdGroupId}`).click();
  await page.getByTestId('pg-form-description').fill('updated by e2e');
  await page.getByTestId('pg-form-submit').click();

  await page.getByTestId(`pg-delete-${createdGroupId}`).click();
  await page.getByTestId('pg-delete-confirm').click();

  await expect(page.getByText('e2e_group', { exact: true })).toHaveCount(0);
});
