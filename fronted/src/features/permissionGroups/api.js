import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const permissionGroupsApi = {
  list() {
    return httpClient.requestJson(authBackendUrl('/api/permission-groups'), {
      method: 'GET',
    });
  },

  listAssignable() {
    return httpClient.requestJson(authBackendUrl('/api/permission-groups/assignable'), {
      method: 'GET',
    });
  },

  listKnowledgeBases() {
    return httpClient.requestJson(
      authBackendUrl('/api/permission-groups/resources/knowledge-bases'),
      { method: 'GET' }
    );
  },

  listKnowledgeTree() {
    return httpClient.requestJson(
      authBackendUrl('/api/permission-groups/resources/knowledge-tree'),
      { method: 'GET' }
    );
  },

  listGroupFolders() {
    return httpClient.requestJson(
      authBackendUrl('/api/permission-groups/resources/group-folders'),
      { method: 'GET' }
    );
  },

  listChats() {
    return httpClient.requestJson(authBackendUrl('/api/permission-groups/resources/chats'), {
      method: 'GET',
    });
  },

  create(payload) {
    return httpClient.requestJson(authBackendUrl('/api/permission-groups'), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  update(groupId, payload) {
    return httpClient.requestJson(authBackendUrl(`/api/permission-groups/${groupId}`), {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  remove(groupId) {
    return httpClient.requestJson(authBackendUrl(`/api/permission-groups/${groupId}`), {
      method: 'DELETE',
    });
  },

  createFolder(payload) {
    return httpClient.requestJson(authBackendUrl('/api/permission-groups/folders'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  },

  updateFolder(folderId, payload) {
    return httpClient.requestJson(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
    });
  },

  removeFolder(folderId) {
    return httpClient.requestJson(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
      method: 'DELETE',
    });
  },
};
