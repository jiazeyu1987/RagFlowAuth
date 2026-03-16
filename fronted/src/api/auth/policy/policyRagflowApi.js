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
      throw new Error('获取数据集列表失败');
    }

    return response.json();
  },

  async listRagflowDocuments(datasetName = '展厅') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/ragflow/documents?dataset_name=${encodeURIComponent(datasetName)}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('获取文档列表失败');
    }

    return response.json();
  },

  async downloadDocument(docId, datasetName = '展厅') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/ragflow/${docId}/download?dataset=${encodeURIComponent(datasetName)}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('下载文档失败');
    }

    return response.blob();
  },

  async downloadRagflowDocument(docId, dataset = '展厅', docName = null) {
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
      throw new Error(this.resolveErrorMessage(error, '下载文档失败'));
    }

    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = docName || extractFilenameFromContentDisposition(contentDisposition, `document_${docId}`);
    const blob = await response.blob();
    triggerBlobDownload(blob, filename);
    return { success: true, filename };
  },

  async previewDocument(docId, dataset = '展厅') {
    const params = new URLSearchParams({ dataset });
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/preview/documents/ragflow/${docId}/preview?${params}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(this.resolveErrorMessage(error, '预览文档失败'));
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
      throw new Error(this.resolveErrorMessage(error, '预览文档失败'));
    }

    return await response.json();
  },

  async previewRagflowDocument(docId, dataset = '展厅', docName = null) {
    const blob = await this.previewRagflowDocumentBlob(docId, dataset, docName);
    const url = window.URL.createObjectURL(blob);
    return url;
  },

  async previewRagflowDocumentBlob(docId, dataset = '展厅', docName = null) {
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
      throw new Error(this.resolveErrorMessage(error, '预览文档失败'));
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
      throw new Error('批量下载失败');
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
      throw new Error(this.resolveErrorMessage(error, '批量下载文档失败'));
    }

    const contentDisposition = response.headers.get('Content-Disposition');
    const filename = extractFilenameFromContentDisposition(contentDisposition, `documents_batch_${Date.now()}.zip`);
    const blob = await response.blob();
    triggerBlobDownload(blob, filename);
    return { success: true, filename };
  },

  async deleteRagflowDocument(docId, datasetName = '展厅') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/ragflow/${docId}?dataset_name=${encodeURIComponent(datasetName)}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('删除文档失败');
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
      throw new Error(this.normalizeDisplayError(detail, '转移文档失败'));
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
      throw new Error(this.normalizeDisplayError(detail, '批量转移文档失败'));
    }

    return response.json();
  },

  async listRagflowDatasets() {
    return this.listDatasets();
  },
};
