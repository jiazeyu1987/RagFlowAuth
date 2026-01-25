// @ts-check
const { test, expect, request } = require('@playwright/test');
const { BACKEND_BASE_URL, preflightAdmin } = require('../helpers/integration');

test('permission groups resources endpoints (real backend) @integration', async () => {
  test.setTimeout(60_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  try {
    const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };

    const kbResp = await api.get('/api/permission-groups/resources/knowledge-bases', { headers });
    expect(kbResp.status()).toBe(200);
    const kbJson = await kbResp.json();
    expect(typeof kbJson).toBe('object');
    expect(typeof kbJson.ok).toBe('boolean');
    if (!kbJson.ok) {
      test.skip(true, `knowledge-bases not available: ${kbJson.error || kbJson.detail || 'unknown error'}`);
    }
    expect(Array.isArray(kbJson.data)).toBeTruthy();

    const chatResp = await api.get('/api/permission-groups/resources/chats', { headers });
    expect(chatResp.status()).toBe(200);
    const chatJson = await chatResp.json();
    expect(typeof chatJson).toBe('object');
    expect(typeof chatJson.ok).toBe('boolean');
    if (!chatJson.ok) {
      test.skip(true, `chats not available: ${chatJson.error || chatJson.detail || 'unknown error'}`);
    }
    expect(Array.isArray(chatJson.data)).toBeTruthy();
  } finally {
    await api.dispose();
  }
});

