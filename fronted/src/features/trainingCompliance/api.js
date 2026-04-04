import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

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
  listRequirements({ limit = 100, controlledAction, roleCode } = {}) {
    return httpClient.requestJson(
      authBackendUrl(
        `/api/training-compliance/requirements${buildQuery({
          limit,
          controlled_action: controlledAction,
          role_code: roleCode,
        })}`
      ),
      { method: 'GET' }
    );
  },

  createRecord(payload) {
    return httpClient.requestJson(authBackendUrl('/api/training-compliance/records'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  },

  listRecords({ limit = 100, requirementCode, userId } = {}) {
    return httpClient.requestJson(
      authBackendUrl(
        `/api/training-compliance/records${buildQuery({
          limit,
          requirement_code: requirementCode,
          user_id: userId,
        })}`
      ),
      { method: 'GET' }
    );
  },

  createCertification(payload) {
    return httpClient.requestJson(authBackendUrl('/api/training-compliance/certifications'), {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    });
  },

  listCertifications({ limit = 100, requirementCode, userId } = {}) {
    return httpClient.requestJson(
      authBackendUrl(
        `/api/training-compliance/certifications${buildQuery({
          limit,
          requirement_code: requirementCode,
          user_id: userId,
        })}`
      ),
      { method: 'GET' }
    );
  },
};

export default trainingComplianceApi;
