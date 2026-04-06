import { authBackendUrl } from '../../../config/backend';
import { documentsApi } from '../../documents/api';
import { httpClient } from '../../../shared/http/httpClient';

const normalizeAllowedExtensionsPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (!Array.isArray(payload.allowed_extensions)) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (!Number.isInteger(payload.updated_at_ms) || payload.updated_at_ms < 0) {
    throw new Error(`${action}_invalid_payload`);
  }
  if (
    payload.allowed_extensions.some(
      (item) => typeof item !== 'string' || !item.trim()
    )
  ) {
    throw new Error(`${action}_invalid_payload`);
  }
  return {
    allowedExtensions: payload.allowed_extensions,
    updatedAtMs: payload.updated_at_ms,
  };
};

export const knowledgeUploadApi = {
  async getAllowedExtensions() {
    return normalizeAllowedExtensionsPayload(
      await httpClient.requestJson(authBackendUrl('/api/knowledge/settings/allowed-extensions'), { method: 'GET' }),
      'knowledge_upload_allowed_extensions_get'
    );
  },

  async updateAllowedExtensions(allowedExtensions, changeReason) {
    return normalizeAllowedExtensionsPayload(
      await httpClient.requestJson(authBackendUrl('/api/knowledge/settings/allowed-extensions'), {
        method: 'PUT',
        body: JSON.stringify({
          allowed_extensions: allowedExtensions || [],
          change_reason: changeReason,
        }),
      }),
      'knowledge_upload_allowed_extensions_update'
    );
  },

  uploadDocument(file, kbId = '展厅') {
    return documentsApi.uploadKnowledge(file, kbId);
  },
};
