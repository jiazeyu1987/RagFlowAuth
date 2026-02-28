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
    if (!response.ok) throw new Error(await parseError(response, 'Failed to load permission groups'));
    return response.json();
  },

  async listKnowledgeBases() {
    const response = await authClient.fetchWithAuth(
      authBackendUrl('/api/permission-groups/resources/knowledge-bases'),
      { method: 'GET' }
    );
    if (!response.ok) throw new Error(await parseError(response, 'Failed to load knowledge bases'));
    return response.json();
  },

  async listKnowledgeTree() {
    const response = await authClient.fetchWithAuth(
      authBackendUrl('/api/permission-groups/resources/knowledge-tree'),
      { method: 'GET' }
    );
    if (!response.ok) throw new Error(await parseError(response, 'Failed to load knowledge tree'));
    return response.json();
  },

  async listGroupFolders() {
    const response = await authClient.fetchWithAuth(
      authBackendUrl('/api/permission-groups/resources/group-folders'),
      { method: 'GET' }
    );
    if (!response.ok) throw new Error(await parseError(response, 'Failed to load permission group folders'));
    return response.json();
  },

  async listChats() {
    const response = await authClient.fetchWithAuth(authBackendUrl('/api/permission-groups/resources/chats'), {
      method: 'GET',
    });
    if (!response.ok) throw new Error(await parseError(response, 'Failed to load chats'));
    return response.json();
  },

  async create(payload) {
    const response = await authClient.fetchWithAuth(authBackendUrl('/api/permission-groups'), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await parseError(response, 'Failed to create permission group'));
    return response.json();
  },

  async update(groupId, payload) {
    const response = await authClient.fetchWithAuth(authBackendUrl(`/api/permission-groups/${groupId}`), {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await parseError(response, 'Failed to update permission group'));
    return response.json();
  },

  async remove(groupId) {
    const response = await authClient.fetchWithAuth(authBackendUrl(`/api/permission-groups/${groupId}`), {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(await parseError(response, 'Failed to delete permission group'));
    return response.json();
  },

  async createFolder(payload) {
    const response = await authClient.fetchWithAuth(authBackendUrl('/api/permission-groups/folders'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    if (!response.ok) throw new Error(await parseError(response, 'Failed to create folder'));
    return response.json();
  },

  async updateFolder(folderId, payload) {
    const response = await authClient.fetchWithAuth(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
    });
    if (!response.ok) throw new Error(await parseError(response, 'Failed to update folder'));
    return response.json();
  },

  async removeFolder(folderId) {
    const response = await authClient.fetchWithAuth(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(await parseError(response, 'Failed to delete folder'));
    return response.json();
  },
};
