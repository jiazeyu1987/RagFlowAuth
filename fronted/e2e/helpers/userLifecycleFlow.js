// @ts-check
const { request } = require('@playwright/test');
const { BACKEND_BASE_URL } = require('./integration');
const { poll } = require('./documentFlow');

async function readJson(response, fallbackMessage) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${fallbackMessage}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

function readUserEnvelope(payload, fallbackMessage) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${fallbackMessage}: invalid envelope`);
  }
  const user = payload.user;
  if (!user || typeof user !== 'object' || Array.isArray(user)) {
    throw new Error(`${fallbackMessage}: missing user`);
  }
  if (!String(user.user_id || '').trim()) {
    throw new Error(`${fallbackMessage}: missing user.user_id`);
  }
  return user;
}

async function loginApiAs(username, password) {
  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  const loginResponse = await api.post('/api/auth/login', {
    data: { username, password },
  });
  const tokens = await readJson(loginResponse, `login failed for ${username}`);
  const headers = { Authorization: `Bearer ${tokens.access_token}` };
  const meResponse = await api.get('/api/auth/me', { headers });
  const user = await readJson(meResponse, `get current user failed for ${username}`);
  return { api, headers, tokens, user };
}

async function tryLoginApi(username, password) {
  const api = await request.newContext({ baseURL: BACKEND_BASE_URL });
  try {
    const loginResponse = await api.post('/api/auth/login', {
      data: { username, password },
    });
    const body = await loginResponse.json().catch(() => ({}));
    return {
      ok: loginResponse.ok(),
      status: loginResponse.status(),
      body,
    };
  } finally {
    await api.dispose();
  }
}

function uniqueUsername(prefix = 'doc_e2e_user') {
  const seed = `${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  return `${prefix}_${seed}`;
}

function uniquePassword(prefix = 'DocE2E') {
  const seed = `${Date.now()}${Math.floor(Math.random() * 900 + 100)}`;
  return `${prefix}${seed}a1`;
}

async function listUsers(api, headers, params = {}) {
  const query = new URLSearchParams(params).toString();
  const response = await api.get(`/api/users${query ? `?${query}` : ''}`, { headers });
  return readJson(response, 'list users failed');
}

async function findUserByUsername(api, headers, username) {
  const users = await listUsers(api, headers, { q: username, limit: '100' });
  return (Array.isArray(users) ? users : []).find(
    (item) => String(item?.username || '') === String(username || '')
  ) || null;
}

async function deleteUserById(api, headers, userId) {
  const response = await api.delete(`/api/users/${encodeURIComponent(userId)}`, { headers });
  if (!response.ok() && response.status() !== 404) {
    const body = await response.text().catch(() => '');
    throw new Error(`delete user failed for ${userId}: ${response.status()} ${body}`.trim());
  }
}

async function ensureUserDeletedByUsername(api, headers, username) {
  const found = await findUserByUsername(api, headers, username);
  if (!found?.user_id) return;
  await deleteUserById(api, headers, String(found.user_id));
}

async function waitForUserVisible(api, headers, username, {
  timeoutMs = 60_000,
  intervalMs = 1_000,
} = {}) {
  return poll(async () => {
    const found = await findUserByUsername(api, headers, username);
    return found || null;
  }, { timeoutMs, intervalMs });
}

async function readSelectableOptions(selectLocator) {
  return selectLocator.locator('option').evaluateAll((options) => (
    options
      .map((option) => ({
        value: String(option.value || '').trim(),
        disabled: Boolean(option.disabled),
      }))
      .filter((item) => item.value && !item.disabled)
  ));
}

async function pickFirstSelectableOption(selectLocator, fieldName) {
  const options = await readSelectableOptions(selectLocator);
  const picked = options.find((item) => item.value);
  if (!picked) {
    throw new Error(`no selectable option for ${fieldName}`);
  }
  await selectLocator.selectOption(picked.value);
  return picked.value;
}

module.exports = {
  deleteUserById,
  ensureUserDeletedByUsername,
  findUserByUsername,
  listUsers,
  loginApiAs,
  pickFirstSelectableOption,
  readUserEnvelope,
  tryLoginApi,
  uniquePassword,
  uniqueUsername,
  waitForUserVisible,
};
