import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DataSecurity from './DataSecurity';
import { dataSecurityApi } from '../features/dataSecurity/api';

jest.mock('../features/dataSecurity/api', () => ({
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
  backup_target_path: '/app/data/backups',
  local_backup_pack_count: 2,
  windows_backup_target_path: '/mnt/replica/RagflowAuth',
  windows_backup_pack_count: 1,
  windows_backup_pack_count_skipped: false,
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

const createRestoreDrill = (overrides = {}) => ({
  drill_id: 'drill-1',
  job_id: 101,
  result: 'passed',
  restore_target: 'staging',
  executed_by: 'tester',
  executed_at_ms: 1_775_270_500_000,
  backup_path: '/app/data/backups/migration_pack_20260404_120000',
  backup_hash: 'hash-local-101',
  package_validation_status: 'passed',
  acceptance_status: 'passed',
  hash_match: true,
  compare_match: true,
  verification_notes: '',
  ...overrides,
});

const renderPage = async ({ settings = settingsResponse, jobs = [createJob()], drills = [] } = {}) => {
  dataSecurityApi.getSettings.mockResolvedValue(settings);
  dataSecurityApi.listJobs.mockResolvedValue({ jobs });
  dataSecurityApi.listRestoreDrills.mockResolvedValue({ items: drills });
  dataSecurityApi.createRestoreDrill.mockResolvedValue(createRestoreDrill());
  dataSecurityApi.runBackup.mockResolvedValue({ job_id: 101 });
  dataSecurityApi.runFullBackup.mockResolvedValue({ job_id: 101 });
  dataSecurityApi.getJob.mockResolvedValue(jobs[0] || null);

  render(
    <MemoryRouter>
      <DataSecurity />
    </MemoryRouter>
  );

  await screen.findByTestId('data-security-page');
};

describe('DataSecurity', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows separate local and Windows backup destinations with split job statuses', async () => {
    const jobs = [
      createJob(),
      createJob({
        id: 102,
        message: 'windows only backup',
        package_hash: 'hash-remote-102',
        output_dir: '',
        replica_path: '/mnt/replica/RagflowAuth/migration_pack_20260403_235959',
        replication_status: 'succeeded',
      }),
    ];

    await renderPage({ jobs });

    expect(await screen.findByText('/app/data/backups')).toBeInTheDocument();
    expect(screen.getByText('/mnt/replica/RagflowAuth')).toBeInTheDocument();
    expect(screen.getByTestId('ds-active-job-status')).toHaveTextContent('#101 completed');
    expect(screen.getByTestId('ds-active-job')).toHaveTextContent('/app/data/backups/migration_pack_20260404_120000');
    expect(screen.getByTestId('ds-active-job')).toHaveTextContent('windows share unavailable');
    expect(screen.getByTestId('ds-job-row-102')).toHaveTextContent('/mnt/replica/RagflowAuth/migration_pack_20260403_235959');
  });

  it('submits restore drills only from jobs that have a local backup output_dir', async () => {
    const recoverableJob = createJob({
      id: 201,
      kind: 'full',
      package_hash: 'hash-local-201',
      output_dir: '/app/data/backups/migration_pack_20260405_080000',
    });
    const windowsOnlyJob = createJob({
      id: 202,
      kind: 'full',
      output_dir: '',
      package_hash: 'hash-remote-202',
      replica_path: '/mnt/replica/RagflowAuth/migration_pack_20260405_080000',
      replication_status: 'succeeded',
    });
    const user = userEvent.setup();

    await renderPage({ jobs: [recoverableJob, windowsOnlyJob] });

    const select = screen.getByTestId('ds-restore-job-select');
    expect(within(select).getByRole('option', { name: '#201 full completed' })).toBeInTheDocument();
    expect(within(select).queryByRole('option', { name: '#202 full completed' })).not.toBeInTheDocument();

    await user.clear(screen.getByTestId('ds-restore-target'));
    await user.type(screen.getByTestId('ds-restore-target'), 'qa-staging');
    await user.type(screen.getByTestId('ds-restore-notes'), 'local-only drill');
    await user.click(screen.getByTestId('ds-restore-submit'));

    await waitFor(() => {
      expect(dataSecurityApi.createRestoreDrill).toHaveBeenCalledWith({
        job_id: 201,
        backup_path: '/app/data/backups/migration_pack_20260405_080000',
        backup_hash: 'hash-local-201',
        restore_target: 'qa-staging',
        verification_notes: 'local-only drill',
      });
    });
  });

  it('blocks restore drills when no job has a local backup', async () => {
    const user = userEvent.setup();

    await renderPage({
      jobs: [
        createJob({
          id: 301,
          output_dir: '',
          package_hash: 'hash-remote-301',
          replica_path: '/mnt/replica/RagflowAuth/migration_pack_20260406_010000',
          replication_status: 'succeeded',
        }),
      ],
    });

    await user.click(screen.getByTestId('ds-restore-submit'));

    expect(dataSecurityApi.createRestoreDrill).not.toHaveBeenCalled();
    expect(await screen.findByTestId('ds-error')).toHaveTextContent('可用于本地恢复演练');
  });
});
