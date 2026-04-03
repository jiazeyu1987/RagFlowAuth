import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const orgDirectoryApi = {
  getTree() {
    return httpClient.requestJson(authBackendUrl('/api/org/tree'), { method: 'GET' });
  },

  rebuildFromExcel(file) {
    if (!file) {
      throw new Error('org_structure_excel_file_required');
    }
    const formData = new FormData();
    formData.append('excel_file', file);
    return httpClient.requestJson(authBackendUrl('/api/org/rebuild-from-excel'), {
      method: 'POST',
      body: formData,
      includeContentType: false,
    });
  },

  listCompanies() {
    return httpClient.requestJson(authBackendUrl('/api/org/companies'), { method: 'GET' });
  },

  createCompany(name) {
    return httpClient.requestJson(authBackendUrl('/api/org/companies'), {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  updateCompany(companyId, name) {
    return httpClient.requestJson(authBackendUrl(`/api/org/companies/${companyId}`), {
      method: 'PUT',
      body: JSON.stringify({ name }),
    });
  },

  deleteCompany(companyId) {
    return httpClient.requestJson(authBackendUrl(`/api/org/companies/${companyId}`), {
      method: 'DELETE',
    });
  },

  listDepartments() {
    return httpClient.requestJson(authBackendUrl('/api/org/departments'), { method: 'GET' });
  },

  createDepartment(name) {
    return httpClient.requestJson(authBackendUrl('/api/org/departments'), {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  updateDepartment(departmentId, name) {
    return httpClient.requestJson(authBackendUrl(`/api/org/departments/${departmentId}`), {
      method: 'PUT',
      body: JSON.stringify({ name }),
    });
  },

  deleteDepartment(departmentId) {
    return httpClient.requestJson(authBackendUrl(`/api/org/departments/${departmentId}`), {
      method: 'DELETE',
    });
  },

  listAudit(params = {}) {
    const query = new URLSearchParams(params).toString();
    const path = query ? `/api/org/audit?${query}` : '/api/org/audit';
    return httpClient.requestJson(authBackendUrl(path), { method: 'GET' });
  },
};
