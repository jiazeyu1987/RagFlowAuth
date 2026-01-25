// @ts-check
const { test, expect, request } = require('@playwright/test');
const { BACKEND_BASE_URL, preflightAdmin } = require('../helpers/integration');

test('users reset password -> new password login works (real backend) @integration', async () => {
  test.setTimeout(90_000);

  const pre = await preflightAdmin();
  if (!pre.ok) test.skip(true, pre.reason);

  const username = `e2e_user_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  const oldPassword = 'Passw0rd!123';
  const newPassword = 'NewPassw0rd!123';
  let userId = null;

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  try {
    const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };

    const createResp = await api.post('/api/users', {
      headers,
      data: { username, password: oldPassword, role: 'viewer', status: 'active' },
    });
    expect(createResp.status()).toBe(201);
    const created = await createResp.json();
    userId = created?.user_id || null;
    expect(userId).toBeTruthy();

    const resetResp = await api.put(`/api/users/${userId}/password`, {
      headers,
      data: { new_password: newPassword },
    });
    expect(resetResp.ok()).toBeTruthy();

    // Old password should no longer work.
    const oldLoginResp = await api.post('/api/auth/login', { data: { username, password: oldPassword } });
    expect([400, 401]).toContain(oldLoginResp.status());

    // New password should work.
    const newLoginResp = await api.post('/api/auth/login', { data: { username, password: newPassword } });
    expect(newLoginResp.ok()).toBeTruthy();
    const tokens = await newLoginResp.json();
    expect(tokens?.access_token).toBeTruthy();
  } finally {
    if (userId != null) {
      const headers = { Authorization: `Bearer ${pre.tokens.access_token}` };
      await api.delete(`/api/users/${userId}`, { headers }).catch(() => {});
    }
    await api.dispose();
  }
});

