import { authBackendUrl } from '../../../config/backend';

export const policyNasApiMethods = {
  async listNasFiles(path = '') {
    const query = new URLSearchParams();
    if (path) {
      query.set('path', path);
    }
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
  },

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
  },

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
  },

  async cancelNasFolderImport(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/nas/import-folder/${encodeURIComponent(taskId)}/cancel`),
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to cancel NAS folder import');
    }

    return response.json();
  },

  async retryNasFolderImport(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/nas/import-folder/${encodeURIComponent(taskId)}/retry`),
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to retry NAS folder import');
    }

    return response.json();
  },

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
  },
};
