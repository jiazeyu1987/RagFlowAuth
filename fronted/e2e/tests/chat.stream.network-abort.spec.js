// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat network abort shows non-business error banner @regression @chat', async ({ page }) => {
  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats: [{ id: 'chat_1', name: 'E2E Chat' }] }) });
  });

  await page.route('**/api/chats/*/sessions', async (route) => {
    const method = route.request().method();
    if (method === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sessions: [{ id: 's_1', name: 'Session 1', messages: [] }] }) });
    }
    if (method === 'POST') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 's_1', name: 'Session 1', messages: [] }) });
    }
    return route.fallback();
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    await route.abort('failed');
  });

  await page.goto('/chat');

  await page.getByTestId('chat-input').fill('network abort test');
  await page.getByTestId('chat-send').click();

  await expect(page.getByTestId('chat-error')).toBeVisible();
  await expect(page.getByTestId('chat-error')).not.toContainText('upstream_stream_disconnected');
});
