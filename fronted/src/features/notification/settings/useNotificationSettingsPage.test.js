import { act, renderHook, waitFor } from '@testing-library/react';
import useNotificationSettingsPage from './useNotificationSettingsPage';
import { notificationApi } from '../api';

jest.mock('../api', () => ({
  notificationApi: {
    listChannels: jest.fn(),
    upsertChannel: jest.fn(),
    listRules: jest.fn(),
    upsertRules: jest.fn(),
    listJobs: jest.fn(),
    listJobLogs: jest.fn(),
    retryJob: jest.fn(),
    resendJob: jest.fn(),
    dispatchPending: jest.fn(),
  },
}));

describe('useNotificationSettingsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    notificationApi.listChannels.mockResolvedValue({
      items: [
        {
          channel_id: 'email-main',
          channel_type: 'email',
          name: '邮件通知',
          enabled: true,
          updated_at_ms: 1710000000000,
          config: { host: 'smtp.example.com', from_email: 'noreply@example.com', use_tls: true },
        },
        {
          channel_id: 'inapp-main',
          channel_type: 'in_app',
          name: '站内信',
          enabled: true,
          updated_at_ms: 1710000000000,
          config: {},
        },
      ],
    });
    notificationApi.listRules.mockResolvedValue({
      groups: [
        {
          group_key: 'operation_approval',
          group_label: '操作审批',
          items: [
            {
              event_type: 'operation_approval_todo',
              event_label: '审批待处理',
              enabled_channel_types: ['in_app'],
              has_enabled_channel_config_by_type: { email: true, dingtalk: false, in_app: true },
            },
          ],
        },
      ],
    });
    notificationApi.listJobs.mockResolvedValue({
      items: [
        {
          job_id: 11,
          channel_id: 'email-main',
          channel_type: 'email',
          event_type: 'operation_approval_todo',
          status: 'queued',
          created_at_ms: 1710000000000,
        },
      ],
    });
    notificationApi.listJobLogs.mockResolvedValue({
      items: [{ id: 1, status: 'queued', attempted_at_ms: 1710000000000, error: null }],
    });
    notificationApi.upsertChannel.mockResolvedValue({});
    notificationApi.upsertRules.mockResolvedValue({
      groups: [
        {
          group_key: 'operation_approval',
          group_label: '操作审批',
          items: [
            {
              event_type: 'operation_approval_todo',
              event_label: '审批待处理',
              enabled_channel_types: ['dingtalk', 'in_app'],
              has_enabled_channel_config_by_type: { email: true, dingtalk: true, in_app: true },
            },
          ],
        },
      ],
    });
  });

  it('loads channel forms, rules, and history into stable hook state', async () => {
    const { result } = renderHook(() => useNotificationSettingsPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(notificationApi.listChannels).toHaveBeenCalledWith(false);
    expect(notificationApi.listRules).toHaveBeenCalledTimes(1);
    expect(notificationApi.listJobs).toHaveBeenCalledWith({
      limit: 100,
      eventType: '',
      channelType: '',
      status: '',
    });
    expect(result.current.forms.email.host).toBe('smtp.example.com');
    expect(result.current.forms.dingtalk.agent_id).toBe('4432005762');
    expect(result.current.ruleItems).toHaveLength(1);
    expect(result.current.eventLabelByType.operation_approval_todo).toBe('审批待处理');
  });

  it('saves channel changes through the notification feature api and reloads the page', async () => {
    const { result } = renderHook(() => useNotificationSettingsPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.setFormValue('email', 'host', 'smtp.changed.example.com');
    });

    await act(async () => {
      await result.current.saveChannels();
    });

    expect(notificationApi.upsertChannel).toHaveBeenCalledWith(
      'email-main',
      expect.objectContaining({
        channel_type: 'email',
        config: expect.objectContaining({
          host: 'smtp.changed.example.com',
          from_email: 'noreply@example.com',
          use_tls: true,
        }),
      })
    );
    expect(notificationApi.upsertChannel).toHaveBeenCalledWith(
      'inapp-main',
      expect.objectContaining({
        channel_type: 'in_app',
      })
    );
    expect(result.current.notice).toBe('基础渠道配置已保存');
  });

  it('saves rules and loads job logs through the feature api', async () => {
    const { result } = renderHook(() => useNotificationSettingsPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.toggleRule('operation_approval_todo', 'dingtalk');
    });

    await act(async () => {
      await result.current.saveRules();
    });

    expect(notificationApi.upsertRules).toHaveBeenCalledWith({
      items: [
        {
          event_type: 'operation_approval_todo',
          enabled_channel_types: ['dingtalk', 'in_app'],
        },
      ],
    });

    await act(async () => {
      await result.current.toggleLogs(11);
    });

    expect(notificationApi.listJobLogs).toHaveBeenCalledWith(11, 20);
    expect(result.current.expandedLogs['11']).toBe(true);
    expect(result.current.logsByJob['11']).toEqual([
      { id: 1, status: 'queued', attempted_at_ms: 1710000000000, error: null },
    ]);
  });
});
