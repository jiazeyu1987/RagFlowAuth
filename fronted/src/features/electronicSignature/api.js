import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const electronicSignatureApi = {
  requestSignatureChallenge(password) {
    return httpClient.requestJson(authBackendUrl('/api/electronic-signatures/challenge'), {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  },

  listSignatures(params = {}) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      search.set(key, String(value));
    });
    const query = search.toString();
    return httpClient.requestJson(authBackendUrl(`/api/electronic-signatures${query ? `?${query}` : ''}`), {
      method: 'GET',
    });
  },

  getSignature(signatureId) {
    return httpClient.requestJson(authBackendUrl(`/api/electronic-signatures/${signatureId}`), {
      method: 'GET',
    });
  },

  verifySignature(signatureId) {
    return httpClient.requestJson(authBackendUrl(`/api/electronic-signatures/${signatureId}/verify`), {
      method: 'POST',
    });
  },

  listAuthorizations(params = {}) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      search.set(key, String(value));
    });
    const query = search.toString();
    return httpClient.requestJson(authBackendUrl(`/api/electronic-signature-authorizations${query ? `?${query}` : ''}`), {
      method: 'GET',
    });
  },

  updateAuthorization(userId, payload) {
    return httpClient.requestJson(authBackendUrl(`/api/electronic-signature-authorizations/${userId}`), {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },
};
