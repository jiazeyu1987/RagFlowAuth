import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';
import { extractFilenameFromContentDisposition, triggerBlobDownload } from '../../api/auth/policy/policyDownloadUtils';

const encode = (value) => encodeURIComponent(String(value || '').trim());

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

async function parseErrorMessage(response) {
  try {
    const data = await response.json();
    if (typeof data?.detail === 'string' && data.detail.trim()) return data.detail;
    if (typeof data?.message === 'string' && data.message.trim()) return data.message;
    if (typeof data?.error === 'string' && data.error.trim()) return data.error;
  } catch (_err) {
    // no-op
  }
  return `请求失败（${response.status}）`;
}

export const paperPlagApi = {
  saveVersion(paperId, payload) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-plag/papers/${encode(paperId)}/versions/save`), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listVersions(paperId, limit = 50) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-plag/papers/${encode(paperId)}/versions${buildQuery({ limit })}`), {
      method: 'GET',
    });
  },

  getVersion(paperId, versionId) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-plag/papers/${encode(paperId)}/versions/${encode(versionId)}`), {
      method: 'GET',
    });
  },

  diffVersions(paperId, fromVersionId, toVersionId) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-plag/papers/${encode(paperId)}/versions/diff`), {
      method: 'POST',
      body: JSON.stringify({ from_version_id: fromVersionId, to_version_id: toVersionId }),
    });
  },

  rollbackVersion(paperId, versionId, note = null) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-plag/papers/${encode(paperId)}/versions/${encode(versionId)}/rollback`), {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
  },

  startReport(payload) {
    return httpClient.requestJson(authBackendUrl('/api/paper-plag/reports/start'), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listReports({ paperId = '', status = '', limit = 50 } = {}) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-plag/reports${buildQuery({ paper_id: paperId, status, limit })}`), {
      method: 'GET',
    });
  },

  getReport(reportId) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-plag/reports/${encode(reportId)}`), {
      method: 'GET',
    });
  },

  cancelReport(reportId) {
    return httpClient.requestJson(authBackendUrl(`/api/paper-plag/reports/${encode(reportId)}/cancel`), {
      method: 'POST',
    });
  },

  async exportReport(reportId, format = 'md') {
    const response = await httpClient.request(authBackendUrl(`/api/paper-plag/reports/${encode(reportId)}/export${buildQuery({ format })}`), {
      method: 'GET',
    });
    if (!response.ok) {
      const message = await parseErrorMessage(response);
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }

    const blob = await response.blob();
    const contentDisposition = response.headers.get('content-disposition') || '';
    const fallbackName = `论文查重报告_${String(reportId || '').trim() || '最新'}.${format === 'txt' ? 'txt' : 'md'}`;
    const filename = extractFilenameFromContentDisposition(contentDisposition, fallbackName);
    triggerBlobDownload(blob, filename);
    return {
      filename,
      size: blob.size,
      type: blob.type,
    };
  },
};
