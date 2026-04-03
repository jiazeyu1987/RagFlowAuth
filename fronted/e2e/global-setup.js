// @ts-check
const fs = require('node:fs');
const path = require('node:path');
const { request } = require('@playwright/test');
const { getAppVersionFromFrontend } = require('./helpers/appVersion');
const { getEnv } = require('./helpers/env');

const E2E_KB_REFS = Array.from(new Set([
  'KB 1',
  'KB 2',
  'ds-a',
  'ds1',
  'ds2',
  'ds_root',
  'ds_nested',
  'intlife',
  'kb-a',
  'kb-hall',
  'kb-one',
  'kb-two',
  'kb-root',
  'kb-guidewire',
  'kb-company-a',
  'kb-research',
  'kb1',
  'kb_1',
  'kb_2',
  '展厅',
  '展厅聊天',
  '知识库调研',
])).sort((left, right) => left.localeCompare(right, 'zh-Hans-CN'));

/**
 * Write a Playwright storageState file that includes the localStorage keys expected by the React app.
 * IMPORTANT: the app clears auth if STORAGE_KEYS.APP_VERSION != APP_VERSION (see fronted/src/hooks/useAuth.js),
 * so we must set appVersion too.
 */
async function writeStorageState({ storagePath, frontendBaseURL, appVersion, accessToken, refreshToken, user }) {
  const origin = new URL(frontendBaseURL).origin;
  const storageState = {
    cookies: [],
    origins: [
      {
        origin,
        localStorage: [
          { name: 'accessToken', value: String(accessToken || '') },
          { name: 'refreshToken', value: String(refreshToken || '') },
          { name: 'user', value: JSON.stringify(user || {}) },
          { name: 'appVersion', value: String(appVersion || '') },
        ],
      },
    ],
  };

  await fs.promises.mkdir(path.dirname(storagePath), { recursive: true });
  await fs.promises.writeFile(storagePath, JSON.stringify(storageState, null, 2), 'utf8');
}

async function readJsonResponse(resp, fallbackMessage) {
  if (!resp.ok()) {
    const body = await resp.text().catch(() => '');
    throw new Error(`${fallbackMessage}: ${resp.status()} ${body}`);
  }
  return resp.json();
}

