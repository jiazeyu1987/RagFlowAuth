import { authBackendUrl } from '../../../config/backend';

const COLLECTION_KIND = 'collection';
const CONTROL_ACTIONS = new Set(['pause', 'resume', 'cancel', 'retry']);

const normalizeDisplayError = (message, fallback) => {
  const text = String(message || '').trim();
  if (!text) return fallback;
  if (/[\u4e00-\u9fff]/.test(text)) return text;
  return fallback;
};

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
  throw new Error(normalizeDisplayError(detail, fallbackMessage));
}

export const policyTasksApiMethods = {
  async getRuntimeFeatureFlags() {
    const response = await this.fetchWithAuth(authBackendUrl('/api/security/feature-flags'), {
      method: 'GET',
    });
    if (!response.ok) {
      await throwResponseError(response, '加载运行时功能开关失败');
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
      await throwResponseError(response, '启动文献采集任务失败');
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
      await throwResponseError(response, '启动专利采集任务失败');
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
      await throwResponseError(response, '获取采集任务列表失败');
    }
    return response.json();
  },

  async getCollectionTaskMetrics() {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/tasks/metrics?kind=${COLLECTION_KIND}`),
      { method: 'GET' }
    );
    if (!response.ok) {
      await throwResponseError(response, '加载采集任务统计失败');
    }
    return response.json();
  },

  async getCollectionTask(taskId) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/tasks/${encodeURIComponent(taskId)}?kind=${COLLECTION_KIND}`),
      { method: 'GET' }
    );
    if (!response.ok) {
      await throwResponseError(response, '加载采集任务详情失败');
    }
    return response.json();
  },

  async controlCollectionTask(taskId, action) {
    const normalizedAction = String(action || '').trim().toLowerCase();
    if (!CONTROL_ACTIONS.has(normalizedAction)) {
      throw new Error(`不支持的任务操作：${normalizedAction}`);
    }
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/tasks/${encodeURIComponent(taskId)}/${normalizedAction}?kind=${COLLECTION_KIND}`),
      { method: 'POST' }
    );
    if (!response.ok) {
      await throwResponseError(response, `采集任务操作失败：${normalizedAction}`);
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
      throw new Error(`不支持的采集任务类型：${kind}`);
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
      await throwResponseError(response, '加入采集结果到本地知识库失败');
    }
    return response.json();
  },
};
