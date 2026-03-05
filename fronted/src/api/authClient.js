import { authBackendUrl } from '../config/backend';
import tokenStore from '../shared/auth/tokenStore';
import { httpClient } from '../shared/http/httpClient';

/**
 * AuthClient - FastAPI + AuthX 閫傞厤鐗堟湰
 *
 * 涓昏鍙樻洿锛?
 * 1. 鏀寔 access_token 鍜?refresh_token
 * 2. 鑷姩鍒锋柊浠ょ墝鏈哄埗
 * 3. 绉婚櫎 verifyPermission锛堝悗绔嚜鍔ㄦ鏌ワ級
 * 4. 閫傞厤鏂扮殑鐧诲綍鍝嶅簲鏍煎紡
 */
class AuthClient {
  constructor() {
    this.baseURL = authBackendUrl('');
    this.accessToken = tokenStore.getAccessToken();
    this.refreshToken = tokenStore.getRefreshToken();
    this.user = tokenStore.getUser();

    if (!this.accessToken) {
      this.user = null;
    }
  }

  setAuth(accessToken, refreshToken, user) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.user = user;
    tokenStore.setAuth(accessToken, refreshToken, user);
  }

  clearAuth() {
    this.accessToken = null;
    this.refreshToken = null;
    this.user = null;
    tokenStore.clearAuth();
  }

  getAuthHeaders(includeContentType = true) {
    if (!this.accessToken) {
      this.accessToken = tokenStore.getAccessToken();
    }
    const headers = {
      ...(this.accessToken ? { 'Authorization': `Bearer ${this.accessToken}` } : {})
    };
    if (includeContentType) {
      headers['Content-Type'] = 'application/json';
    }
    return headers;
  }

  /**
   * 鑷姩鍒锋柊璁块棶浠ょ墝
   */
  async refreshAccessToken() {
    try {
      const token = await httpClient.refreshAccessToken();
      this.accessToken = token;
      this.refreshToken = tokenStore.getRefreshToken();
      return token;
    } catch (e) {
      this.clearAuth();
      window.location.href = '/login';
      throw e;
    }
  }

  /**
   * 甯﹁嚜鍔ㄥ埛鏂扮殑 fetch 灏佽
   */
  async fetchWithAuth(url, options = {}) {
    const response = await httpClient.request(url, options);
    this.accessToken = tokenStore.getAccessToken();
    this.refreshToken = tokenStore.getRefreshToken();
    this.user = tokenStore.getUser();
    return response;
  }

  /**
   * 鐧诲綍
   * 鍝嶅簲鏍煎紡锛歿 access_token, refresh_token, token_type, scopes }
   * 娉ㄦ剰锛氬悗绔凡涓嶅啀浣跨敤 scopes 鍋氫笟鍔℃巿鏉冿紝scopes 浠呬负鍏煎瀛楁锛堥€氬父涓虹┖鏁扮粍锛夈€?   */
  async login(username, password) {
    const data = await httpClient.requestJson(authBackendUrl('/api/auth/login'), {
      method: 'POST',
      skipAuth: true,
      skipRefresh: true,
      body: JSON.stringify({ username, password }),
    });

    const user = await httpClient.requestJson(authBackendUrl('/api/auth/me'), {
      headers: { 'Authorization': `Bearer ${data.access_token}` },
      skipRefresh: true,
    });

    // 瀛樺偍涓ょ浠ょ墝
    this.setAuth(data.access_token, data.refresh_token, user);

    return {
      ...data,
      user  // 涓轰簡鍏煎鏃т唬鐮?
    };
  }

  /**
   * 鐧诲嚭
   */
  async logout() {
    try {
      await httpClient.requestJson(authBackendUrl('/api/auth/logout'), {
        method: 'POST',
        skipRefresh: true,
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearAuth();
    }
  }

  /**
   * 鑾峰彇褰撳墠鐢ㄦ埛淇℃伅
   */
  async getCurrentUser() {
    const response = await this.fetchWithAuth(authBackendUrl('/api/auth/me'), {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error('Failed to get current user');
    }

    return response.json();
  }

  /**
   * 鏉冮檺妫€鏌ワ紙绠€鍖栫増锛?
   * 鏂板悗绔笉鍐嶉渶瑕佽皟鐢?verify 绔偣
   * 杩欓噷浠呯敤浜庡墠绔?UI 鏄剧ず鎺у埗
   */
  can(role, resource, action) {
    // Deprecated: UI permission checks live in useAuth.can().
    return false;
  }

  /**
   * 浠ヤ笅鏂规硶浣跨敤 fetchWithAuth 鑷姩澶勭悊浠ょ墝鍒锋柊
   */

  async listUsers(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users?${queryParams}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to list users');
    }

    return response.json();
  }

  async createUser(userData) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/users'),
      {
        method: 'POST',
        body: JSON.stringify(userData),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create user');
    }

    return response.json();
  }

  async updateUser(userId, userData) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}`),
      {
        method: 'PUT',
        body: JSON.stringify(userData),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update user');
    }

    return response.json();
  }

  async deleteUser(userId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('Failed to delete user');
    }

    return response.json();
  }

  async resetPassword(userId, newPassword) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/password`),
      {
        method: 'PUT',
        body: JSON.stringify({ new_password: newPassword }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to reset password');
    }

    return response.json();
  }

  async changePassword(oldPassword, newPassword) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/auth/password'),
      {
        method: 'PUT',
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      }
    );

    if (!response.ok) {
      let errorMessage = 'Failed to change password';
      try {
        const data = await response.json();
        if (data?.detail) errorMessage = data.detail;
      } catch {
        // ignore
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

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
  }

  async uploadDocument(file, kbId = '灞曞巺') {
    console.log('[authClient] Step 6 - uploadDocument called');
    console.log('[authClient] Step 7 - Parameters:', {
      fileName: file.name,
      fileSize: file.size,
      kbId: kbId,
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
  }

  async getStats() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/knowledge/stats'),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to get stats');
    }

    return response.json();
  }

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
  }

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
  }

  async deleteDocument(docId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/knowledge/${docId}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('Failed to delete document');
    }

    return response.json();
  }

  async downloadLocalDocument(docId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/knowledge/${docId}/download`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to download document');
    }

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `document_${docId}`;

    if (contentDisposition) {
      const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;\s]+)/i);
      if (utf8Match && utf8Match[1]) {
        filename = decodeURIComponent(utf8Match[1]);
      } else {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
    }

    const blob = await response.blob();

    // Trigger download
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    return { success: true, filename };
  }

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
  }

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

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `documents_batch_${Date.now()}.zip`;

    if (contentDisposition) {
      const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;\s]+)/i);
      if (utf8Match && utf8Match[1]) {
        filename = decodeURIComponent(utf8Match[1]);
      } else {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
    }

    const blob = await response.blob();

    // Trigger download
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    return { success: true, filename };
  }

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
  }

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
  }

  async listDatasets() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/datasets'),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to list datasets');
    }

    return response.json();
  }

  async listRagflowDocuments(datasetName = '灞曞巺') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/ragflow/documents?dataset_name=${encodeURIComponent(datasetName)}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to list documents');
    }

    return response.json();
  }

  async downloadDocument(docId, datasetName = '灞曞巺') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/ragflow/${docId}/download?dataset=${encodeURIComponent(datasetName)}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      throw new Error('Failed to download document');
    }

    return response.blob();
  }

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

    let filename = docName || `document_${docId}`;

    const contentDisposition = response.headers.get('Content-Disposition');
    if (contentDisposition && !docName) {
      const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;\s]+)/i);
      if (utf8Match && utf8Match[1]) {
        filename = decodeURIComponent(utf8Match[1]);
      } else {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
    }

    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    return { success: true, filename };
  }

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
  }

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
  }

  async previewRagflowDocument(docId, dataset = '灞曞巺', docName = null) {
    const blob = await this.previewRagflowDocumentBlob(docId, dataset, docName);
    const url = window.URL.createObjectURL(blob);
    return url;
  }

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
  }

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
  }

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

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `documents_batch_${Date.now()}.zip`;

    if (contentDisposition) {
      const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;\s]+)/i);
      if (utf8Match && utf8Match[1]) {
        filename = decodeURIComponent(utf8Match[1]);
      } else {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
    }

    // Get blob and trigger download
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    return { success: true, filename };
  }

  async deleteRagflowDocument(docId, datasetName = '灞曞巺') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/documents/ragflow/${docId}?dataset_name=${encodeURIComponent(datasetName)}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      throw new Error('Failed to delete document');
    }

    return response.json();
  }

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
  }

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
  }

  // Alias for backwards compatibility
  async listRagflowDatasets() {
    return this.listDatasets();
  }

  // ==================== 鐭ヨ瘑搴撴潈闄愮浉鍏?API ====================

  /**
   * 鑾峰彇鐢ㄦ埛鐨勭煡璇嗗簱鏉冮檺鍒楄〃锛堢鐞嗗憳锛?
   */
  async getUserKnowledgeBases(userId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/kbs`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get user KBs');
    }

    return response.json();  // { kb_ids: [...] }
  }

  /**
   * 鎺堜簣鐢ㄦ埛鐭ヨ瘑搴撴潈闄?
   */
  async grantKnowledgeBaseAccess(userId, kbId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/kbs/${encodeURIComponent(kbId)}`),
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to grant KB access');
    }

    return response.json();
  }

  /**
   * 鎾ら攢鐢ㄦ埛鐭ヨ瘑搴撴潈闄?
   */
  async revokeKnowledgeBaseAccess(userId, kbId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/kbs/${encodeURIComponent(kbId)}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to revoke KB access');
    }

    return response.json();
  }

  /**
   * 鎵归噺鎺堟潈澶氫釜鐢ㄦ埛澶氫釜鐭ヨ瘑搴?
   */
  async batchGrantKnowledgeBases(userIds, kbIds) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/users/batch-grant'),
      {
        method: 'POST',
        body: JSON.stringify({ user_ids: userIds, kb_ids: kbIds })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to batch grant');
    }

    return response.json();
  }

  /**
   * 鑾峰彇褰撳墠鐢ㄦ埛鍙闂殑鐭ヨ瘑搴撳垪琛?
   */
  async getMyKnowledgeBases() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/me/kbs'),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get my KBs');
    }

    return response.json();  // { kb_ids: [...] }
  }

  // ==================== Chat 鐩稿叧 API ====================

  /**
   * 鑾峰彇鐢ㄦ埛鏈夋潈闄愮殑鑱婂ぉ鍔╂墜鍒楄〃
   */
  async listMyChats() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/chats/my'),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get my chats');
    }

    return response.json();  // { chat_ids: [...] }
  }

  /**
   * 鑾峰彇鑱婂ぉ鍔╂墜璇︽儏
   */
  async getChat(chatId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/chats/${chatId}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get chat');
    }

    return response.json();
  }

  /**
   * 鍒涘缓鑱婂ぉ浼氳瘽
   */
  async createChatSession(chatId, name = '新会话') {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/chats/${chatId}/sessions`),
      {
        method: 'POST',
        body: JSON.stringify({ name })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create session');
    }

    return response.json();
  }

  /**
   * 鍒楀嚭鑱婂ぉ鍔╂墜鐨勬墍鏈変細璇?
   */
  async listChatSessions(chatId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/chats/${chatId}/sessions`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to list sessions');
    }

    return response.json();
  }

  /**
   * 鍒犻櫎鑱婂ぉ浼氳瘽
   */
  async deleteChatSessions(chatId, sessionIds = null) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/chats/${chatId}/sessions`),
      {
        method: 'DELETE',
        body: JSON.stringify(sessionIds ? { ids: sessionIds } : {})
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete sessions');
    }

    return response.json();
  }

  // ==================== 鑱婂ぉ鍔╂墜鏉冮檺鐩稿叧 API ====================

  /**
   * 鑾峰彇鐢ㄦ埛鐨勮亰澶╁姪鎵嬫潈闄愬垪琛紙绠＄悊鍛橈級
   */
  async getUserChats(userId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/chats`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get user chats');
    }

    return response.json();  // { chat_ids: [...] }
  }

  /**
   * 鎺堜簣鐢ㄦ埛鑱婂ぉ鍔╂墜鏉冮檺
   */
  async grantChatAccess(userId, chatId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/chats/${encodeURIComponent(chatId)}`),
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to grant chat access');
    }

    return response.json();
  }

  /**
   * 鎾ら攢鐢ㄦ埛鑱婂ぉ鍔╂墜鏉冮檺
   */
  async revokeChatAccess(userId, chatId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/users/${userId}/chats/${encodeURIComponent(chatId)}`),
      { method: 'DELETE' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to revoke chat access');
    }

    return response.json();
  }

  /**
   * 鎵归噺鎺堟潈澶氫釜鐢ㄦ埛澶氫釜鑱婂ぉ鍔╂墜
   */
  async batchGrantChats(userIds, chatIds) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/users/batch-grant-chats'),
      {
        method: 'POST',
        body: JSON.stringify({ user_ids: userIds, chat_ids: chatIds })
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to batch grant chats');
    }

    return response.json();
  }

  /**
   * 鑾峰彇褰撳墠鐢ㄦ埛鍙闂殑鑱婂ぉ鍔╂墜鍒楄〃
   */
  async getMyChats() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/me/chats'),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get my chats');
    }

    return response.json();  // { chat_ids: [...] }
  }

  // ==================== Agent/鎼滅储浣撶浉鍏?API ====================

  /**
   * 鍒楀嚭鎵€鏈夋悳绱綋
   */
  async listAgents(params = {}) {
    const queryParams = new URLSearchParams(params).toString();
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/agents?${queryParams}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to list agents');
    }

    return response.json();  // { agents: [...], count: N }
  }

  /**
   * 鑾峰彇鍗曚釜鎼滅储浣撹鎯?
   */
  async getAgent(agentId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/agents/${agentId}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get agent');
    }

    return response.json();
  }

  /**
   * 涓庢悳绱綋瀵硅瘽锛堣繑鍥?EventSource 鐢ㄤ簬娴佸紡鍝嶅簲锛?
   */
  createAgentCompletionStream(agentId, question, sessionId = null) {
    const token = localStorage.getItem('access_token');
    if (!token) {
      throw new Error('No access token');
    }

    const url = new URL(authBackendUrl(`/api/agents/${agentId}/completions`));
    url.searchParams.append('question', question);
    if (sessionId) {
      url.searchParams.append('session_id', sessionId);
    }

    return new EventSource(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
  }

  // ==================== 鐭ヨ瘑搴撴绱㈢浉鍏?API ====================

  /**
   * 鍦ㄧ煡璇嗗簱涓绱㈡枃鏈潡
   * @param {Object} searchParams - 鎼滅储鍙傛暟
   * @param {string} searchParams.question - 鏌ヨ闂鎴栧叧閿瘝
   * @param {string[]} searchParams.dataset_ids - 鐭ヨ瘑搴揑D鍒楄〃锛堝彲閫夛紝榛樿浣跨敤鎵€鏈夊彲鐢ㄧ煡璇嗗簱锛?
   * @param {number} searchParams.page - 椤电爜锛岄粯璁?
   * @param {number} searchParams.page_size - 姣忛〉鏁伴噺锛岄粯璁?0
   * @param {number} searchParams.similarity_threshold - 鐩镐技搴﹂槇鍊硷紙0-1锛夛紝榛樿0.2
   * @param {number} searchParams.top_k - 鍚戦噺璁＄畻鍙備笌鐨刢hunk鏁伴噺锛岄粯璁?0
   * @param {boolean} searchParams.keyword - 鏄惁鍚敤鍏抽敭璇嶅尮閰嶏紝榛樿false
   * @param {boolean} searchParams.highlight - 鏄惁楂樹寒鍖归厤璇嶏紝榛樿false
   */
  async searchChunks(searchParams) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/search'),
      {
        method: 'POST',
        body: JSON.stringify(searchParams)
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to search chunks');
    }

    return response.json();  // { chunks: [...], total: N, page: N, page_size: N }
  }

  /**
   * 鑾峰彇褰撳墠鐢ㄦ埛鍙敤鐨勭煡璇嗗簱鍒楄〃
   */
  async getAvailableDatasets() {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/datasets'),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get datasets');
    }

    return response.json();  // { datasets: [...], count: N }
  }

  async listNasFiles(path = '') {
    const query = new URLSearchParams();
    if (path) query.set('path', path);
    const suffix = query.toString() ? `?${query}` : '';
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/nas/files${suffix}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to list NAS files');
    }

    return response.json();
  }

  async importNasFolder(path, kbRef) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/nas/import-folder'),
      {
        method: 'POST',
        body: JSON.stringify({ path, kb_ref: kbRef }),
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to import NAS folder');
    }

    return response.json();
  }

  async getNasFolderImportStatus(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/nas/import-folder/${encodeURIComponent(taskId)}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to get NAS folder import status');
    }

    return response.json();
  }

  async importNasFile(path, kbRef) {
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/nas/import-file'),
      {
        method: 'POST',
        body: JSON.stringify({ path, kb_ref: kbRef }),
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to import NAS file');
    }

    return response.json();
  }
}

const authClient = new AuthClient();
export default authClient;

