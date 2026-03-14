import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const reviewApi = {
  getConflict(docId) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/conflict`), { method: 'GET' });
  },

  listConflicts(limit = 100) {
    const safeLimit = Math.max(1, Math.min(Number(limit) || 100, 500));
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/conflicts?limit=${safeLimit}`), { method: 'GET' });
  },

  approve(docId, reviewNotes = null) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/approve`), {
      method: 'POST',
      body: JSON.stringify({ review_notes: reviewNotes }),
    });
  },

  approveBatch(docIds, reviewNotes = null) {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/documents/batch/approve'), {
      method: 'POST',
      body: JSON.stringify({ doc_ids: docIds, review_notes: reviewNotes }),
    });
  },

  approveOverwrite(docId, replaceDocId, overwriteReason, reviewNotes = null) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/approve-overwrite`), {
      method: 'POST',
      body: JSON.stringify({
        replace_doc_id: replaceDocId,
        overwrite_reason: overwriteReason,
        review_notes: reviewNotes,
      }),
    });
  },

  resolveConflictRename(docId, newFilename, reason = null) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/resolve-conflict-rename`), {
      method: 'POST',
      body: JSON.stringify({
        new_filename: newFilename,
        resolution_reason: reason,
      }),
    });
  },

  resolveConflictSkip(docId, reason = null) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/resolve-conflict-skip`), {
      method: 'POST',
      body: JSON.stringify({
        resolution_reason: reason,
      }),
    });
  },

  reject(docId, reviewNotes = null) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/reject`), {
      method: 'POST',
      body: JSON.stringify({ review_notes: reviewNotes }),
    });
  },

  rejectBatch(docIds, reviewNotes = null) {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/documents/batch/reject'), {
      method: 'POST',
      body: JSON.stringify({ doc_ids: docIds, review_notes: reviewNotes }),
    });
  },
};
