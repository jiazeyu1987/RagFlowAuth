// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat can recover after non-business stream failure and continue conversation @regression @chat', async ({ page }) => {
  let completionCalls = 0;

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
        body: JSON.stringify({
          sessions: [
            {
              id: 's_1',
              name: 'Session 1',
              messages: [
                { role: 'user', content: 'seed context question' },
                { role: 'assistant', content: 'seed context answer' },
              ],
            },
          ],
        }),
      });
    }
    if (method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 's_1', name: 'Session 1', messages: [] }),
      });
    }
    return route.fallback();
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    completionCalls += 1;

    if (completionCalls === 1) {
      return route.abort('failed');
    }

    const sse = ['data: {"code":0,"data":{"answer":"Recovered answer"}}', 'data: [DONE]', ''].join('\n') + '\n';
    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
      body: sse,
    });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('chat-item-chat_1')).toBeVisible();
  await expect(page.getByTestId('chat-session-item-s_1')).toBeVisible();
  await expect(page.getByText('seed context answer')).toBeVisible();

  await page.getByTestId('chat-input').fill('first turn question');
  await expect(page.getByTestId('chat-send')).toBeEnabled();
  await page.getByTestId('chat-send').click();

  await expect.poll(() => completionCalls).toBe(1);
  await expect(page.getByTestId('chat-error')).toBeVisible();
  await expect(page.getByText('seed context answer')).toBeVisible();

  await page.getByTestId('chat-input').fill('second turn question');
  await expect(page.getByTestId('chat-send')).toBeEnabled();
  await page.getByTestId('chat-send').click();

  await expect.poll(() => completionCalls).toBe(2);
  await expect(page.getByTestId('chat-input')).toHaveValue('');
  await expect(page.getByText('seed context answer')).toBeVisible();
  await expect(page.getByTestId('chat-error')).toHaveCount(0);
});
