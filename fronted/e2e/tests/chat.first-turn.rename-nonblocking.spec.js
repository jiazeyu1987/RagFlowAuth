// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat first turn is not blocked by slow auto-rename @regression @chat', async ({ page }) => {
  let renameCalls = 0;
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
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        sessions: [{ id: 's_1', name: 'new chat', messages: [] }],
      }),
    });
  });

  await page.route('**/api/chats/*/sessions/*', async (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    renameCalls += 1;
    await new Promise((resolve) => setTimeout(resolve, 3000));
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    completionCalls += 1;
    const sse = ['data: {"code":0,"data":{"answer":"First turn answer"}}', 'data: [DONE]', ''].join('\n') + '\n';
    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
      body: sse,
    });
  });

  await page.goto('/chat');
  await expect(page.getByTestId('chat-session-item-s_1')).toBeVisible();

  await page.getByTestId('chat-input').fill('first turn question');
  await page.getByTestId('chat-send').click();

  await expect.poll(() => completionCalls, { timeout: 1500 }).toBe(1);
  await expect(page.getByText('First turn answer')).toBeVisible();
  await expect.poll(() => renameCalls, { timeout: 5000 }).toBe(1);
  await expect(page.getByTestId('chat-error')).toHaveCount(0);
});
