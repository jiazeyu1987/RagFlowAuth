// @ts-check
const { poll } = require('./documentFlow');
const { createPermissionGroup, deletePermissionGroup } = require('./permissionGroupsFlow');
const {
  deleteUserById,
  ensureUserDeletedByUsername,
  findUserByUsername,
  loginApiAs,
  readUserEnvelope,
  uniquePassword,
  uniqueUsername,
} = require('./userLifecycleFlow');

async function readJson(response, fallbackMessage) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${fallbackMessage}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

async function disposeSession(session) {
  if (!session?.api) return;
  await session.api.dispose().catch(() => {});
}

async function updateDataSecuritySettings(api, headers, updates, {
  changeReason = 'worker-05 real doc e2e update',
} = {}) {
  const response = await api.put('/api/admin/data-security/settings', {
    headers,
    data: {
      ...(updates || {}),
      change_reason: changeReason,
    },
  });
  return readJson(response, 'update data security settings failed');
}

async function listDataSecurityJobs(api, headers, limit = 30) {
  const response = await api.get(`/api/admin/data-security/backup/jobs?limit=${encodeURIComponent(limit)}`, {
    headers,
  });
  const body = await readJson(response, 'list data security jobs failed');
  return Array.isArray(body?.jobs) ? body.jobs : [];
}

async function getDataSecurityJob(api, headers, jobId) {
  const response = await api.get(`/api/admin/data-security/backup/jobs/${encodeURIComponent(jobId)}`, {
    headers,
  });
  return readJson(response, `get data security job failed for ${jobId}`);
}

async function listRestoreDrills(api, headers, limit = 30) {
  const response = await api.get(`/api/admin/data-security/restore-drills?limit=${encodeURIComponent(limit)}`, {
    headers,
  });
  const body = await readJson(response, 'list restore drills failed');
  return Array.isArray(body?.items) ? body.items : [];
}

async function waitForDataSecurityJobTerminal(api, headers, jobId, {
  timeoutMs = 300_000,
  intervalMs = 2_000,
} = {}) {
  const settled = await poll(async () => {
    const job = await getDataSecurityJob(api, headers, jobId);
    const status = String(job?.status || '').toLowerCase();
    if (status && !['queued', 'running', 'canceling'].includes(status)) {
      return job;
    }
    return null;
  }, { timeoutMs, intervalMs });
  if (!settled) {
    throw new Error(`data security job ${jobId} did not reach terminal state`);
  }
  return settled;
}

async function createToolsEmptyStateAccount(summary, {
  adminPassword = process.env.E2E_ADMIN_PASS || 'admin123',
  subAdminPassword = process.env.E2E_SUB_ADMIN_PASS || adminPassword,
} = {}) {
  const adminUsername = process.env.E2E_ADMIN_USER || summary?.users?.admin?.username;
  const subAdminUsername = process.env.E2E_SUB_ADMIN_USER || summary?.users?.sub_admin?.username;
  if (!adminUsername || !subAdminUsername) {
    throw new Error('missing admin or sub-admin username in bootstrap summary');
  }

  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let adminSession = null;
  /** @type {Awaited<ReturnType<typeof loginApiAs>> | null} */
  let subAdminSession = null;
  let groupId = 0;
  let userId = '';
  const username = uniqueUsername('doc_tools_empty');
  const password = uniquePassword('DocToolsEmpty');

  try {
    adminSession = await loginApiAs(adminUsername, adminPassword);
    subAdminSession = await loginApiAs(subAdminUsername, subAdminPassword);

    await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, username);

    const viewerUser = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      summary?.users?.viewer?.username
    );
    const subAdminUser = await findUserByUsername(
      adminSession.api,
      adminSession.headers,
      subAdminUsername
    );
    if (!viewerUser?.company_id || !subAdminUser?.user_id) {
      throw new Error('bootstrap viewer/sub-admin user missing company or manager reference');
    }

    groupId = await createPermissionGroup(subAdminSession.api, subAdminSession.headers, {
      group_name: `doc_tools_empty_${Date.now()}`,
      description: 'worker-05 real tools empty-state group',
      accessible_tools: ['ghost_tool'],
      can_view_tools: true,
      can_view_kb_config: false,
      can_download: false,
      can_upload: false,
      can_review: false,
      can_copy: false,
      can_delete: false,
      can_manage_kb_directory: false,
    });

    const createResponse = await adminSession.api.post('/api/users', {
      headers: adminSession.headers,
      data: {
        username,
        password,
        full_name: `Doc Tools Empty ${Date.now()}`,
        role: 'viewer',
        manager_user_id: subAdminUser.user_id,
        company_id: viewerUser.company_id,
        department_id: viewerUser.department_id,
        status: 'active',
        max_login_sessions: 3,
        idle_timeout_minutes: 120,
      },
    });
    const createBody = await readJson(createResponse, `create tools empty-state user failed for ${username}`);
    userId = String(
      readUserEnvelope(createBody, `create tools empty-state user returned invalid payload for ${username}`).user_id || ''
    ).trim();
    if (!userId) {
      throw new Error(`create tools empty-state user did not return user_id for ${username}`);
    }

    const assignGroupResponse = await subAdminSession.api.put(`/api/users/${encodeURIComponent(userId)}`, {
      headers: subAdminSession.headers,
      data: { group_ids: [groupId] },
    });
    await readJson(assignGroupResponse, `assign tools empty-state group failed for ${username}`);

    const userSession = await loginApiAs(username, password);

    return {
      username,
      password,
      userId,
      groupId,
      adminSession,
      subAdminSession,
      userSession,
      cleanup: async () => {
        if (adminSession && userId) {
          await deleteUserById(adminSession.api, adminSession.headers, userId);
        } else if (adminSession) {
          await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, username);
        }
        if (subAdminSession && groupId > 0) {
          await deletePermissionGroup(subAdminSession.api, subAdminSession.headers, groupId).catch(() => {});
        }
        await disposeSession(userSession);
        await disposeSession(subAdminSession);
        await disposeSession(adminSession);
      },
    };
  } catch (error) {
    if (adminSession) {
      if (userId) {
        await deleteUserById(adminSession.api, adminSession.headers, userId).catch(() => {});
      } else {
        await ensureUserDeletedByUsername(adminSession.api, adminSession.headers, username).catch(() => {});
      }
    }
    if (subAdminSession && groupId > 0) {
      await deletePermissionGroup(subAdminSession.api, subAdminSession.headers, groupId).catch(() => {});
    }
    await disposeSession(subAdminSession);
    await disposeSession(adminSession);
    throw error;
  }
}

module.exports = {
  createToolsEmptyStateAccount,
  disposeSession,
  getDataSecurityJob,
  listDataSecurityJobs,
  listRestoreDrills,
  loginApiAs,
  readJson,
  updateDataSecuritySettings,
  waitForDataSecurityJobTerminal,
};
