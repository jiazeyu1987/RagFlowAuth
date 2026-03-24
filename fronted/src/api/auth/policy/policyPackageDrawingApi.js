import { authBackendUrl } from '../../../config/backend';

export const policyPackageDrawingApiMethods = {
  async queryPackageDrawingByModel(model) {
    const response = await this.fetchWithAuth(
      authBackendUrl(`/api/package-drawing/by-model?model=${encodeURIComponent(String(model || '').trim())}`),
      { method: 'GET' }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to query package drawing');
    }

    return response.json();
  },

  async importPackageDrawingExcel(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.fetchWithAuth(
      authBackendUrl('/api/package-drawing/import'),
      {
        method: 'POST',
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to import package drawing excel');
    }

    return response.json();
  },
};
