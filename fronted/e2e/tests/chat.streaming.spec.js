// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat can create session, stream response, and delete session (mock) @regression @chat', async ({ page }) => {
  const chats = [{ id: 'chat_1', name: 'E2E Chat' }];
  let sessions = [{ id: 's_1', name: 'Session 1', messages: [] }];

  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats }) });
  });

  await page.route('**/api/chats/*/sessions', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sessions }) });
    }
    if (method === 'POST') {
      const body = route.request().postDataJSON();
      const created = { id: `s_${Date.now()}`, name: body?.name || 'New', messages: [] };
      sessions = [created, ...sessions];
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(created) });
    }
    if (method === 'DELETE') {
      const body = route.request().postDataJSON();
      const ids = Array.isArray(body?.ids) ? body.ids : [];
      sessions = sessions.filter((s) => !ids.includes(s.id));
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true }) });
    }
    return route.fallback();
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const sse =
      [
        'data: {"code":0,"data":{"answer":"Hello"}}',
        'data: {"code":0,"data":{"answer":"Hello world"}}',
        'data: {"code":0,"data":{"answer":"<think>ignore</think>!"}}',
        'data: [DONE]',
        '',
      ].join('\n') + '\n';

    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
      body: sse,
    });
  });

  await page.goto('/chat');

  await expect(page.getByTestId('chat-list')).toBeVisible();
  await expect(page.getByTestId('chat-item-chat_1')).toBeVisible();

  await expect(page.getByTestId('chat-session-item-s_1')).toBeVisible();

  await page.getByTestId('chat-session-create').click();
  await expect(page.locator('[data-testid^="chat-session-item-s_"]')).toHaveCount(2);

  await page.getByTestId('chat-input').fill('hi');
  await page.getByTestId('chat-send').click();

  await expect(page.getByTestId('chat-message-0-user')).toContainText('hi');
  await expect(page.getByTestId('chat-message-1-assistant')).toContainText('Hello world!');
  await expect(page.getByTestId('chat-error')).toHaveCount(0);

  await page.getByTestId('chat-session-delete-s_1').click();
  await expect(page.getByTestId('chat-delete-modal')).toBeVisible();
  await page.getByTestId('chat-delete-confirm').click();
  await expect(page.getByTestId('chat-session-item-s_1')).toHaveCount(0);
});

