import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NotificationSettings from './NotificationSettings';
import { notificationApi } from '../features/notification/api';

jest.mock('../features/notification/api', () => ({
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

const rulesResponse = {
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
};

describe('NotificationSettings', () => {
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
    notificationApi.listRules.mockResolvedValue(rulesResponse);
    notificationApi.listJobs.mockResolvedValue({
      items: [
        {
          job_id: 11,
          channel_id: 'email-main',
          channel_type: 'email',
          channel_name: '邮件通知',
          event_type: 'operation_approval_todo',
          recipient_username: 'wangxin',
          status: 'queued',
          last_error: null,
          created_at_ms: 1710000000000,
        },
      ],
    });
    notificationApi.listJobLogs.mockResolvedValue({
      items: [{ id: 1, status: 'queued', attempted_at_ms: 1710000000000, error: null }],
    });
    notificationApi.upsertChannel.mockResolvedValue({});
    notificationApi.upsertRules.mockResolvedValue(rulesResponse);
    notificationApi.retryJob.mockResolvedValue({});
    notificationApi.resendJob.mockResolvedValue({});
    notificationApi.dispatchPending.mockResolvedValue({});
  });

  it('renders tabs and saves structured channel config', async () => {
    const user = userEvent.setup();
    render(<NotificationSettings />);

    await screen.findByTestId('notification-settings-page');
    expect(screen.getByTestId('notification-save-rules')).toBeInTheDocument();
    expect(screen.queryByTestId('notification-save-channels')).not.toBeInTheDocument();
    await user.click(screen.getByTestId('notification-tab-channels'));
    expect(screen.getByTestId('notification-dingtalk-app-key')).toHaveValue('dingidnt7v7zbm5tqzyn');
    expect(screen.getByTestId('notification-dingtalk-app-secret')).toHaveValue('gi-v0YEkV_SCwXo9vGvYgBJzEbQ4wS4WUXDwA7ZkqMuNflFu0JfdFW1TeJIxcOjC');
    expect(screen.getByTestId('notification-dingtalk-agent-id')).toHaveValue('4432005762');
    expect(screen.getByTestId('notification-dingtalk-recipient-map')).toHaveValue(`{
  "025247281136343306": "025247281136343306",
  "3245020131886184": "3245020131886184",
  "204548010024278804": "204548010024278804"
}`);
    await user.clear(screen.getByTestId('notification-email-host'));
    await user.type(screen.getByTestId('notification-email-host'), 'smtp.changed.example.com');
    await user.click(screen.getByTestId('notification-save-channels'));

    await waitFor(() => {
      expect(notificationApi.upsertChannel).toHaveBeenCalledTimes(2);
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
    });
  });

  it('saves rule matrix selections', async () => {
    const user = userEvent.setup();
    render(<NotificationSettings />);

    await screen.findByTestId('notification-rule-operation_approval_todo-dingtalk');
    await user.click(screen.getByTestId('notification-rule-operation_approval_todo-dingtalk'));
    await user.click(screen.getByTestId('notification-save-rules'));

    await waitFor(() => {
      expect(notificationApi.upsertRules).toHaveBeenCalledWith({
        items: [
          {
            event_type: 'operation_approval_todo',
            enabled_channel_types: ['dingtalk', 'in_app'],
          },
        ],
      });
    });
  });

  it('filters history and loads delivery logs in history tab', async () => {
    const user = userEvent.setup();
    notificationApi.listJobs
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({
        items: [
          {
            job_id: 11,
            channel_id: 'email-main',
            channel_type: 'email',
            channel_name: '邮件通知',
            event_type: 'operation_approval_todo',
            recipient_username: 'wangxin',
            status: 'queued',
            last_error: null,
            created_at_ms: 1710000000000,
          },
        ],
      });

    render(<NotificationSettings />);

    await screen.findByTestId('notification-tab-history');
    await user.click(screen.getByTestId('notification-tab-history'));
    await user.selectOptions(screen.getByTestId('notification-history-channel'), 'email');
    await user.click(screen.getByTestId('notification-history-apply'));

    await waitFor(() => {
      expect(notificationApi.listJobs).toHaveBeenLastCalledWith({
        limit: 100,
        eventType: '',
        channelType: 'email',
        status: '',
      });
    });

    await user.click(screen.getByTestId('notification-history-logs-11'));
    await waitFor(() => {
      expect(notificationApi.listJobLogs).toHaveBeenCalledWith(11, 20);
    });
  });
});
