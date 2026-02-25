// @ts-check
const { request } = require('@playwright/test');

const FRONTEND_BASE_URL = process.env.E2E_FRONTEND_BASE_URL || 'http://localhost:3000';
const BACKEND_BASE_URL = process.env.E2E_BACKEND_BASE_URL || 'http://localhost:8001';
const ADMIN_USER = process.env.E2E_ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.E2E_ADMIN_PASS || 'admin123';

async function backendIsReady() {
  try {
    const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
    const resp = await api.get('/docs');
    await api.dispose();
    return resp.ok();
  } catch {
    return false;
  }
}

async function preflightAdmin() {
  if (!(await backendIsReady())) {
    return { ok: false, reason: `backend not reachable at ${BACKEND_BASE_URL}` };
  }

  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const loginResp = await api.post('/api/auth/login', { data: { username: ADMIN_USER, password: ADMIN_PASS } });
  if (!loginResp.ok()) {
    await api.dispose();
    return { ok: false, reason: 'admin login failed; check E2E_ADMIN_USER/E2E_ADMIN_PASS' };
  }
  const tokens = await loginResp.json();
  const meResp = await api.get('/api/auth/me', { headers: { Authorization: `Bearer ${tokens.access_token}` } });
  if (!meResp.ok()) {
    await api.dispose();
    return { ok: false, reason: 'GET /api/auth/me failed; backend not ready' };
  }
  await api.dispose();

  return { ok: true, tokens };
}

async function uiLogin(page, username = ADMIN_USER, password = ADMIN_PASS) {
  await page.goto(`${FRONTEND_BASE_URL}/login`);
  await page.getByTestId('login-username').fill(username);
  await page.getByTestId('login-password').fill(password);
  const [loginResp] = await Promise.all([
    page.waitForResponse((r) => r.url().includes('/api/auth/login') && r.request().method() === 'POST'),
    page.getByTestId('login-submit').click(),
  ]);
  if (!loginResp.ok()) {
    throw new Error(`UI login failed: ${loginResp.status()}`);
  }
  await page.waitForURL(/(\/|\/chat)$/, { timeout: 30_000 });
}

module.exports = {
  FRONTEND_BASE_URL,
  BACKEND_BASE_URL,
  ADMIN_USER,
  ADMIN_PASS,
  backendIsReady,
  preflightAdmin,
  uiLogin,
};
