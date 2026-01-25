// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');
const { mockJson } = require('../helpers/mock');

adminTest('permission groups can select knowledge bases and chats @regression @admin', async ({ page }) => {
  const kbList = [
    { id: 'kb_1', name: 'KB One' },
    { id: 'kb_2', name: 'KB Two' },
  ];
  const chatList = [
    { id: 'chat_1', name: 'Chat One', type: 'chat' },
    { id: 'agent_1', name: 'Agent One', type: 'agent' },
  ];

  const groups = [
    {
      group_id: 1,
      group_name: 'admin',
      description: 'system admin',
      accessible_kbs: ['kb_1'],
      accessible_chats: ['agent_1'],
      can_upload: true,
      can_review: true,
      can_download: true,
      can_delete: true,
      is_system: 1,
      user_count: 1,
    },
  ];

  let capturedCreateBody = null;

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
      capturedCreateBody = body;
      const created = {
        group_id: 200 + groups.length,
        is_system: 0,
        user_count: 0,
        ...body,
      };
      groups.push(created);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, data: { group_id: created.group_id } }),
      });
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

    return route.fallback();
  });

  await mockJson(page, '**/api/permission-groups/resources/knowledge-bases', { ok: true, data: kbList });
  await mockJson(page, '**/api/permission-groups/resources/chats', { ok: true, data: chatList });

  await page.goto('/permission-groups');

  // Edit existing: should preselect current resources.
  await page.getByTestId('pg-edit-1').click();
  await expect(page.getByTestId('pg-modal')).toBeVisible();
  await expect(page.getByTestId('pg-form-kb-kb_1')).toBeChecked();
  await expect(page.getByTestId('pg-form-chat-agent_1')).toBeChecked();
  await page.getByTestId('pg-form-cancel').click();

  // Create: select resources and ensure POST payload contains them.
  await page.getByTestId('pg-create-open').click();
  await page.getByTestId('pg-form-group-name').fill('e2e_group_resources');
  await page.getByTestId('pg-form-kb-kb_2').check();
  await page.getByTestId('pg-form-chat-chat_1').check();
  await page.getByTestId('pg-form-submit').click();

  expect(capturedCreateBody).toBeTruthy();
  expect(capturedCreateBody.accessible_kbs).toEqual(['kb_2']);
  expect(capturedCreateBody.accessible_chats).toEqual(['chat_1']);
});
