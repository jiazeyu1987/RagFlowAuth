import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const assertSuccessEnvelope = (response, action) => {
  if (response?.ok !== true) {
    const detail = String(response?.error || response?.detail || '').trim();
    throw new Error(detail || `${action}_failed`);
  }
  return response;
};

const unwrapEnvelopeData = (response, action) => {
  const envelope = assertSuccessEnvelope(response, action);
  if (!Object.prototype.hasOwnProperty.call(envelope, 'data')) {
    throw new Error(`${action}_missing_data`);
  }
  return envelope.data;
};

const unwrapArrayData = (response, action) => {
  const data = unwrapEnvelopeData(response, action);
  if (!Array.isArray(data)) {
    throw new Error(`${action}_invalid_data`);
  }
  return data;
};

const unwrapObjectData = (response, action) => {
  const data = unwrapEnvelopeData(response, action);
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error(`${action}_invalid_data`);
  }
  return data;
};

export const permissionGroupsApi = {
  async list() {
    const response = await httpClient.requestJson(authBackendUrl('/api/permission-groups'), {
      method: 'GET',
    });
    return unwrapArrayData(response, 'permission_groups_list');
  },

  async listAssignable() {
    const response = await httpClient.requestJson(authBackendUrl('/api/permission-groups/assignable'), {
      method: 'GET',
    });
    return unwrapArrayData(response, 'permission_groups_assignable_list');
  },

  async listKnowledgeBases() {
    const response = await httpClient.requestJson(
      authBackendUrl('/api/permission-groups/resources/knowledge-bases'),
      { method: 'GET' }
    );
    return unwrapArrayData(response, 'permission_groups_knowledge_bases');
  },

  async listKnowledgeTree() {
    const response = await httpClient.requestJson(
      authBackendUrl('/api/permission-groups/resources/knowledge-tree'),
      { method: 'GET' }
    );
    const data = unwrapObjectData(response, 'permission_groups_knowledge_tree');
    if (!Array.isArray(data.nodes) || !Array.isArray(data.datasets) || typeof data.bindings !== 'object' || data.bindings == null) {
      throw new Error('permission_groups_knowledge_tree_invalid_data');
    }
    return data;
  },

  async listGroupFolders() {
    const response = await httpClient.requestJson(
      authBackendUrl('/api/permission-groups/resources/group-folders'),
      { method: 'GET' }
    );
    const data = unwrapObjectData(response, 'permission_groups_group_folders');
    if (!Array.isArray(data.folders) || typeof data.group_bindings !== 'object' || data.group_bindings == null) {
      throw new Error('permission_groups_group_folders_invalid_data');
    }
    return data;
  },

  async listChats() {
    const response = await httpClient.requestJson(authBackendUrl('/api/permission-groups/resources/chats'), {
      method: 'GET',
    });
    return unwrapArrayData(response, 'permission_groups_chats');
  },

  async create(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/permission-groups'), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return unwrapObjectData(response, 'permission_groups_create');
  },

  async update(groupId, payload) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/permission-groups/${groupId}`), {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    assertSuccessEnvelope(response, 'permission_groups_update');
  },

  async remove(groupId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/permission-groups/${groupId}`), {
      method: 'DELETE',
    });
    assertSuccessEnvelope(response, 'permission_groups_delete');
  },

  async createFolder(payload) {
    const response = await httpClient.requestJson(authBackendUrl('/api/permission-groups/folders'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
    return unwrapObjectData(response, 'permission_groups_folder_create');
  },

  async updateFolder(folderId, payload) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
    });
    return unwrapObjectData(response, 'permission_groups_folder_update');
  },

  async removeFolder(folderId) {
    const response = await httpClient.requestJson(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
      method: 'DELETE',
    });
    assertSuccessEnvelope(response, 'permission_groups_folder_delete');
  },
};
