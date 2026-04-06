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
};

export default trainingComplianceApi;
