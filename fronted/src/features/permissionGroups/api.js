import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const assertObjectPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const normalizeArrayField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!Array.isArray(envelope[field])) {
    throw new Error(`${action}_invalid_payload`);
  }
  return envelope[field];
};

const normalizeObjectField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  const value = envelope[field];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

const normalizeResultField = (payload, action) => {
  const result = normalizeObjectField(payload, 'result', action);
  if (typeof result.message !== 'string' || !result.message.trim()) {
    throw new Error(`${action}_invalid_payload`);
  }
  return result;
};

export const permissionGroupsApi = {
  async list() {
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/permission-groups'), {
        method: 'GET',
      }),
      'groups',
      'permission_groups_list'
    );
  },

  async listAssignable() {
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/permission-groups/assignable'), {
        method: 'GET',
      }),
      'groups',
      'permission_groups_assignable_list'
    );
  },

  async listKnowledgeBases() {
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/permission-groups/resources/knowledge-bases'), {
        method: 'GET',
      }),
      'knowledge_bases',
      'permission_groups_knowledge_bases'
    );
  },

  async listKnowledgeTree() {
    const data = normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/permission-groups/resources/knowledge-tree'), {
        method: 'GET',
      }),
      'knowledge_tree',
      'permission_groups_knowledge_tree'
    );
    if (!Array.isArray(data.nodes) || !Array.isArray(data.datasets) || typeof data.bindings !== 'object' || data.bindings == null) {
      throw new Error('permission_groups_knowledge_tree_invalid_payload');
    }
    return data;
  },

  async listGroupFolders() {
    const data = normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/permission-groups/resources/group-folders'), {
        method: 'GET',
      }),
      'folder_snapshot',
      'permission_groups_group_folders'
    );
    if (!Array.isArray(data.folders) || typeof data.group_bindings !== 'object' || data.group_bindings == null) {
      throw new Error('permission_groups_group_folders_invalid_payload');
    }
    return data;
  },

  async listChats() {
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/permission-groups/resources/chats'), {
        method: 'GET',
      }),
      'chats',
      'permission_groups_chats'
    );
  },

  async create(payload) {
    const result = normalizeResultField(
      await httpClient.requestJson(authBackendUrl('/api/permission-groups'), {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
      'permission_groups_create'
    );
    if (!Number.isInteger(result.group_id)) {
      throw new Error('permission_groups_create_invalid_payload');
    }
    return result;
  },

  async update(groupId, payload) {
    return normalizeResultField(
      await httpClient.requestJson(authBackendUrl(`/api/permission-groups/${groupId}`), {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
      'permission_groups_update'
    );
  },

  async remove(groupId) {
    return normalizeResultField(
      await httpClient.requestJson(authBackendUrl(`/api/permission-groups/${groupId}`), {
        method: 'DELETE',
      }),
      'permission_groups_delete'
    );
  },

  async createFolder(payload) {
    return normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/permission-groups/folders'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'folder',
      'permission_groups_folder_create'
    );
  },

  async updateFolder(folderId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
        method: 'PUT',
        body: JSON.stringify(payload || {}),
      }),
      'folder',
      'permission_groups_folder_update'
    );
  },

  async removeFolder(folderId) {
    return normalizeResultField(
      await httpClient.requestJson(authBackendUrl(`/api/permission-groups/folders/${encodeURIComponent(folderId)}`), {
        method: 'DELETE',
      }),
      'permission_groups_folder_delete'
    );
  },
};
