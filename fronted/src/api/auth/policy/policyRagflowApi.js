import { authBackendUrl } from '../../../config/backend';
import {
  extractFilenameFromContentDisposition,
  triggerBlobDownload,
} from './policyDownloadUtils';

export const policyRagflowApiMethods = {
  async listDatasets() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/datasets'),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to list datasets');
    }

    return response.json();
  },

  async listRagflowDocuments(datasetName = '灞曞巺') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/ragflow/documents?dataset_name=${encodeURIComponent(datasetName)}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to list documents');
    }

    return response.json();
  },

  async downloadDocument(docId, datasetName = '灞曞巺') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/ragflow/${docId}/download?dataset=${encodeURIComponent(datasetName)}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to download document');
    }

    return response.blob();
  },

  async downloadRagflowDocument(docId, dataset = '灞曞巺', docName = null) {
    const params = new URLSearchParams({ dataset });
    if (docName) {
      params.append('filename', docName);
    }

    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/ragflow/${docId}/download?${params}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to download document');
    }

    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = docName || extractFilenameFromContentDisposition(contentDisposition, `document_${docId}`);
    const blob = await response.blob();
    triggerBlobDownload(blob, filename);
    return { success: true, filename };
  },

  async previewDocument(docId, dataset = '灞曞巺') {
    const params = new URLSearchParams({ dataset });
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/preview/documents/ragflow/${docId}/preview?${params}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to preview document');
    }

    return await response.json();
  },

  async previewKnowledgeDocument(docId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/preview/documents/knowledge/${docId}/preview`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to preview document');
    }

    return await response.json();
  },

  async previewRagflowDocument(docId, dataset = '灞曞巺', docName = null) {
    const blob = await this.previewRagflowDocumentBlob(docId, dataset, docName);
    const url = window.URL.createObjectURL(blob);
    return url;
  },

  async previewRagflowDocumentBlob(docId, dataset = '灞曞巺', docName = null) {
    const params = new URLSearchParams({ dataset });
    if (docName) {
      params.append('filename', docName);
    }

    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/ragflow/${docId}/download?${params}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to preview document');
    }

    return response.blob();
  },

  async batchDownload(documentsInfo) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/documents/ragflow/batch/download'),
      {
        method: 'POST',
        body: JSON.stringify({ documents: documentsInfo }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to batch download');
    }

    return response.blob();
  },

  async batchDownloadRagflowDocuments(selectedDocs) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/documents/ragflow/batch/download'),
      {
        method: 'POST',
        body: JSON.stringify({ documents: selectedDocs }),
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

  async deleteRagflowDocument(docId, datasetName = '灞曞巺') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/ragflow/${docId}?dataset_name=${encodeURIComponent(datasetName)}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('Failed to delete document');
    }

    return response.json();
  },

  async transferRagflowDocument(docId, sourceDatasetName, targetDatasetName, operation = 'copy') {
    const response = await this.fetchWithAuth(
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

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const detail = typeof error?.detail === 'string' ? error.detail : (error?.detail?.code || '');
      throw new Error(detail || 'Failed to transfer document');
    }

    return response.json();
  },

  async transferRagflowDocumentsBatch(items, operation = 'copy') {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/ragflow/documents/transfer/batch'),
      {
        method: 'POST',
        body: JSON.stringify({
          operation,
          items: Array.isArray(items) ? items : [],
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const detail = typeof error?.detail === 'string' ? error.detail : (error?.detail?.code || '');
      throw new Error(detail || 'Failed to batch transfer documents');
    }

    return response.json();
  },

  async listRagflowDatasets() {
    return this.listDatasets();
  },
};
