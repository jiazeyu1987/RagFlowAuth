import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const drugAdminApi = {
  listProvinces() {
    return httpClient.requestJson(authBackendUrl('/api/drug-admin/provinces'), {
      method: 'GET',
    });
  },

  resolveProvince(province) {
    return httpClient.requestJson(authBackendUrl('/api/drug-admin/resolve'), {
      method: 'POST',
      body: JSON.stringify({ province: String(province || '') }),
    });
  },

  verifyAll() {
    return httpClient.requestJson(authBackendUrl('/api/drug-admin/verify'), {
      method: 'POST',
    });
  },
};

export default drugAdminApi;
