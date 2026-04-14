import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const assertObjectPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const normalizeArrayField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!Array.isArray(envelope[field])) {
    throw new Error(`${action}_invalid_payload`);
  }
  return envelope[field];
};

const normalizeObjectField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  const value = envelope[field];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

const buildQuery = (params = {}) => {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  const text = search.toString();
  return text ? `?${text}` : '';
};

export const batchRecordsApi = {
  async listTemplates(params = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/batch-records/templates${buildQuery({
            include_versions: params.includeVersions ? 'true' : undefined,
            include_obsolete: params.includeObsolete ? 'true' : undefined,
            limit: params.limit ?? 100,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'batch_records_templates_list'
    );
  },

  async getTemplate(templateId) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/batch-records/templates/${templateId}`),
        { method: 'GET' }
      ),
      'template',
      'batch_records_template_get'
    );
  },

  async createTemplate(payload) {
    return normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/quality-system/batch-records/templates'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'template',
      'batch_records_template_create'
    );
  },

  async createTemplateVersion(templateCode, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/batch-records/templates/${encodeURIComponent(templateCode)}/versions`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'template',
      'batch_records_template_version_create'
    );
  },

  async publishTemplate(templateId) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/batch-records/templates/${templateId}/publish`),
        { method: 'POST' }
      ),
      'template',
      'batch_records_template_publish'
    );
  },

  async listExecutions(params = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/quality-system/batch-records/executions${buildQuery({
            status: params.status,
            template_code: params.templateCode,
            batch_no: params.batchNo,
            limit: params.limit ?? 100,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'batch_records_executions_list'
    );
  },

  async createExecution(payload) {
    return normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/quality-system/batch-records/executions'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'bundle',
      'batch_records_execution_create'
    );
  },

  async getExecution(executionId) {
    return assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/batch-records/executions/${executionId}`),
        { method: 'GET' }
      ),
      'batch_records_execution_get'
    );
  },

  async writeStep(executionId, payload) {
    return assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/batch-records/executions/${executionId}/steps`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'batch_records_step_write'
    );
  },

  async signExecution(executionId, payload) {
    return assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/batch-records/executions/${executionId}/sign`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'batch_records_execution_sign'
    );
  },

  async reviewExecution(executionId, payload) {
    return assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/batch-records/executions/${executionId}/review`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'batch_records_execution_review'
    );
  },

  async exportExecution(executionId) {
    return assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/quality-system/batch-records/executions/${executionId}/export`),
        { method: 'POST' }
      ),
      'batch_records_execution_export'
    );
  },
};

export default batchRecordsApi;

