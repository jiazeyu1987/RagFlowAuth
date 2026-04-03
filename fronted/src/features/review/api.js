import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

function buildSignedReviewBody(signaturePayload = {}, extraBody = {}) {
  return JSON.stringify({
    ...extraBody,
    sign_token: signaturePayload.sign_token,
    signature_meaning: signaturePayload.signature_meaning,
    signature_reason: signaturePayload.signature_reason,
    review_notes: signaturePayload.review_notes ?? signaturePayload.signature_reason ?? null,
  });
}

export const reviewApi = {
  getConflict(docId) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/conflict`), { method: 'GET' });
  },

  approve(docId, signaturePayload) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/approve`), {
      method: 'POST',
      body: buildSignedReviewBody(signaturePayload),
    });
  },

  approveBatch(docIds, signaturePayload) {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/documents/batch/approve'), {
      method: 'POST',
      body: buildSignedReviewBody(signaturePayload, { doc_ids: docIds }),
    });
  },

  approveOverwrite(docId, replaceDocId, signaturePayload) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/approve-overwrite`), {
      method: 'POST',
      body: buildSignedReviewBody(signaturePayload, { replace_doc_id: replaceDocId }),
    });
  },

  reject(docId, signaturePayload) {
    return httpClient.requestJson(authBackendUrl(`/api/knowledge/documents/${docId}/reject`), {
      method: 'POST',
      body: buildSignedReviewBody(signaturePayload),
    });
  },

  rejectBatch(docIds, signaturePayload) {
    return httpClient.requestJson(authBackendUrl('/api/knowledge/documents/batch/reject'), {
      method: 'POST',
      body: buildSignedReviewBody(signaturePayload, { doc_ids: docIds }),
    });
  },
};
