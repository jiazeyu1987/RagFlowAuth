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
      throw new Error('获取文档列表失败');
    }

    return response.json();
  },

  async uploadDocument(file, kbId = '展厅') {
    console.log('[认证客户端] 开始上传文档');
    console.log('[认证客户端] 上传参数：', {
      文件名: file.name,
      文件大小: file.size,
      kbId,
      知识库标识类型: typeof kbId,
      知识库标识长度: kbId?.length
    });

    const formData = new FormData();
    formData.append('file', file);

    const url = authBackendUrl(`/api/documents/knowledge/upload?kb_id=${encodeURIComponent(kbId)}`);
    console.log('[认证客户端] 请求地址：', url);

    const response = await this.fetchWithAuth(
      url,
      {
        method: 'POST',
        body: formData,
        headers: this.getAuthHeaders(false)
      }
    );

    console.log('[认证客户端] 收到响应：', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok
    });

    if (!response.ok) {
      const error = await response.json();
      console.log('[认证客户端] 错误响应：', error);
      throw new Error(this.resolveErrorMessage(error, '上传文档失败'));
    }

    const result = await response.json();
    console.log('[认证客户端] 上传成功：', result);
    return result;
  },

  async getStats() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/knowledge/stats'),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('获取统计信息失败');
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
      throw new Error(this.resolveErrorMessage(error, '审核通过失败'));
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
      throw new Error(this.resolveErrorMessage(error, '审核驳回失败'));
    }

    return response.json();
  },

  async deleteDocument(docId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/knowledge/${docId}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('删除文档失败');
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
      throw new Error(this.resolveErrorMessage(error, '下载文档失败'));
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
      throw new Error(this.resolveErrorMessage(error, '下载文档失败'));
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
      throw new Error(this.resolveErrorMessage(error, '批量下载文档失败'));
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
      throw new Error('获取删除记录失败');
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
      throw new Error('获取下载记录失败');
    }

    return response.json();
  },
};
