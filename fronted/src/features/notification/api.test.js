import { notificationApi } from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('notificationApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('routes admin notification endpoints through the auth backend base url', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true });

    await expect(notificationApi.listChannels(true)).resolves.toEqual({ items: [] });
    await expect(notificationApi.upsertChannel('email/main', { enabled: true })).resolves.toEqual({ ok: true });
    await expect(notificationApi.listRules()).resolves.toEqual({ items: [] });
    await expect(notificationApi.upsertRules({ items: [] })).resolves.toEqual({ ok: true });
    await expect(
      notificationApi.listJobs({ limit: 10, status: 'queued', eventType: 'approval', channelType: 'email' })
    ).resolves.toEqual({ items: [] });
    await expect(notificationApi.listJobLogs('job/1', '20&all=true')).resolves.toEqual({ items: [] });
    await expect(notificationApi.retryJob('job/1')).resolves.toEqual({ ok: true });
    await expect(notificationApi.dispatchPending('50&all=true')).resolves.toEqual({ ok: true });
    await expect(notificationApi.resendJob('job/1')).resolves.toEqual({ ok: true });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/admin/notifications/channels?enabled_only=true'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/admin/notifications/channels/email%2Fmain',
      {
        method: 'PUT',
        body: JSON.stringify({ enabled: true }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/admin/notifications/rules'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/admin/notifications/rules',
      {
        method: 'PUT',
        body: JSON.stringify({ items: [] }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      5,
      'http://auth.local/api/admin/notifications/jobs?limit=10&status=queued&event_type=approval&channel_type=email'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      6,
      'http://auth.local/api/admin/notifications/jobs/job%2F1/logs?limit=20%26all%3Dtrue'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      7,
      'http://auth.local/api/admin/notifications/jobs/job%2F1/retry',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      8,
      'http://auth.local/api/admin/notifications/dispatch?limit=50%26all%3Dtrue',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      9,
      'http://auth.local/api/admin/notifications/jobs/job%2F1/resend',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
  });

  it('routes personal message endpoints through the auth backend base url', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [], unread_count: 0, total: 0 })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({ ok: true });

    await expect(notificationApi.listMyMessages({ limit: 30, offset: 5, unreadOnly: true })).resolves.toEqual({
      items: [],
      unread_count: 0,
      total: 0,
    });
    await expect(notificationApi.updateMyMessageReadState('job/2', true)).resolves.toEqual({ ok: true });
    await expect(notificationApi.markAllMyMessagesRead()).resolves.toEqual({ ok: true });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/me/messages?limit=30&offset=5&unread_only=true'
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/me/messages/job%2F2/read-state',
      {
        method: 'PATCH',
        body: JSON.stringify({ read: true }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/me/messages/mark-all-read',
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
  });
});
