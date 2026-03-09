// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat stream disconnect shows error banner @regression @chat', async ({ page }) => {
  const chats = [{ id: 'chat_1', name: 'E2E Chat' }];
  const sessions = [{ id: 's_1', name: 'Session 1', messages: [] }];

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
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(sessions[0]) });
    }
    return route.fallback();
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();

    const sse =
      [
        'data: {"code":0,"data":{"answer":"partial answer"}}',
        'data: {"code":-1,"message":"upstream_stream_disconnected"}',
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

  await page.getByTestId('chat-input').fill('hello');
  await page.getByTestId('chat-send').click();

  await expect(page.getByTestId('chat-error')).toContainText('upstream_stream_disconnected');
});
