import { authBackendUrl } from '../../../config/backend';
import { httpClient } from '../../../shared/http/httpClient';

export const documentBrowserApi = {
  async listDocuments(datasetName = '灞曞巺') {
    const query = new URLSearchParams({
      dataset_name: String(datasetName || ''),
    }).toString();
    const response = await httpClient.requestJson(authBackendUrl(`/api/ragflow/documents?${query}`), {
      method: 'GET',
    });
    return Array.isArray(response?.documents) ? response.documents : [];
  },

  transferDocument(docId, sourceDatasetName, targetDatasetName, operation = 'copy') {
    return httpClient.requestJson(
      authBackendUrl(`/api/ragflow/documents/${encodeURIComponent(docId)}/transfer`),
      {
        method: 'POST',
        body: JSON.stringify({
          source_dataset_name: sourceDatasetName,
          target_dataset_name: targetDatasetName,
          operation,
        }),
      }
    );
  },
};

