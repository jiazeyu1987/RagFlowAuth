import { dataSecurityApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('dataSecurityApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('routes settings and backup actions through the auth backend base url', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ enabled: true, local_backup_target_path: '/app/data/backups' })
      .mockResolvedValueOnce({ enabled: false, windows_backup_target_path: '/mnt/replica/RagflowAuth' })
      .mockResolvedValueOnce({ job_id: 101 })
      .mockResolvedValueOnce({ job_id: 102 });

    await expect(dataSecurityApi.getSettings()).resolves.toEqual({
      enabled: true,
      local_backup_target_path: '/app/data/backups',
      local_backup_pack_count: 0,
      windows_backup_target_path: '',
      windows_backup_pack_count: 0,
      windows_backup_pack_count_skipped: false,
    });
    await expect(dataSecurityApi.updateSettings({ enabled: false })).resolves.toEqual({
      enabled: false,
      local_backup_target_path: '',
      local_backup_pack_count: 0,
      windows_backup_target_path: '/mnt/replica/RagflowAuth',
      windows_backup_pack_count: 0,
      windows_backup_pack_count_skipped: false,
    });
    await expect(dataSecurityApi.runBackup()).resolves.toEqual({ job_id: 101 });
    await expect(dataSecurityApi.runFullBackup()).resolves.toEqual({ job_id: 102 });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/admin/data-security/settings'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/admin/data-security/settings',
      {
        method: 'PUT',
        body: JSON.stringify({ enabled: false }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/admin/data-security/backup/run',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/admin/data-security/backup/run-full',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
  });

  it('encodes path and query parameters for job and restore drill endpoints', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ jobs: [] })
      .mockResolvedValueOnce({ id: 'job/1' })
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ drill_id: 'drill-1' });

    await expect(dataSecurityApi.listJobs('30&all=true')).resolves.toEqual([]);
    await expect(dataSecurityApi.getJob('job/1')).resolves.toEqual({ id: 'job/1' });
    await expect(dataSecurityApi.listRestoreDrills('20&kind=all')).resolves.toEqual([]);
    await expect(dataSecurityApi.createRestoreDrill({ job_id: 1 })).resolves.toEqual({ drill_id: 'drill-1' });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/admin/data-security/backup/jobs?limit=30%26all%3Dtrue'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/admin/data-security/backup/jobs/job%2F1'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/admin/data-security/restore-drills?limit=20%26kind%3Dall'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/admin/data-security/restore-drills',
      {
        method: 'POST',
        body: JSON.stringify({ job_id: 1 }),
      }
    );
  });

  it('fails fast when list or settings payloads are invalid', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce([]);

    await expect(dataSecurityApi.getSettings()).rejects.toThrow('data_security_settings_get_invalid_payload');
    await expect(dataSecurityApi.listJobs(30)).rejects.toThrow('data_security_jobs_list_invalid_payload');
    await expect(dataSecurityApi.createRestoreDrill({ job_id: 1 })).rejects.toThrow(
      'data_security_restore_drill_create_invalid_payload'
    );
  });
});
