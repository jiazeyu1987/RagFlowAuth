import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

const assertObjectPayload = (payload, action) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return payload;
};

const normalizeArrayField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  if (!Array.isArray(envelope[field])) {
    throw new Error(`${action}_invalid_payload`);
  }
  return envelope[field];
};

const normalizeSettings = (payload, action) => {
  const data = assertObjectPayload(payload, action);
  return {
    ...data,
    local_backup_target_path: String(data.local_backup_target_path || ''),
    local_backup_pack_count: Number(data.local_backup_pack_count ?? 0) || 0,
    windows_backup_target_path: String(data.windows_backup_target_path || ''),
    windows_backup_pack_count: Number(data.windows_backup_pack_count ?? 0) || 0,
    windows_backup_pack_count_skipped: Boolean(data.windows_backup_pack_count_skipped),
  };
};

export const dataSecurityApi = {
  getSettings: async () =>
    normalizeSettings(
      await httpClient.requestJson(authBackendUrl('/api/admin/data-security/settings')),
      'data_security_settings_get'
    ),

  updateSettings: async (settings) =>
    normalizeSettings(
      await httpClient.requestJson(authBackendUrl('/api/admin/data-security/settings'), {
        method: 'PUT',
        body: JSON.stringify(settings),
      }),
      'data_security_settings_update'
    ),

  runBackup: async () =>
    assertObjectPayload(
      await httpClient.requestJson(authBackendUrl('/api/admin/data-security/backup/run'), {
        method: 'POST',
        body: JSON.stringify({}),
      }),
      'data_security_backup_run'
    ),

  runFullBackup: async () =>
    assertObjectPayload(
      await httpClient.requestJson(authBackendUrl('/api/admin/data-security/backup/run-full'), {
        method: 'POST',
        body: JSON.stringify({}),
      }),
      'data_security_backup_run_full'
    ),

  listJobs: async (limit = 30) =>
    normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(`/api/admin/data-security/backup/jobs?limit=${encodeURIComponent(limit)}`)
      ),
      'jobs',
      'data_security_jobs_list'
    ),

  getJob: async (jobId) =>
    assertObjectPayload(
      await httpClient.requestJson(
        authBackendUrl(`/api/admin/data-security/backup/jobs/${encodeURIComponent(jobId)}`)
      ),
      'data_security_job_get'
    ),

  listRestoreDrills: async (limit = 30) =>
    normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(`/api/admin/data-security/restore-drills?limit=${encodeURIComponent(limit)}`)
      ),
      'items',
      'data_security_restore_drills_list'
    ),

  createRestoreDrill: async (payload) =>
    assertObjectPayload(
      await httpClient.requestJson(authBackendUrl('/api/admin/data-security/restore-drills'), {
        method: 'POST',
        body: JSON.stringify(payload || {}),
      }),
      'data_security_restore_drill_create'
    ),
};
