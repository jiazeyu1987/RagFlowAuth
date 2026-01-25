// @ts-check
const { test, expect, request } = require('@playwright/test');
const { BACKEND_BASE_URL, preflightAdmin } = require('../helpers/integration');

test('diagnostics endpoints basic shape + auth @integration', async () => {
  test.setTimeout(60_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  try {
    // permissions diagnostics should require auth (any user), so without auth should be denied.
    const unauthPerm = await api.get('/api/diagnostics/permissions');
    expect([401, 403]).toContain(unauthPerm.status());

    const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
    const permResp = await api.get('/api/diagnostics/permissions', { headers });
    expect(permResp.ok()).toBeTruthy();
    const permJson = await permResp.json();
    expect(permJson?.user).toBeTruthy();
    expect(permJson?.snapshot).toBeTruthy();
    expect(permJson?.effective_access).toBeTruthy();

    // ragflow diagnostics is admin-only: without auth should be denied.
    const unauthRag = await api.get('/api/diagnostics/ragflow');
    expect([401, 403]).toContain(unauthRag.status());

    const ragResp = await api.get('/api/diagnostics/ragflow', { headers });
    expect(ragResp.ok()).toBeTruthy();
    const ragJson = await ragResp.json();
    expect(ragJson?.ragflow).toBeTruthy();
    expect(ragJson?.chat).toBeTruthy();
    expect(typeof ragJson?.ragflow?.api_key_configured).toBe('boolean');
  } finally {
    await api.dispose();
  }
});

