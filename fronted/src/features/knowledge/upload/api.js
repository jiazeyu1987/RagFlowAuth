import { authBackendUrl } from '../../../config/backend';
import { documentsApi } from '../../documents/api';
import { httpClient } from '../../../shared/http/httpClient';

export const knowledgeUploadApi = {
  getAllowedExtensions() {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/settings/allowed-extensions'), { method: 'GET' });
  },

  updateAllowedExtensions(allowedExtensions, changeReason) {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/settings/allowed-extensions'), {
      method: 'PUT',
      body: JSON.stringify({
        allowed_extensions: allowedExtensions || [],
        change_reason: changeReason,
      }),
    });
  },

  uploadDocument(file, kbId = '展厅') {
    return documentsApi.uploadKnowledge(file, kbId);
  },
};

