// @ts-check
const { test, expect } = require('@playwright/test');
const { adminStorageStatePath } = require('../helpers/auth');

test.use({ storageState: adminStorageStatePath });

test('chat shows sources/chunk and hides download when no permission @regression @chat @rbac', async ({ page }) => {
  await page.route('**/api/auth/me', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'u_viewer_no_dl',
        username: 'viewer_no_dl',
        role: 'viewer',
        status: 'active',
        permissions: { can_upload: false, can_review: false, can_download: false, can_delete: false },
      }),
    });
  });
  await page.route('**/api/me/kbs', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ kb_ids: ['ds1'] }) });
  });
  await page.route('**/api/auth/refresh', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'e2e_access_token', token_type: 'bearer' }) });
  });

  await page.route('**/api/chats/my', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ chats: [{ id: 'chat_1', name: 'E2E Chat' }] }) });
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
    const sse = [
      'data: {"code":0,"data":{"answer":"Result [ID:0]","sources":[{"dataset":"kb-one","doc_id":"doc1","title":"demo.md","chunk":"# 标题\\n- 条目"}]}}',
      'data: [DONE]',
      '',
    ].join('\n') + '\n';
    return route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream; charset=utf-8' },
      body: sse,
    });
  });

  await page.route('**/api/preview/documents/ragflow/doc1/preview?*', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ type: 'text', filename: 'demo.md', content: '# 标题\n- 条目' }),
    });
  });

  await page.goto('/chat');
  await page.getByTestId('chat-input').fill('测试引用');
  await page.getByTestId('chat-send').click();

  const assistant = page.getByTestId('chat-message-1-assistant');
  await expect(assistant).toContainText('Result');
  await expect(assistant).toContainText('demo.md');
  await expect(page.getByTestId('chat-source-view-0')).toBeVisible();
  await expect(assistant.getByRole('button', { name: /下载/ })).toHaveCount(0);

  await page.getByTestId('chat-source-view-0').click();
  const modal = page.getByTestId('document-preview-modal');
  await expect(modal).toBeVisible();
  await expect(modal.locator('h1')).toContainText('标题');
  await page.keyboard.press('Escape');

  const citationBadge = assistant.locator('span[title]').first();
  await citationBadge.click();
  await expect(page.getByTestId('chat-citation-tooltip')).toContainText('标题');
});
