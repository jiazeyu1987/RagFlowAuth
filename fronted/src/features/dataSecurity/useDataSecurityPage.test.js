import { act, renderHook, waitFor } from '@testing-library/react';
import useDataSecurityPage from './useDataSecurityPage';
import { dataSecurityApi } from './api';

jest.mock('./api', () => ({
  dataSecurityApi: {
    getSettings: jest.fn(),
    updateSettings: jest.fn(),
    runBackup: jest.fn(),
    runFullBackup: jest.fn(),
    listJobs: jest.fn(),
    getJob: jest.fn(),
    listRestoreDrills: jest.fn(),
    createRestoreDrill: jest.fn(),
  },
}));

const settingsResponse = {
  enabled: true,
  backup_retention_max: 7,
  local_backup_target_path: '/app/data/backups',
  windows_backup_target_path: '/mnt/replica/RagflowAuth',
  target_mode: 'share',
  target_ip: '10.0.0.8',
  target_share_name: 'BackupShare',
  target_subdir: 'RagflowAuth',
};

const createJob = (overrides = {}) => ({
  id: 101,
  kind: 'incremental',
  status: 'completed',
  message: 'backup finished',
  progress: 100,
  package_hash: 'hash-local-101',
  output_dir: '/app/data/backups/migration_pack_20260404_120000',
  replica_path: '',
  replication_status: 'failed',
  replication_error: 'windows share unavailable',
  created_at_ms: 1_775_270_400_000,
  started_at_ms: 1_775_270_300_000,
  detail: '',
  ...overrides,
});

describe('useDataSecurityPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    dataSecurityApi.getSettings.mockResolvedValue(settingsResponse);
    dataSecurityApi.listJobs.mockResolvedValue({ jobs: [createJob()] });
    dataSecurityApi.listRestoreDrills.mockResolvedValue({ items: [] });
    dataSecurityApi.createRestoreDrill.mockResolvedValue({
      drill_id: 'drill-1',
      job_id: 101,
      result: 'passed',
    });
  });

  it('loads settings, jobs, and restore options into stable hook state', async () => {
    const { result } = renderHook(() => useDataSecurityPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(dataSecurityApi.getSettings).toHaveBeenCalledTimes(1);
    expect(dataSecurityApi.listJobs).toHaveBeenCalledWith(30);
    expect(dataSecurityApi.listRestoreDrills).toHaveBeenCalledWith(30);
    expect(result.current.localBackupTargetPath).toBe('/app/data/backups');
    expect(result.current.windowsBackupTargetPath).toBe('/mnt/replica/RagflowAuth');
    expect(result.current.restoreEligibleJobs).toHaveLength(1);
    expect(result.current.selectedRestoreJobId).toBe('101');
  });

  it('submits restore drills through the feature api using the selected local backup', async () => {
    const { result } = renderHook(() => useDataSecurityPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      result.current.setRestoreTarget('qa-staging');
      result.current.setRestoreNotes('local-only drill');
    });

    await act(async () => {
      await result.current.submitRestoreDrill();
    });

    expect(dataSecurityApi.createRestoreDrill).toHaveBeenCalledWith({
      job_id: 101,
      backup_path: '/app/data/backups/migration_pack_20260404_120000',
      backup_hash: 'hash-local-101',
      restore_target: 'qa-staging',
      verification_notes: 'local-only drill',
    });
  });
});
