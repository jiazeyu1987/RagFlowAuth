// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat think is incremental and not duplicated @regression @chat', async ({ page }) => {
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
    const sse =
      [
        'data: {"code":0,"data":{"answer":"<think>思考A</think>"}}',
        'data: {"code":0,"data":{"answer":"<think>思考A\\n思考B</think>最终答案"}}',
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
  await page.getByTestId('chat-input').fill('测试 think');
  await page.getByTestId('chat-send').click();

  const assistant = page.getByTestId('chat-message-1-assistant');
  await expect(assistant).toContainText('最终答案');
  await expect(assistant).toContainText('思考A');
  await expect(assistant).toContainText('思考B');

  const fullText = await assistant.innerText();
  const countA = (fullText.match(/思考A/g) || []).length;
  const countB = (fullText.match(/思考B/g) || []).length;
  expect(countA).toBe(1);
  expect(countB).toBe(1);
});

