// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat auto-refreshes current session when stream has no renderable answer @regression @chat', async ({ page }) => {
  let sessionsGetCount = 0;

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
    sessionsGetCount += 1;
    const sessions =
      sessionsGetCount === 1
        ? [{ id: 's_1', name: 'Session 1', messages: [] }]
        : [
            {
              id: 's_1',
              name: 'Session 1',
              messages: [
                { role: 'user', content: 'question' },
                { role: 'assistant', content: 'refreshed from session api' },
              ],
            },
          ];
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ sessions }),
    });
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const sse = ['data: [DONE]', ''].join('\n') + '\n';
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

  await expect.poll(() => sessionsGetCount).toBeGreaterThan(1);
  await expect(page.getByText('refreshed from session api')).toBeVisible();
});
