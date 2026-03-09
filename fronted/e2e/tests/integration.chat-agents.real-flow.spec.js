// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');

const TARGET_CHAT_NAME = '\u5c55\u5385\u804a\u5929';
const CHAT_QUESTION = '\u4ecb\u7ecd\u4e00\u4e0b\u5bfc\u4e1d';
const SEARCH_QUERY = '\u5bfc\u4e1d';
const STRICT_REAL_FLOW = String(process.env.E2E_REQUIRE_REAL_FLOW || '') === '1';

function normalizeChatName(rawName) {
  return String(rawName || '')
    .trim()
    .replace(/^\[+|\]+$/g, '')
    .trim();
}

test('real flow: smart chat and global search are both available @integration @chat @agents @realdata', async ({ page }) => {
  test.setTimeout(300_000);

  const pre = await preflightAdmin();
  if (!pre.ok) {
    if (STRICT_REAL_FLOW) throw new Error(pre.reason);
    test.skip(true, pre.reason);
  }

  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });

  let targetChatId = null;
  let createdSessionId = null;

  try {
    const chatsResp = await api.get('/api/chats/my', { headers });
    expect(chatsResp.ok(), 'GET /api/chats/my failed').toBeTruthy();
    const chatsPayload = await chatsResp.json();
    const chats = Array.isArray(chatsPayload?.chats) ? chatsPayload.chats : [];

    const targetChat = chats.find((chat) => normalizeChatName(chat?.name) === TARGET_CHAT_NAME);
    expect(targetChat, `chat not found: ${TARGET_CHAT_NAME}`).toBeTruthy();
    targetChatId = targetChat?.id ? String(targetChat.id) : null;
    expect(targetChatId, 'target chat id missing').toBeTruthy();

    const datasetsResp = await api.get('/api/datasets', { headers });
    expect(datasetsResp.ok(), 'GET /api/datasets failed').toBeTruthy();
    const datasetsPayload = await datasetsResp.json();
    const datasets = Array.isArray(datasetsPayload?.datasets) ? datasetsPayload.datasets : [];
    expect(datasets.length, 'no dataset available for global search').toBeGreaterThan(0);

    const datasetIds = datasets.map((item) => item?.id).filter(Boolean);
    const preSearchResp = await api.post('/api/search', {
      headers,
      data: {
        question: SEARCH_QUERY,
        dataset_ids: datasetIds,
        page: 1,
        page_size: 30,
        similarity_threshold: 0.2,
        top_k: 30,
        keyword: false,
        highlight: false,
      },
    });
    expect(preSearchResp.ok(), 'precheck /api/search failed').toBeTruthy();
    const preSearchPayload = await preSearchResp.json();
    const preSearchChunks = Array.isArray(preSearchPayload?.chunks) ? preSearchPayload.chunks : [];
    expect(preSearchChunks.length, `precheck "${SEARCH_QUERY}" returned no chunks`).toBeGreaterThan(0);

    await uiLogin(page);
    await expect(page).toHaveURL(/\/chat$/);

    await page.goto(`${FRONTEND_BASE_URL}/chat`);
    await expect(page.getByTestId('chat-page')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId(`chat-item-${targetChatId}`)).toBeVisible({ timeout: 30_000 });
    await page.getByTestId(`chat-item-${targetChatId}`).click();

    const [createSessionResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes(`/api/chats/${targetChatId}/sessions`) && resp.request().method() === 'POST'
      ),
      page.getByTestId('chat-session-create').click(),
    ]);
    expect(createSessionResp.ok(), 'create chat session failed').toBeTruthy();
    const createdSession = await createSessionResp.json();
    createdSessionId = createdSession?.id ? String(createdSession.id) : null;
    expect(createdSessionId, 'created session id missing').toBeTruthy();
    await expect(page.getByTestId(`chat-session-item-${createdSessionId}`)).toBeVisible({ timeout: 30_000 });

    await page.getByTestId('chat-input').fill(CHAT_QUESTION);
    const assistantMessages = page.getByTestId('chat-messages').locator("[data-testid$='-assistant']");
    const assistantBeforeCount = await assistantMessages.count();

    const completionRequestPromise = page.waitForRequest(
      (req) => req.url().includes(`/api/chats/${targetChatId}/completions`) && req.method() === 'POST'
    );
    const completionResponsePromise = page.waitForResponse(
      (resp) => resp.url().includes(`/api/chats/${targetChatId}/completions`) && resp.request().method() === 'POST'
    );

    await page.getByTestId('chat-send').click();

    const completionReq = await completionRequestPromise;
    const completionReqBody = completionReq.postDataJSON();
    expect(completionReqBody?.question).toBe(CHAT_QUESTION);

    const completionResp = await completionResponsePromise;
    expect(completionResp.ok(), 'chat completion request failed').toBeTruthy();

    await expect(assistantMessages).toHaveCount(assistantBeforeCount + 1, { timeout: 90_000 });
    const assistantMessage = assistantMessages.nth(assistantBeforeCount);
    await expect(assistantMessage).toBeVisible({ timeout: 30_000 });
    await expect
      .poll(
        async () => {
          const text = await assistantMessage.textContent();
          return String(text || '').trim().length;
        },
        { timeout: 120_000 }
      )
      .toBeGreaterThan(0);
    await expect(page.getByTestId('chat-error')).toHaveCount(0);

    const finalAssistantText = String((await assistantMessage.textContent()) || '').toLowerCase();
    expect(finalAssistantText.includes('backend_error')).toBeFalsy();
    expect(finalAssistantText.includes('upstream_stream_disconnected')).toBeFalsy();

    await page.goto(`${FRONTEND_BASE_URL}/agents`);
    await expect(page.getByTestId('agents-search-input')).toBeVisible({ timeout: 30_000 });
    await page.getByTestId('agents-search-input').fill(SEARCH_QUERY);
    await expect(page.getByTestId('agents-search-button')).toBeEnabled({ timeout: 30_000 });

    const [searchResp] = await Promise.all([
      page.waitForResponse((resp) => resp.url().includes('/api/search') && resp.request().method() === 'POST'),
      page.getByTestId('agents-search-button').click(),
    ]);
    expect(searchResp.ok(), 'global search request failed').toBeTruthy();
    const searchReqPayload = searchResp.request().postDataJSON();
    expect(String(searchReqPayload?.question || '').trim()).toBe(SEARCH_QUERY);

    const searchPayload = await searchResp.json();
    const chunks = Array.isArray(searchPayload?.chunks) ? searchPayload.chunks : [];
    expect(chunks.length, `"${SEARCH_QUERY}" returned no chunks`).toBeGreaterThan(0);

    await expect(page.getByTestId('agents-result-item-0')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('agents-results-summary')).toContainText(/\d+/);
    await expect(page.getByTestId('agents-error')).toHaveCount(0);
  } finally {
    try {
      if (targetChatId && createdSessionId) {
        await api.delete(`/api/chats/${targetChatId}/sessions`, {
          headers,
          data: { ids: [createdSessionId] },
        });
      }
    } finally {
      await api.dispose();
    }
  }
});
