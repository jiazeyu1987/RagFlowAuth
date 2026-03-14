// @ts-check
const { expect } = require('@playwright/test');
const { adminTest } = require('../helpers/auth');

adminTest('chat safety flow visualization renders backend safety stages @regression @chat', async ({ page }) => {
  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ chats: [{ id: 'chat_1', name: '安全演示助手' }] }),
    });
  });

  await page.route('**/api/chats/*/sessions', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ sessions: [{ id: 's_1', name: '会话 1', messages: [] }] }),
    });
  });

  await page.route('**/api/chats/*/completions', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const sse =
      [
        'data: {"code":0,"data":{"security":{"security_stage":"classify","security_status":"success","summary":"敏感分级完成","detail":"命中 1 条规则，分级结果：中敏"}}}',
        'data: {"code":0,"data":{"security":{"security_stage":"desensitize","security_status":"success","summary":"脱敏处理完成","detail":"已完成自动脱敏，命中 1 条规则"}}}',
        'data: {"code":0,"data":{"security":{"security_stage":"intercept","security_status":"running","summary":"正在执行拦截检查...","detail":"正在进行策略比对与放行判定"}}}',
        'data: {"code":0,"data":{"security":{"security_stage":"intercept","security_status":"success","summary":"安全流程完成，已放行回复","detail":"通过拦截检查，允许继续生成回答","done":true}}}',
        'data: {"code":0,"data":{"answer":"这是通过安全流程后的回复"}}',
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
  await expect(page.getByTestId('chat-session-item-s_1')).toBeVisible();

  await page.getByTestId('chat-input').fill('请演示安全流程');
  await page.getByTestId('chat-send').click();

  await expect(page.getByText('这是通过安全流程后的回复')).toBeVisible();
  await expect(page.getByTestId('chat-safety-flow-1')).toBeVisible();
  await expect(page.getByTestId('chat-safety-flow-1')).toContainText('分级');
  await expect(page.getByTestId('chat-safety-flow-1')).toContainText('脱敏');
  await expect(page.getByTestId('chat-safety-flow-1')).toContainText('拦截');
  await expect(page.getByTestId('chat-safety-flow-1')).toContainText('安全流程完成，已放行回复');
});

