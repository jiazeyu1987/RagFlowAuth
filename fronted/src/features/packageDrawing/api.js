import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const packageDrawingApi = {
  queryByModel(model) {
    const query = new URLSearchParams({
      model: String(model || '').trim(),
    }).toString();
    return httpClient.requestJson(authBackendUrl(`/api/package-drawing/by-model?${query}`), {
      method: 'GET',
    });
  },

  importExcel(file) {
    const formData = new FormData();
    formData.append('file', file);

    return httpClient.requestJson(authBackendUrl('/api/package-drawing/import'), {
      method: 'POST',
      body: formData,
    });
  },
};

export default packageDrawingApi;
