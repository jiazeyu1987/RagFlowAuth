// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat handles SSE tail buffer without trailing newline @regression @chat', async ({ page }) => {
  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ chats: [{ id: 'chat_1', name: 'E2E Chat' }] }),
    });
  });

  await page.route('**/api/chats/*/sessions', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ sessions: [{ id: 's_1', name: 'Session 1', messages: [] }] }),
      });
    }
    return route.fallback();
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
      // Intentionally no trailing newline and no space after `data:`.
      body: 'data:{"code":0,"data":{"answer":"Tail buffer answer"}}',
    });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('chat-session-item-s_1')).toBeVisible();

  await page.getByTestId('chat-input').fill('first turn question');
  await page.getByTestId('chat-send').click();

  await expect(page.getByText('Tail buffer answer')).toBeVisible();
  await expect(page.getByTestId('chat-error')).toHaveCount(0);
});