async function apiLogin(api, username, password) {
  const loginResp = await api.post('/api/auth/login', {
    data: { username, password },
  });
  const tokens = await readJsonResponse(loginResp, `Login failed for ${username}`);
  const meResp = await api.get('/api/auth/me', {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  const user = await readJsonResponse(meResp, 'GET /api/auth/me failed');
  return { tokens, user };
}

function authHeaders(accessToken) {
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

async function ensurePermissionGroup(api, adminAccessToken, payload) {
  const listResp = await api.get('/api/permission-groups', {
    headers: authHeaders(adminAccessToken),
  });
  const listData = await readJsonResponse(listResp, 'List permission groups failed');
  const groups = Array.isArray(listData?.data) ? listData.data : [];
  const existing = groups.find((group) => group && group.group_name === payload.group_name);

  if (existing?.group_id) {
    const updateResp = await api.put(`/api/permission-groups/${existing.group_id}`, {
      headers: authHeaders(adminAccessToken),
      data: payload,
    });
    await readJsonResponse(updateResp, `Update permission group '${payload.group_name}' failed`);
    return Number(existing.group_id);
  }

  const createResp = await api.post('/api/permission-groups', {
    headers: authHeaders(adminAccessToken),
    data: payload,
  });
  const created = await readJsonResponse(createResp, `Create permission group '${payload.group_name}' failed`);
  const groupId = Number(created?.data?.group_id || 0);
  if (!groupId) {
    throw new Error(`Create permission group '${payload.group_name}' returned no group_id`);
  }
  return groupId;
}

async function findUserByUsername(api, adminAccessToken, username) {
  const resp = await api.get(`/api/users?limit=500&q=${encodeURIComponent(username)}`, {
    headers: authHeaders(adminAccessToken),
  });
  const users = await readJsonResponse(resp, `List users for ${username} failed`);
  const list = Array.isArray(users) ? users : [];
  return list.find((user) => String(user?.username || '').trim() === username) || null;
}

async function ensureUser(api, adminAccessToken, config) {
  const {
    username,
    password,
    role,
    groupIds,
  } = config;

  let existing = await findUserByUsername(api, adminAccessToken, username);

  if (!existing) {
    const createResp = await api.post('/api/users', {
      headers: authHeaders(adminAccessToken),
      data: {
        username,
        password,
        role,
        status: 'active',
        group_ids: groupIds,
        can_change_password: true,
        disable_login_enabled: false,
      },
    });
    existing = await readJsonResponse(createResp, `Create user '${username}' failed`);
  } else {
    const updateResp = await api.put(`/api/users/${existing.user_id}`, {
      headers: authHeaders(adminAccessToken),
      data: {
        role,
        status: 'active',
        group_ids: groupIds,
        can_change_password: true,
        disable_login_enabled: false,
      },
    });
    existing = await readJsonResponse(updateResp, `Update user '${username}' failed`);
  }

  const resetResp = await api.put(`/api/users/${existing.user_id}/password`, {
    headers: authHeaders(adminAccessToken),
    data: {
      new_password: password,
    },
  });
  await readJsonResponse(resetResp, `Reset password for '${username}' failed`);

  return apiLogin(api, username, password);
}

module.exports = async () => {
  const env = getEnv();
  if (env.mode !== 'real') {
    throw new Error(`Unsupported E2E_MODE '${env.mode}'. Mock auth mode has been removed; use E2E_MODE=real.`);
  }

  const appVersion = getAppVersionFromFrontend();
  const api = await request.newContext({ baseURL: env.backendBaseURL });

  try {
    const realAdmin = await apiLogin(api, env.adminUsername, env.adminPassword);

    const viewerGroupId = await ensurePermissionGroup(api, realAdmin.tokens.access_token, {
      group_name: 'viewer',
      description: 'E2E viewer group',
      accessible_kbs: E2E_KB_REFS,
      accessible_chats: [],
      accessible_tools: [],
      can_upload: false,
      can_review: false,
      can_download: true,
      can_copy: false,
      can_delete: false,
      can_manage_kb_directory: false,
      can_view_kb_config: true,
      can_view_tools: true,
    });

    const reviewerGroupId = await ensurePermissionGroup(api, realAdmin.tokens.access_token, {
      group_name: 'e2e_reviewer',
      description: 'E2E reviewer group',
      accessible_kbs: E2E_KB_REFS,
      accessible_chats: [],
      accessible_tools: [],
      can_upload: false,
      can_review: true,
      can_download: true,
      can_copy: false,
      can_delete: false,
      can_manage_kb_directory: false,
      can_view_kb_config: true,
      can_view_tools: true,
    });

    const uploaderGroupId = await ensurePermissionGroup(api, realAdmin.tokens.access_token, {
      group_name: 'e2e_uploader',
      description: 'E2E uploader group',
      accessible_kbs: E2E_KB_REFS,
      accessible_chats: [],
      accessible_tools: [],
      can_upload: true,
      can_review: false,
      can_download: true,
      can_copy: false,
      can_delete: false,
      can_manage_kb_directory: false,
      can_view_kb_config: true,
      can_view_tools: true,
    });

    const operatorGroupId = await ensurePermissionGroup(api, realAdmin.tokens.access_token, {
      group_name: 'e2e_operator',
      description: 'E2E broad business operator group',
      accessible_kbs: E2E_KB_REFS,
      accessible_chats: [],
      accessible_tools: [],
      can_upload: true,
      can_review: true,
      can_download: true,
      can_copy: true,
      can_delete: true,
      can_manage_kb_directory: true,
      can_view_kb_config: true,
      can_view_tools: true,
    });

    const viewer = await ensureUser(api, realAdmin.tokens.access_token, {
      username: 'e2e_viewer',
      password: env.viewerPassword,
      role: 'viewer',
      groupIds: [viewerGroupId],
    });

    const reviewer = await ensureUser(api, realAdmin.tokens.access_token, {
      username: 'e2e_reviewer',
      password: env.reviewerPassword,
      role: 'reviewer',
      groupIds: [reviewerGroupId],
    });

    const uploader = await ensureUser(api, realAdmin.tokens.access_token, {
      username: 'e2e_uploader',
      password: env.uploaderPassword,
      role: 'operator',
      groupIds: [uploaderGroupId],
    });

    const operator = await ensureUser(api, realAdmin.tokens.access_token, {
      username: 'e2e_operator',
      password: env.operatorPassword,
      role: 'operator',
      groupIds: [operatorGroupId],
    });

    const authDir = path.join(__dirname, '.auth');
    const states = [
      { filename: 'real-admin.json', session: realAdmin },
      { filename: 'admin.json', session: operator },
      { filename: 'operator.json', session: operator },
      { filename: 'viewer.json', session: viewer },
      { filename: 'reviewer.json', session: reviewer },
      { filename: 'uploader.json', session: uploader },
    ];

    for (const item of states) {
      await writeStorageState({
        storagePath: path.join(authDir, item.filename),
        frontendBaseURL: env.frontendBaseURL,
        appVersion,
        accessToken: item.session.tokens.access_token,
        refreshToken: item.session.tokens.refresh_token,
        user: item.session.user,
      });
    }
  } finally {
    await api.dispose();
  }
};
