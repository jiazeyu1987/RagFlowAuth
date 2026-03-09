// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat stream renders when answer arrives as data.content @regression @chat', async ({ page }) => {
  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ chats: [{ id: 'chat_1', name: 'E2E Chat' }] }),
    });
  });

  await page.route('**/api/chats/*/sessions', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ sessions: [{ id: 's_1', name: 'Session 1', messages: [] }] }),
    });
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const sse = ['data: {"code":0,"data":{"content":"content-field answer"}}', 'data: [DONE]', ''].join('\n') + '\n';
    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
      body: sse,
    });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('chat-session-item-s_1')).toBeVisible();
  await page.getByTestId('chat-input').fill('question');
  await page.getByTestId('chat-send').click();

  await expect(page.getByText('content-field answer')).toBeVisible();
  await expect(page.getByTestId('chat-error')).toHaveCount(0);
});
