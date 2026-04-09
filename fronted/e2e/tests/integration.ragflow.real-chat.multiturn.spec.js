// @ts-check
const { test, expect, request } = require('@playwright/test');
const { FRONTEND_BASE_URL, BACKEND_BASE_URL, preflightAdmin, uiLogin } = require('../helpers/integration');
const { getRealDataConfig, findChatByName } = require('../helpers/ragflowRealData');

async function selectChatAndWaitForSessions(page, targetChatId) {
  const targetSessionsResponse = page
    .waitForResponse(
      (resp) => resp.url().includes(`/api/chats/${targetChatId}/sessions`) && resp.request().method() === 'GET',
      { timeout: 15_000 }
    )
    .catch(() => null);

  await page.getByTestId(`chat-item-${targetChatId}`).click();

  const sessionsResp = await targetSessionsResponse;
  if (sessionsResp) {
    expect(sessionsResp.ok(), `load sessions failed for chat=${targetChatId}`).toBeTruthy();
  }
}

test('ragflow real chat: multi-turn responses on target chat @integration @chat @realdata', async ({ page }) => {
  test.setTimeout(360_000);

  const cfg = getRealDataConfig();
  const pre = await preflightAdmin();
  if (!pre.ok) {
    if (cfg.strict) throw new Error(pre.reason);
    test.skip(true, pre.reason);
  }

  const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });

  let targetChatId = null;
  let createdSessionId = null;

  try {
    const chatLookup = await findChatByName(api, headers, cfg.chatName);
    if (!chatLookup.ok) {
      if (cfg.strict) throw new Error(chatLookup.reason);
      test.skip(true, chatLookup.reason);
    }

    targetChatId = String(chatLookup.chat.id || '');
    expect(targetChatId).toBeTruthy();

    const prompts = cfg.chatPrompts.slice(0, Math.max(1, cfg.maxTerms));
    expect(prompts.length).toBeGreaterThan(0);
    const sessionName = `e2e multi turn ${Date.now()}`;

    const createSessionResp = await api.post(`/api/chats/${targetChatId}/sessions`, {
      headers,
      data: { name: sessionName },
    });
    expect(createSessionResp.ok(), 'precreate chat session failed').toBeTruthy();
    const createdSession = await createSessionResp.json();
    createdSessionId = createdSession?.session?.id ? String(createdSession.session.id) : null;
    expect(createdSessionId, 'created session id missing').toBeTruthy();

    await uiLogin(page);
    await page.goto(`${FRONTEND_BASE_URL}/chat`);
    await expect(page.getByTestId('chat-page')).toBeVisible({ timeout: 30_000 });

    await expect(page.getByTestId(`chat-item-${targetChatId}`)).toBeVisible({ timeout: 30_000 });
    await selectChatAndWaitForSessions(page, targetChatId);
    await expect(page.getByTestId(`chat-session-item-${createdSessionId}`)).toBeVisible({ timeout: 30_000 });
    await page.getByTestId(`chat-session-item-${createdSessionId}`).click();

    const assistantMessages = page.getByTestId('chat-messages').locator("[data-testid$='-assistant']");

    for (const prompt of prompts) {
      const previousAssistantCount = await assistantMessages.count();

      await page.getByTestId('chat-input').fill(prompt);

      const completionReqPromise = page.waitForRequest(
        (req) => req.url().includes(`/api/chats/${targetChatId}/completions`) && req.method() === 'POST'
      );
      const completionRespPromise = page.waitForResponse(
        (resp) => resp.url().includes(`/api/chats/${targetChatId}/completions`) && resp.request().method() === 'POST'
      );

      await page.getByTestId('chat-send').click();

      const completionReq = await completionReqPromise;
      const reqBody = completionReq.postDataJSON();
      expect(String(reqBody?.question || '').trim()).toBe(String(prompt).trim());
      expect(String(reqBody?.session_id || '').trim()).toBe(String(createdSessionId || '').trim());

      const completionResp = await completionRespPromise;
      expect(completionResp.ok(), `chat completion failed for prompt=${prompt}`).toBeTruthy();

      await expect(assistantMessages).toHaveCount(previousAssistantCount + 1, { timeout: 90_000 });

      const currentAssistant = assistantMessages.nth(previousAssistantCount);
      await expect(currentAssistant).toBeVisible({ timeout: 30_000 });
      await expect
        .poll(
          async () => {
            const text = await currentAssistant.textContent();
            return String(text || '').trim().length;
          },
          { timeout: 120_000 }
        )
        .toBeGreaterThan(cfg.minAnswerChars);

      const answer = String((await currentAssistant.textContent()) || '').toLowerCase();
      expect(answer.includes('backend_error')).toBeFalsy();
      expect(answer.includes('upstream_stream_disconnected')).toBeFalsy();
      expect(answer.includes('chat request failed')).toBeFalsy();
      await expect(page.getByTestId('chat-error')).toHaveCount(0);
    }
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
