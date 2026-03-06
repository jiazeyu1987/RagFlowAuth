import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

class DrugAdminManager {
  async listProvinces() {
    return httpClient.requestJson(authBackendUrl('/api/drug-admin/provinces'), { method: 'GET' });
  }

  async resolveProvince(province) {
    return httpClient.requestJson(authBackendUrl('/api/drug-admin/resolve'), {
      method: 'POST',
      body: JSON.stringify({ province: String(province || '') }),
    });
  }

  async verifyAll() {
    return httpClient.requestJson(authBackendUrl('/api/drug-admin/verify'), {
      method: 'POST',
    });
  }
}

const drugAdminManager = new DrugAdminManager();
export default drugAdminManager;

