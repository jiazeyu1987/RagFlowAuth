import { authBackendUrl } from '../../config/backend';
import { httpClient } from '../../shared/http/httpClient';

export const notificationApi = {
  listChannels: async (enabledOnly = false) =>
    httpClient.requestJson(
      authBackendUrl(`/api/admin/notifications/channels?enabled_only=${enabledOnly ? 'true' : 'false'}`)
    ),

  upsertChannel: async (channelId, payload) =>
    httpClient.requestJson(
      authBackendUrl(`/api/admin/notifications/channels/${encodeURIComponent(channelId)}`),
      {
        method: 'PUT',
        body: JSON.stringify(payload || {}),
      }
    ),

  listRules: async () =>
    httpClient.requestJson(authBackendUrl('/api/admin/notifications/rules')),

  upsertRules: async (payload) =>
    httpClient.requestJson(authBackendUrl('/api/admin/notifications/rules'), {
      method: 'PUT',
      body: JSON.stringify(payload || {}),
    }),

  listJobs: async ({ limit = 50, status = '', eventType = '', channelType = '' } = {}) => {
    const qs = new URLSearchParams();
    qs.set('limit', String(limit));
    if (status) qs.set('status', status);
    if (eventType) qs.set('event_type', eventType);
    if (channelType) qs.set('channel_type', channelType);
    return httpClient.requestJson(authBackendUrl(`/api/admin/notifications/jobs?${qs.toString()}`));
  },

  listJobLogs: async (jobId, limit = 20) =>
    httpClient.requestJson(
      authBackendUrl(
        `/api/admin/notifications/jobs/${encodeURIComponent(jobId)}/logs?limit=${encodeURIComponent(limit)}`
      )
    ),

  retryJob: async (jobId) =>
    httpClient.requestJson(authBackendUrl(`/api/admin/notifications/jobs/${encodeURIComponent(jobId)}/retry`), {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  dispatchPending: async (limit = 100) =>
    httpClient.requestJson(authBackendUrl(`/api/admin/notifications/dispatch?limit=${encodeURIComponent(limit)}`), {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  resendJob: async (jobId) =>
    httpClient.requestJson(authBackendUrl(`/api/admin/notifications/jobs/${encodeURIComponent(jobId)}/resend`), {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  listMyMessages: async ({ limit = 50, offset = 0, unreadOnly = false } = {}) => {
    const qs = new URLSearchParams();
    qs.set('limit', String(limit));
    qs.set('offset', String(offset));
    if (unreadOnly) qs.set('unread_only', 'true');
    return httpClient.requestJson(authBackendUrl(`/api/me/messages?${qs.toString()}`));
  },

  updateMyMessageReadState: async (jobId, read) =>
    httpClient.requestJson(authBackendUrl(`/api/me/messages/${encodeURIComponent(jobId)}/read-state`), {
      method: 'PATCH',
      body: JSON.stringify({ read: !!read }),
    }),

  markAllMyMessagesRead: async () =>
    httpClient.requestJson(authBackendUrl('/api/me/messages/mark-all-read'), {
      method: 'POST',
      body: JSON.stringify({}),
    }),
};
