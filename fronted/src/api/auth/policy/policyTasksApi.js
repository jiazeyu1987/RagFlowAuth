import { authBackendUrl } from '../../../config/backend';

const COLLECTION_KIND = 'collection';
const CONTROL_ACTIONS = new Set(['pause', 'resume', 'cancel', 'retry']);

async function throwResponseError(response, fallbackMessage) {
  let detail = '';
  try {
    const payload = await response.json();
    if (typeof payload?.detail === 'string') {
      detail = payload.detail;
    } else if (typeof payload?.message === 'string') {
      detail = payload.message;
    }
  } catch (_err) {
    detail = '';
  }
  throw new Error(detail || fallbackMessage);
}

export const policyTasksApiMethods = {
  async getRuntimeFeatureFlags() {
    const response = await this.fetchWithAuth(authBackendUrl('/api/security/feature-flags'), {
      method: 'GET',
    });
    if (!response.ok) {
      await throwResponseError(response, 'Failed to load runtime feature flags');
    }
    return response.json();
  },

  async startPaperCollectionTask({ keywordText = '', useAnd = true, autoAnalyze = false, sources = {} } = {}) {
    const response = await this.fetchWithAuth(authBackendUrl('/api/paper-download/sessions'), {
      method: 'POST',
      body: JSON.stringify({
        keyword_text: String(keywordText || ''),
        use_and: Boolean(useAnd),
        auto_analyze: Boolean(autoAnalyze),
        sources: sources && typeof sources === 'object' ? sources : {},
      }),
    });
    if (!response.ok) {
      await throwResponseError(response, 'Failed to start paper collection task');
    }
    return response.json();
  },

  async startPatentCollectionTask({ keywordText = '', useAnd = true, autoAnalyze = false, sources = {} } = {}) {
    const response = await this.fetchWithAuth(authBackendUrl('/api/patent-download/sessions'), {
      method: 'POST',
      body: JSON.stringify({
        keyword_text: String(keywordText || ''),
        use_and: Boolean(useAnd),
        auto_analyze: Boolean(autoAnalyze),
        sources: sources && typeof sources === 'object' ? sources : {},
      }),
    });
    if (!response.ok) {
      await throwResponseError(response, 'Failed to start patent collection task');
    }
    return response.json();
  },

  async listCollectionTasks({ status = '', limit = 200 } = {}) {
    const query = new URLSearchParams({
      kind: COLLECTION_KIND,
      limit: String(Math.max(1, Math.min(Number(limit) || 200, 200))),
    });
    if (String(status || '').trim()) {
      query.set('status', String(status).trim());
    }

    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/tasks?${query.toString()}`),
      { method: 'GET' }
    );
    if (!response.ok) {
      await throwResponseError(response, 'Failed to list collection tasks');
    }
    return response.json();
  },

  async getCollectionTaskMetrics() {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/tasks/metrics?kind=${COLLECTION_KIND}`),
      { method: 'GET' }
    );
    if (!response.ok) {
      await throwResponseError(response, 'Failed to load collection task metrics');
    }
    return response.json();
  },

  async getCollectionTask(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/tasks/${encodeURIComponent(taskId)}?kind=${COLLECTION_KIND}`),
      { method: 'GET' }
    );
    if (!response.ok) {
      await throwResponseError(response, 'Failed to load collection task');
    }
    return response.json();
  },

  async controlCollectionTask(taskId, action) {
    const normalizedAction = String(action || '').trim().toLowerCase();
    if (!CONTROL_ACTIONS.has(normalizedAction)) {
      throw new Error(`Unsupported task action: ${normalizedAction}`);
    }
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/tasks/${encodeURIComponent(taskId)}/${normalizedAction}?kind=${COLLECTION_KIND}`),
      { method: 'POST' }
    );
    if (!response.ok) {
      await throwResponseError(response, `Failed to ${normalizedAction} collection task`);
    }
    return response.json();
  },

  async pauseCollectionTask(taskId) {
    return this.controlCollectionTask(taskId, 'pause');
  },

  async resumeCollectionTask(taskId) {
    return this.controlCollectionTask(taskId, 'resume');
  },

  async cancelCollectionTask(taskId) {
    return this.controlCollectionTask(taskId, 'cancel');
  },

  async retryCollectionTask(taskId) {
    return this.controlCollectionTask(taskId, 'retry');
  },

  async addCollectionTaskToLocalKb(taskId, taskKind, kbRef = '') {
    const kind = String(taskKind || '').trim().toLowerCase();
    const encodedTaskId = encodeURIComponent(taskId);
    const endpoint =
      kind === 'paper_download'
        ? `/api/paper-download/sessions/${encodedTaskId}/add-all-to-local-kb`
        : kind === 'patent_download'
          ? `/api/patent-download/sessions/${encodedTaskId}/add-all-to-local-kb`
          : '';

    if (!endpoint) {
      throw new Error(`Unsupported collection task kind: ${kind}`);
    }

    const payload = {};
    if (String(kbRef || '').trim()) {
      payload.kb_ref = String(kbRef).trim();
    }

    const response = await this.fetchWithAuth(authBackendUrl(endpoint), {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      await throwResponseError(response, 'Failed to add collection results to local KB');
    }
    return response.json();
  },
};
