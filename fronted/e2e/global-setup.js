// @ts-check
const fs = require('node:fs');
const path = require('node:path');
const { request } = require('@playwright/test');
const { getAppVersionFromFrontend } = require('./helpers/appVersion');
const { getEnv } = require('./helpers/env');

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

async function apiLogin(api, username, password) {
  const loginResp = await api.post('/api/auth/login', {
    data: { username, password },
  });
  if (!loginResp.ok()) {
    const body = await loginResp.text().catch(() => '');
    throw new Error(`Login failed for ${username}: ${loginResp.status()} ${body}`);
  }
  const tokens = await loginResp.json();
  const meResp = await api.get('/api/auth/me', {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
  });
  if (!meResp.ok()) {
    const body = await meResp.text().catch(() => '');
    throw new Error(`GET /api/auth/me failed: ${meResp.status()} ${body}`);
  }
  const user = await meResp.json();
  return { tokens, user };
}

async function createViewerUser(api, adminAccessToken, username, password) {
  // Ensure a "viewer" permission group exists (backend may not seed defaults).
  const listResp = await api.get('/api/permission-groups', {
    headers: { Authorization: `Bearer ${adminAccessToken}` },
  });
  if (!listResp.ok()) {
    const body = await listResp.text().catch(() => '');
    throw new Error(`List permission groups failed: ${listResp.status()} ${body}`);
  }
  const listData = await listResp.json();
  const groups = Array.isArray(listData?.data) ? listData.data : [];
  let viewerGroup = groups.find((g) => g && g.group_name === 'viewer');

  if (!viewerGroup) {
    const createResp = await api.post('/api/permission-groups', {
      headers: { Authorization: `Bearer ${adminAccessToken}` },
      data: {
        group_name: 'viewer',
        description: 'E2E default viewer group',
        accessible_kbs: [],
        accessible_chats: [],
        can_upload: false,
        can_review: false,
        can_download: true,
        can_delete: false,
      },
    });
    if (!createResp.ok()) {
      const body = await createResp.text().catch(() => '');
      throw new Error(`Create permission group 'viewer' failed: ${createResp.status()} ${body}`);
    }
    const created = await createResp.json();
    viewerGroup = { group_id: created?.data?.group_id, group_name: 'viewer' };
  }

  const resp = await api.post('/api/users', {
    headers: { Authorization: `Bearer ${adminAccessToken}` },
    data: {
      username,
      password,
      role: 'viewer',
      status: 'active',
      group_ids: viewerGroup?.group_id ? [viewerGroup.group_id] : undefined,
    },
  });

  // The backend currently raises ValueError on duplicate usernames which may surface as 500.
  // To avoid flakiness, we always use a unique username per run.
  if (!resp.ok()) {
    const body = await resp.text().catch(() => '');
    throw new Error(`Create viewer user failed: ${resp.status()} ${body}`);
  }
}

module.exports = async () => {
  const env = getEnv();
  const appVersion = getAppVersionFromFrontend();

  if (env.mode === 'mock') {
    const authDir = path.join(__dirname, '.auth');
    const adminStatePath = path.join(authDir, 'admin.json');
    const viewerStatePath = path.join(authDir, 'viewer.json');

    const adminUser = {
      user_id: 'e2e_admin',
      username: env.adminUsername || 'admin',
      role: 'admin',
      status: 'active',
      group_ids: [1],
      permissions: { can_upload: true, can_review: true, can_download: true, can_delete: true },
      accessible_kbs: [],
      accessible_kb_ids: [],
      accessible_chats: [],
    };

    const viewerUser = {
      user_id: 'e2e_viewer',
      username: 'viewer',
      role: 'viewer',
      status: 'active',
      group_ids: [2],
      permissions: { can_upload: false, can_review: false, can_download: true, can_delete: false },
      accessible_kbs: [],
      accessible_kb_ids: [],
      accessible_chats: [],
    };

    await writeStorageState({
      storagePath: adminStatePath,
      frontendBaseURL: env.frontendBaseURL,
      appVersion,
      accessToken: 'e2e_access_token',
      refreshToken: 'e2e_refresh_token',
      user: adminUser,
    });

    await writeStorageState({
      storagePath: viewerStatePath,
      frontendBaseURL: env.frontendBaseURL,
      appVersion,
      accessToken: 'e2e_access_token_viewer',
      refreshToken: 'e2e_refresh_token_viewer',
      user: viewerUser,
    });

    return;
  }

  const api = await request.newContext({ baseURL: env.backendBaseURL });

  const admin = await apiLogin(api, env.adminUsername, env.adminPassword);

  const authDir = path.join(__dirname, '.auth');
  const adminStatePath = path.join(authDir, 'admin.json');
  await writeStorageState({
    storagePath: adminStatePath,
    frontendBaseURL: env.frontendBaseURL,
    appVersion,
    accessToken: admin.tokens.access_token,
    refreshToken: admin.tokens.refresh_token,
    user: admin.user,
  });

  const viewerUsername = `e2e_viewer_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  const viewerPassword = env.viewerPassword || 'viewer123';

  await createViewerUser(api, admin.tokens.access_token, viewerUsername, viewerPassword);
  const viewer = await apiLogin(api, viewerUsername, viewerPassword);

  const viewerStatePath = path.join(authDir, 'viewer.json');
  await writeStorageState({
    storagePath: viewerStatePath,
    frontendBaseURL: env.frontendBaseURL,
    appVersion,
    accessToken: viewer.tokens.access_token,
    refreshToken: viewer.tokens.refresh_token,
    user: viewer.user,
  });

  await api.dispose();
};
