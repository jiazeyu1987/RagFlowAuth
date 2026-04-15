import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const assertArrayPayload = (payload, action) => {
  if (!Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const assertObjectPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

export const qualitySystemConfigApi = {
  async getConfig() {
    return assertObjectPayload(
      await httpClient.requestJson(authBackendUrl('/api/admin/quality-system-config'), {
        method: 'GET',
      }),
      'quality_system_config_get'
    );
  },

  async searchUsers(keyword, limit = 20) {
    const query = new URLSearchParams();
    if (keyword) query.set('q', String(keyword));
    if (limit) query.set('limit', String(limit));
    const suffix = query.toString();
    return assertArrayPayload(
      await httpClient.requestJson(
        authBackendUrl(
          suffix
            ? `/api/admin/quality-system-config/users?${suffix}`
            : '/api/admin/quality-system-config/users'
        ),
        { method: 'GET' }
      ),
      'quality_system_config_user_search'
    );
  },

  async updateAssignments(positionId, payload) {
    return assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/admin/quality-system-config/positions/${positionId}/assignments`),
        {
          method: 'PUT',
          body: JSON.stringify(payload),
        }
      ),
      'quality_system_config_assignments_update'
    );
  },

  async createFileCategory(payload) {
    return assertObjectPayload(
      await httpClient.requestJson(authBackendUrl('/api/admin/quality-system-config/file-categories'), {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
      'quality_system_config_file_category_create'
    );
  },

  async deactivateFileCategory(categoryId, payload) {
    return assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/admin/quality-system-config/file-categories/${categoryId}/deactivate`),
        {
          method: 'POST',
          body: JSON.stringify(payload),
        }
      ),
      'quality_system_config_file_category_deactivate'
    );
  },
};

export default qualitySystemConfigApi;
