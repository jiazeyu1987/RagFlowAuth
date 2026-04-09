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
    runRealRestore: jest.fn(),
  },
}));

const settingsResponse = {
  enabled: true,
  backup_retention_max: 7,
  local_backup_target_path: '/app/data/backups',
  local_backup_pack_count: 2,
  ragflow_compose_path: '/app/ragflow_compose/docker-compose.yml',
  ragflow_stop_services: false,
  full_backup_include_images: true,
  auth_db_path: 'data/auth.db',
};

const createJob = (overrides = {}) => ({
  id: 101,
  kind: 'incremental',
  status: 'completed',
  message: 'backup finished',
  progress: 100,
  package_hash: 'hash-local-101',
  output_dir: '/app/data/backups/migration_pack_20260404_120000',
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

const renderPage = async ({
  settings = settingsResponse,
  jobs = [createJob()],
  drills = [],
  route = '/data-security',
} = {}) => {
  dataSecurityApi.getSettings.mockResolvedValue(settings);
  dataSecurityApi.updateSettings.mockResolvedValue(settings);
  dataSecurityApi.listJobs.mockResolvedValue(jobs);
  dataSecurityApi.listRestoreDrills.mockResolvedValue(drills);
  dataSecurityApi.createRestoreDrill.mockResolvedValue(createRestoreDrill());
  dataSecurityApi.runRealRestore.mockResolvedValue({
    job_id: 101,
    result: 'success',
    live_auth_db_path: '/app/data/auth.db',
  });
  dataSecurityApi.runBackup.mockResolvedValue({ job_id: 101 });
  dataSecurityApi.runFullBackup.mockResolvedValue({ job_id: 101 });
  dataSecurityApi.getJob.mockResolvedValue(jobs[0] || createJob());

  render(
    <MemoryRouter initialEntries={[route]}>
      <DataSecurity />
    </MemoryRouter>
  );

  await screen.findByTestId('data-security-page');
};

describe('DataSecurity', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows only server local backup information on the page', async () => {
    const jobs = [
      createJob(),
      createJob({
        id: 102,
        message: 'missing local output',
        package_hash: 'hash-local-102',
        output_dir: '',
      }),
    ];

    await renderPage({ jobs });

    expect(await screen.findByText('/app/data/backups')).toBeInTheDocument();
    expect(screen.getByTestId('ds-active-job-status')).toHaveTextContent('#101 completed');
    expect(screen.getByTestId('ds-active-job')).toHaveTextContent(
      '/app/data/backups/migration_pack_20260404_120000'
    );
    expect(screen.getByTestId('ds-job-row-102')).toHaveTextContent('missing local output');
    expect(screen.queryByText(/Windows/i)).not.toBeInTheDocument();
  });

  it('submits restore drills only from jobs that have a local backup output_dir', async () => {
    const recoverableJob = createJob({
      id: 201,
      kind: 'full',
      package_hash: 'hash-local-201',
      output_dir: '/app/data/backups/migration_pack_20260405_080000',
    });
    const incompleteJob = createJob({
      id: 202,
      kind: 'full',
      output_dir: '',
      package_hash: 'hash-local-202',
    });
    const user = userEvent.setup();

    await renderPage({ jobs: [recoverableJob, incompleteJob] });

    expect(screen.getByText('恢复演练（仅校验）')).toBeInTheDocument();
    expect(screen.getByTestId('ds-real-restore-submit')).toHaveTextContent('真实恢复当前数据');
    expect(
      screen.getByText(/不会覆盖当前系统数据，也不会恢复已删除的用户/)
    ).toBeInTheDocument();

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

  it('submits real restore only after reason and confirmation prompts', async () => {
    const user = userEvent.setup();
    const promptSpy = jest
      .spyOn(window, 'prompt')
      .mockReturnValueOnce('recover deleted user')
      .mockReturnValueOnce('RESTORE');
    const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

    await renderPage({
      jobs: [
        createJob({
          id: 201,
          kind: 'full',
          package_hash: 'hash-local-201',
          output_dir: '/app/data/backups/migration_pack_20260405_080000',
        }),
      ],
    });

    await user.click(screen.getByTestId('ds-real-restore-submit'));

    await waitFor(() => {
      expect(dataSecurityApi.runRealRestore).toHaveBeenCalledWith({
        job_id: 201,
        backup_path: '/app/data/backups/migration_pack_20260405_080000',
        backup_hash: 'hash-local-201',
        change_reason: 'recover deleted user',
        confirmation_text: 'RESTORE',
      });
    });
    expect(alertSpy).toHaveBeenCalledWith('真实恢复已完成：/app/data/auth.db');

    promptSpy.mockRestore();
    alertSpy.mockRestore();
  });

  it('does not submit real restore when the confirmation prompt is canceled', async () => {
    const user = userEvent.setup();
    const promptSpy = jest
      .spyOn(window, 'prompt')
      .mockReturnValueOnce('recover deleted user')
      .mockReturnValueOnce(null);

    await renderPage();

    await user.click(screen.getByTestId('ds-real-restore-submit'));

    expect(dataSecurityApi.runRealRestore).not.toHaveBeenCalled();

    promptSpy.mockRestore();
  });

  it('disables restore drills when no job has a local backup', async () => {
    const user = userEvent.setup();

    await renderPage({
      jobs: [
        createJob({
          id: 301,
          output_dir: '',
          package_hash: 'hash-local-301',
        }),
      ],
    });

    expect(screen.getByTestId('ds-restore-submit')).toBeDisabled();
    expect(screen.getByTestId('ds-real-restore-submit')).toBeDisabled();
    expect(screen.getByTestId('ds-restore-blocked-reason')).toHaveTextContent(
      '当前没有可用于恢复的服务器本机备份任务'
    );

    await user.click(screen.getByTestId('ds-restore-submit'));

    expect(dataSecurityApi.createRestoreDrill).not.toHaveBeenCalled();
    expect(dataSecurityApi.runRealRestore).not.toHaveBeenCalled();
    expect(screen.queryByTestId('ds-error')).not.toBeInTheDocument();
  });

  it('saves generic backup settings through the auth backend', async () => {
    const user = userEvent.setup();
    const promptSpy = jest
      .spyOn(window, 'prompt')
      .mockReturnValue('switch local backup runtime settings');
    dataSecurityApi.updateSettings.mockResolvedValue({
      ...settingsResponse,
      enabled: false,
      ragflow_compose_path: '/srv/ragflow/docker-compose.yml',
      ragflow_stop_services: true,
      full_backup_include_images: false,
      auth_db_path: 'data/auth.db',
    });

    await renderPage({
      route: '/data-security?advanced=1',
    });

    await user.click(screen.getByTestId('ds-enabled'));
    await user.clear(screen.getByTestId('ds-ragflow-compose-path'));
    await user.type(screen.getByTestId('ds-ragflow-compose-path'), '/srv/ragflow/docker-compose.yml');
    await user.click(screen.getByTestId('ds-ragflow-stop-services'));
    await user.click(screen.getByTestId('ds-full-backup-include-images'));
    await user.click(screen.getByTestId('ds-settings-save'));

    await waitFor(() => {
      expect(dataSecurityApi.updateSettings).toHaveBeenCalledWith({
        enabled: false,
        ragflow_compose_path: '/srv/ragflow/docker-compose.yml',
        ragflow_stop_services: true,
        auth_db_path: 'data/auth.db',
        full_backup_include_images: false,
        change_reason: 'switch local backup runtime settings',
      });
    });

    promptSpy.mockRestore();
  });
});
