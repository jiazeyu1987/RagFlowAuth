// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

test('chat can create and delete session (real backend) @integration', async ({ page }) => {
  test.setTimeout(120_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  let chatId = null;

  try {
    const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
    const chatsResp = await api.get('/api/chats/my', { headers });
    if (!chatsResp.ok()) test.skip(true, 'GET /api/chats/my failed; chat may be unavailable');
    const payload = await chatsResp.json();
    const chats = payload?.chats || [];
    if (!Array.isArray(chats) || chats.length === 0) test.skip(true, 'no chats available for this user');
    chatId = chats[0].id;
    if (!chatId) test.skip(true, 'first chat missing id');
  } finally {
    await api.dispose();
  }

  await uiLogin(page);
  await expect(page).toHaveURL(/\/$/);

  await page.goto(`${FRONTEND_BASE_URL}/chat`);
  await expect(page.getByTestId('chat-list')).toBeVisible({ timeout: 30_000 });

  await page.getByTestId(`chat-item-${chatId}`).click();

  const [createResp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes(`/api/chats/${chatId}/sessions`) && r.request().method() === 'POST'),
    page.getByTestId('chat-session-create').click(),
  ]);

  const created = await createResp.json();
  const sessionId = created?.id;
  if (!sessionId) test.fail(true, 'create session did not return id');

  await expect(page.getByTestId(`chat-session-item-${sessionId}`)).toBeVisible({ timeout: 30_000 });

  await page.getByTestId(`chat-session-item-${sessionId}`).click();
  await page.getByTestId(`chat-session-delete-${sessionId}`).click();
  await expect(page.getByTestId('chat-delete-modal')).toBeVisible();

  await Promise.all([
    page.waitForResponse((r) => r.url().includes(`/api/chats/${chatId}/sessions`) && r.request().method() === 'DELETE'),
    page.getByTestId('chat-delete-confirm').click(),
  ]);

  await expect(page.getByTestId(`chat-session-item-${sessionId}`)).toHaveCount(0);
});
