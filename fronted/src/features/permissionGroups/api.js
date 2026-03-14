import authClient from '../../api/authClient';
import { authBackendUrl } from '../../config/backend';

const parseError = async (response, fallbackMessage) => {
  try {
    const data = await response.json();
    return data?.detail || data?.message || data?.error || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
};

export const permissionGroupsApi = {
  async list() {
    const response = await authClient.fetchWithAuth(authBackendUrl('/api/permission-groups'), {
      method: 'GET',
    });
    if (!response.ok) throw new Error(await parseError(response, '加载权限分组失败'));
    return response.json();
  },

  async listKnowledgeBases() {
    const response = await authClient.fetchWithAuth(
      authBackendUrl('/api/permission-groups/resources/knowledge-bases'),
      { method: 'GET' }
    );
    if (!response.ok) throw new Error(await parseError(response, '加载知识库失败'));
    return response.json();
  },

  async listKnowledgeTree() {
    const response = await authClient.fetchWithAuth(
      authBackendUrl('/api/permission-groups/resources/knowledge-tree'),
      { method: 'GET' }
    );
    if (response.ok) {
      return response.json();
    }

    // Backward compatibility for environments that only expose knowledge-bases.
    const fallback = await authClient.fetchWithAuth(
      authBackendUrl('/api/permission-groups/resources/knowledge-bases'),
      { method: 'GET' }
    );
    if (!fallback.ok) {
      throw new Error(await parseError(response, '加载知识树失败'));
    }
    const data = await fallback.json();
    const datasets = Array.isArray(data?.data) ? data.data : [];
    return { ok: true, data: { nodes: [], datasets } };
  },

  async listGroupFolders() {
    const response = await authClient.fetchWithAuth(
      authBackendUrl('/api/permission-groups/resources/group-folders'),
      { method: 'GET' }
    );
    if (!response.ok) throw new Error(await parseError(response, '加载权限分组文件夹失败'));
    return response.json();
  },

  async listChats() {
    const response = await authClient.fetchWithAuth(authBackendUrl('/api/permission-groups/resources/chats'), {
      method: 'GET',
    });
    if (!response.ok) throw new Error(await parseError(response, '加载对话列表失败'));
    return response.json();
  },

  async create(payload) {
    const response = await authClient.fetchWithAuth(authBackendUrl('/api/permission-groups'), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await parseError(response, '创建权限分组失败'));
    return response.json();
  },

  async update(groupId, payload) {
    const response = await authClient.fetchWithAuth(authBackendUrl(`/api/permission-groups/${groupId}`), {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await parseError(response, '更新权限分组失败'));
    return response.json();
  },

  async remove(groupId) {
    const response = await authClient.fetchWithAuth(authBackendUrl(`/api/permission-groups/${groupId}`), {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(await parseError(response, '删除权限分组失败'));
    return response.json();
  },

  async createFolder(payload) {
    const response = await authClient.fetchWithAuth(authBackendUrl('/api/permission-groups/folders'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    if (!response.ok) throw new Error(await parseError(response, '创建文件夹失败'));
    return response.json();
  },

  async updateFolder(folderId, payload) {
    const response = await authClient.fetchWithAuth(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
    });
    if (!response.ok) throw new Error(await parseError(response, '更新文件夹失败'));
    return response.json();
  },

  async removeFolder(folderId) {
    const response = await authClient.fetchWithAuth(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(await parseError(response, '删除文件夹失败'));
    return response.json();
  },
};
