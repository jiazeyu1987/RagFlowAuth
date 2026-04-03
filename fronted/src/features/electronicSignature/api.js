import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const electronicSignatureApi = {
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
};
