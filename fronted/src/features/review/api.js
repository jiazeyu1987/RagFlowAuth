import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const reviewApi = {
  getConflict(docId) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/conflict`), { method: 'GET' });
  },

  approve(docId, reviewNotes = null) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/approve`), {
      method: 'POST',
      body: JSON.stringify({ review_notes: reviewNotes }),
    });
  },

  approveOverwrite(docId, replaceDocId, reviewNotes = null) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/approve-overwrite`), {
      method: 'POST',
      body: JSON.stringify({ replace_doc_id: replaceDocId, review_notes: reviewNotes }),
    });
  },

  reject(docId, reviewNotes = null) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/reject`), {
      method: 'POST',
      body: JSON.stringify({ review_notes: reviewNotes }),
    });
  },
};
