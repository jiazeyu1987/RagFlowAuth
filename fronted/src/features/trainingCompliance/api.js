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

export const trainingComplianceApi = {
  async listRequirements({ limit = 100, controlledAction, roleCode } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/training-compliance/requirements${buildQuery({
            limit,
            controlled_action: controlledAction,
            role_code: roleCode,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'training_compliance_requirements_list'
    );
  },

  async createRecord(payload) {
    return normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/training-compliance/records'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'record',
      'training_compliance_record_create'
    );
  },

  async listRecords({ limit = 100, requirementCode, userId } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/training-compliance/records${buildQuery({
            limit,
            requirement_code: requirementCode,
            user_id: userId,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'training_compliance_records_list'
    );
  },

  async createCertification(payload) {
    return normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/training-compliance/certifications'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'certification',
      'training_compliance_certification_create'
    );
  },

  async listCertifications({ limit = 100, requirementCode, userId } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/training-compliance/certifications${buildQuery({
            limit,
            requirement_code: requirementCode,
            user_id: userId,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'training_compliance_certifications_list'
    );
  },

  async listEffectiveRevisions({ limit = 100 } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(`/api/training-compliance/effective-revisions${buildQuery({ limit })}`),
        { method: 'GET' }
      ),
      'items',
      'training_compliance_effective_revisions_list'
    );
  },

  async listTrainableRevisions({ limit = 100 } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(`/api/training-compliance/trainable-revisions${buildQuery({ limit })}`),
        { method: 'GET' }
      ),
      'items',
      'training_compliance_trainable_revisions_list'
    );
  },

  async getRevisionGate(controlledRevisionId) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/training-compliance/revisions/${encodeURIComponent(controlledRevisionId)}/gate`),
        { method: 'GET' }
      ),
      'gate',
      'training_compliance_revision_gate_get'
    );
  },

  async upsertRevisionGate(controlledRevisionId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/training-compliance/revisions/${encodeURIComponent(controlledRevisionId)}/gate`),
        {
          method: 'PUT',
          body: JSON.stringify(payload || {}),
        }
      ),
      'gate',
      'training_compliance_revision_gate_upsert'
    );
  },

  async generateAssignments(payload) {
    return normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/training-compliance/assignments/generate'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'items',
      'training_compliance_assignments_generate'
    );
  },

  async listAssignments({ limit = 100, status } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/training-compliance/assignments${buildQuery({
            limit,
            status,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'training_compliance_assignments_list'
    );
  },

  async acknowledgeAssignment(assignmentId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/training-compliance/assignments/${encodeURIComponent(assignmentId)}/acknowledge`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'assignment',
      'training_compliance_assignment_acknowledge'
    );
  },

  async recordReadProgress(assignmentId, payload = {}) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/training-compliance/assignments/${encodeURIComponent(assignmentId)}/read-progress`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'assignment',
      'training_compliance_assignment_read_progress'
    );
  },

  async listQuestionThreads({ limit = 100, status } = {}) {
    return normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/training-compliance/question-threads${buildQuery({
            limit,
            status,
          })}`
        ),
        { method: 'GET' }
      ),
      'items',
      'training_compliance_question_threads_list'
    );
  },

  async resolveQuestionThread(threadId, payload) {
    return normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/training-compliance/question-threads/${encodeURIComponent(threadId)}/resolve`),
        {
          method: 'POST',
          body: JSON.stringify(payload || {}),
        }
      ),
      'thread',
      'training_compliance_question_thread_resolve'
    );
  },
};

export default trainingComplianceApi;
