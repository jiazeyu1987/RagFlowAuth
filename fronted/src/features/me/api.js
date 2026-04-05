import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const meApi = {
  listMyKnowledgeBases() {
    return httpClient.requestJson(authBackendUrl('/api/me/kbs'), { method: 'GET' });
  },
};

export default meApi;
