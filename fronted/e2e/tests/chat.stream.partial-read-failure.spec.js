// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat recovers after partial-token stream read failure @regression @chat', async ({ page }) => {
  await page.addInitScript(() => {
    const originalFetch = window.fetch.bind(window);
    const encoder = new TextEncoder();
    window.__completionCalls = 0;

    window.fetch = async (input, init) => {
      const url = typeof input === 'string' ? input : String(input?.url || '');
      const method = String(init?.method || (typeof input !== 'string' ? input?.method : '') || 'GET').toUpperCase();

      if (url.includes('/api/chats/chat_1/completions') && method === 'POST') {
        window.__completionCalls += 1;

        if (window.__completionCalls === 1) {
          let step = 0;
          const stream = new ReadableStream({
            async pull(controller) {
              if (step === 0) {
                step = 1;
                controller.enqueue(encoder.encode('data: {"code":0,"data":{"answer":"partial token"}}\n'));
                return;
              }
              controller.error(new Error('reader_failed_mid_stream'));
            },
          });
          return new Response(stream, {
            status: 200,
            headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
          });
        }

        const okSse = ['data: {"code":0,"data":{"answer":"Recovered answer"}}', 'data: [DONE]', ''].join('\n') + '\n';
        return new Response(okSse, {
          status: 200,
          headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
        });
      }

      return originalFetch(input, init);
    };
  });

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

  await page.goto('/chat');
  await expect(page.getByTestId('chat-session-item-s_1')).toBeVisible();
  await expect(page.getByText('seed context answer')).toBeVisible();

  await page.getByTestId('chat-input').fill('first turn question');
  await page.getByTestId('chat-send').click();
  await expect.poll(() => page.evaluate(() => window.__completionCalls)).toBe(1);
  await expect(page.getByTestId('chat-error')).toBeVisible();

  await page.getByTestId('chat-input').fill('second turn question');
  await page.getByTestId('chat-send').click();
  await expect.poll(() => page.evaluate(() => window.__completionCalls)).toBe(2);
  await expect(page.getByText('Recovered answer')).toBeVisible();
  await expect(page.getByTestId('chat-error')).toHaveCount(0);
});
