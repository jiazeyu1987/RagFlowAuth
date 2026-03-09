import { authBackendUrl } from '../../../config/backend';
import {
  extractFilenameFromContentDisposition,
  triggerBlobDownload,
} from './policyDownloadUtils';

export const policyKnowledgeApiMethods = {
  can(role, resource, action) {
    // Deprecated: UI permission checks live in useAuth.can().
    return false;
  },

  async listDocuments(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/knowledge/documents?${queryParams}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to list documents');
    }

    return response.json();
  },

  async uploadDocument(file, kbId = '灞曞巺') {
    console.log('[authClient] Step 6 - uploadDocument called');
    console.log('[authClient] Step 7 - Parameters:', {
      fileName: file.name,
      fileSize: file.size,
      kbId,
      kbIdType: typeof kbId,
      kbIdLength: kbId?.length
    });

    const formData = new FormData();
    formData.append('file', file);

    const url = authBackendUrl(`/api/documents/knowledge/upload?kb_id=${encodeURIComponent(kbId)}`);
    console.log('[authClient] Step 8 - Sending request to:', url);

    const response = await this.fetchWithAuth(
      url,
      {
        method: 'POST',
        body: formData,
        headers: this.getAuthHeaders(false)
      }
    );

    console.log('[authClient] Step 9 - Response received:', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok
    });

    if (!response.ok) {
      const error = await response.json();
      console.log('[authClient] Step 9a - Error response:', error);
      throw new Error(error.detail || 'Failed to upload document');
    }

    const result = await response.json();
    console.log('[authClient] Step 9b - Success response:', result);
    return result;
  },

  async getStats() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/knowledge/stats'),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to get stats');
    }

    return response.json();
  },

  async approveDocument(docId, reviewNotes = null) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/knowledge/documents/${docId}/approve`),
      {
        method: 'POST',
        body: JSON.stringify({ review_notes: reviewNotes }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to approve document');
    }

    return response.json();
  },

  async rejectDocument(docId, reviewNotes = null) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/knowledge/documents/${docId}/reject`),
      {
        method: 'POST',
        body: JSON.stringify({ review_notes: reviewNotes }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to reject document');
    }

    return response.json();
  },

  async deleteDocument(docId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/knowledge/${docId}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('Failed to delete document');
    }

    return response.json();
  },

  async downloadLocalDocument(docId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/knowledge/${docId}/download`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to download document');
    }

    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = extractFilenameFromContentDisposition(contentDisposition, `document_${docId}`);
    const blob = await response.blob();
    triggerBlobDownload(blob, filename);
    return { success: true, filename };
  },

  async downloadLocalDocumentBlob(docId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/knowledge/${docId}/download`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to download document');
    }

    return response.blob();
  },

  async batchDownloadLocalDocuments(docIds) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/documents/knowledge/batch/download'),
      {
        method: 'POST',
        body: JSON.stringify({ doc_ids: docIds }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to batch download documents');
    }

    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = extractFilenameFromContentDisposition(contentDisposition, `documents_batch_${Date.now()}.zip`);
    const blob = await response.blob();
    triggerBlobDownload(blob, filename);
    return { success: true, filename };
  },

  async listDeletions(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/knowledge/deletions?${queryParams}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to list deletions');
    }

    return response.json();
  },

  async listDownloads(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/ragflow/downloads?${queryParams}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to list downloads');
    }

    return response.json();
  },
};
