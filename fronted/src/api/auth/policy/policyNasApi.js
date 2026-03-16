import { authBackendUrl } from '../../../config/backend';

const TASK_KIND_QUERY = 'kind=nas_import';

function taskControlPath(taskId, action = '') {
  const encodedId = encodeURIComponent(taskId);
  const actionSuffix = action ? `/${action}` : '';
  return `/api/tasks/${encodedId}${actionSuffix}?${TASK_KIND_QUERY}`;
}

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
      throw new Error(this.resolveErrorMessage(error, '获取 NAS 文件列表失败'));
    }

    return response.json();
  },

  async importNasFolder(path, kbRef, priority = null) {
    const payload = { path, kb_ref: kbRef };
    if (Number.isFinite(priority)) {
      payload.priority = Number(priority);
    }
    const response = await this.fetchWithAuth(
      authBackendUrl('/api/nas/import-folder'),
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(this.resolveErrorMessage(error, '导入 NAS 文件夹失败'));
    }

    return response.json();
  },

  async getNasFolderImportStatus(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(taskControlPath(taskId)),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(this.resolveErrorMessage(error, '获取 NAS 文件夹导入状态失败'));
    }

    return response.json();
  },

  async cancelNasFolderImport(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(taskControlPath(taskId, 'cancel')),
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(this.resolveErrorMessage(error, '取消 NAS 文件夹导入失败'));
    }

    return response.json();
  },

  async pauseNasFolderImport(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(taskControlPath(taskId, 'pause')),
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(this.resolveErrorMessage(error, '暂停 NAS 文件夹导入失败'));
    }

    return response.json();
  },

  async resumeNasFolderImport(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(taskControlPath(taskId, 'resume')),
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(this.resolveErrorMessage(error, '继续 NAS 文件夹导入失败'));
    }

    return response.json();
  },

  async retryNasFolderImport(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(taskControlPath(taskId, 'retry')),
      { method: 'POST' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(this.resolveErrorMessage(error, '重试 NAS 文件夹导入失败'));
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
      throw new Error(this.resolveErrorMessage(error, '导入 NAS 文件失败'));
    }

    return response.json();
  },
};
