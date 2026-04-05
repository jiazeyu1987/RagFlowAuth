// @ts-check
const { loginApiAs } = require('./docRealFlow');

async function readJson(response, message) {
  if (!response.ok()) {
    const body = await response.text().catch(() => '');
    throw new Error(`${message}: ${response.status()} ${body}`.trim());
  }
  return response.json();
}

async function createPermissionGroup(api, headers, payload) {
  const response = await api.post('/api/permission-groups', { headers, data: payload });
  const body = await readJson(response, `create permission group failed for ${payload.group_name}`);
  const groupId = Number(body?.data?.group_id || 0);
  if (!Number.isInteger(groupId) || groupId <= 0) {
    throw new Error(`create permission group did not return group_id for ${payload.group_name}`);
  }
  return groupId;
}

async function deletePermissionGroup(api, headers, groupId) {
  const response = await api.delete(`/api/permission-groups/${groupId}`, { headers });
  return readJson(response, `delete permission group failed for ${groupId}`);
}

async function getUser(api, headers, userId) {
  const response = await api.get(`/api/users/${encodeURIComponent(userId)}`, { headers });
  return readJson(response, `get user failed for ${userId}`);
}

async function updateUserGroups(api, headers, userId, groupIds) {
  const response = await api.put(`/api/users/${encodeURIComponent(userId)}`, {
    headers,
    data: { group_ids: groupIds },
  });
  return readJson(response, `update user groups failed for ${userId}`);
}

function normalizeGroupIds(rawValue) {
  if (!Array.isArray(rawValue)) return [];
  return rawValue
    .map((groupId) => Number(groupId))
    .filter((groupId) => Number.isInteger(groupId) && groupId > 0);
}

module.exports = {
  createPermissionGroup,
  deletePermissionGroup,
  getUser,
  loginApiAs,
  normalizeGroupIds,
  readJson,
  updateUserGroups,
};
