// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat configs: locked branch supports save-name-only and clear parsed files @regression @kbs @chat-configs', async ({ page }) => {
  const chats = [{ id: 'chat_1', name: 'Chat One' }];
  const chatDetail = { id: 'chat_1', name: 'Chat One', dataset_ids: ['ds1'] };
  const updateBodies = [];
  let clearCalls = 0;

  await page.route('**/api/chats?page_size=1000**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats }) });
  });

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ datasets: [{ id: 'ds1', name: 'KB 1' }, { id: 'ds2', name: 'KB 2' }] }),
    });
  });

  await page.route('**/api/chats/chat_1/clear-parsed-files', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    clearCalls += 1;
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
  });

  await page.route('**/api/chats/chat_1', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chat: chatDetail }) });
    }
    if (method === 'PUT') {
      const body = route.request().postDataJSON();
      updateBodies.push(body);
      if (Array.isArray(body?.dataset_ids)) {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: "chat_dataset_locked: doesn't own parsed file" }),
        });
      }
      chatDetail.name = String(body?.name || chatDetail.name);
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chat: chatDetail }) });
    }
    return route.fallback();
  });

  await page.goto('/chat-configs');
  await expect(page.getByTestId('chat-configs-page')).toBeVisible();
  await page.getByTestId('chat-config-item-chat_1').click();

  await page.getByTestId('chat-config-name').fill('Chat One Renamed');
  await page.getByTestId('chat-config-save').click();
  await expect(page.getByTestId('chat-config-detail-error')).toContainText('已关联已解析文档');
  await expect(page.getByTestId('chat-config-save-name-only')).toBeVisible();

  page.once('dialog', async (dialog) => dialog.accept());
  await page.getByTestId('chat-config-clear-parsed').click();
  await expect.poll(() => clearCalls).toBe(1);

  await page.getByTestId('chat-config-save').click();
  await expect(page.getByTestId('chat-config-detail-error')).toContainText('已关联已解析文档');
  await page.getByTestId('chat-config-name').fill('Chat One Renamed');
  await page.getByTestId('chat-config-save-name-only').click();
  expect(updateBodies.length).toBeGreaterThanOrEqual(2);
  expect(updateBodies.at(-1)).toEqual({ name: 'Chat One Renamed' });
});

adminTest('chat configs: copy and delete failure branches show errors @regression @kbs @chat-configs', async ({ page }) => {
  const chats = [{ id: 'chat_1', name: 'Chat One' }];
  const chatDetail = { id: 'chat_1', name: 'Chat One', dataset_ids: ['ds1'] };

  await page.route('**/api/chats?page_size=1000**', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats }) });
  });

  await page.route('**/api/datasets', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ datasets: [{ id: 'ds1', name: 'KB 1' }] }) });
  });

  await page.route('**/api/chats/chat_1', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chat: chatDetail }) });
    }
    if (method === 'PUT') {
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: "chat_dataset_locked: doesn't own parsed file" }),
      });
    }
    if (method === 'DELETE') {
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'delete_chat_failed_test' }),
      });
    }
    return route.fallback();
  });

  await page.route('**/api/chats', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'copy_chat_failed_test' }),
    });
  });

  await page.goto('/chat-configs');
  await expect(page.getByTestId('chat-configs-page')).toBeVisible();
  await page.getByTestId('chat-config-item-chat_1').click();

  await page.getByTestId('chat-config-save').click();
  await expect(page.getByTestId('chat-config-detail-error')).toContainText('已关联已解析文档');
  await expect(page.getByTestId('chat-config-copy-new')).toBeVisible();

  await page.getByTestId('chat-config-copy-new').click();
  await expect(page.getByTestId('chat-config-detail-error')).toContainText('copy_chat_failed_test');

  page.once('dialog', async (dialog) => dialog.accept());
  await page.getByTestId('chat-config-delete-chat_1').click();
  await expect(page.getByTestId('chat-config-list-error')).toContainText('delete_chat_failed_test');
});
