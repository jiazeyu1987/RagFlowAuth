import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const auditApi = {
  listEvents(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/audit/events?${query}` : '/api/audit/events';
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },
};

