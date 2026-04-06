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

const normalizeCountField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  const value = envelope[field];
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

const normalizeJobList = (payload) => ({
  items: normalizeArrayField(payload, 'items', 'notification_jobs_list'),
  count: normalizeCountField(payload, 'count', 'notification_jobs_list'),
});

const normalizeInboxList = (payload) => ({
  items: normalizeArrayField(payload, 'items', 'notification_messages_list'),
  count: normalizeCountField(payload, 'count', 'notification_messages_list'),
  total: normalizeCountField(payload, 'total', 'notification_messages_list'),
  unreadCount: normalizeCountField(payload, 'unread_count', 'notification_messages_list'),
});

export const notificationApi = {
  listChannels: async (enabledOnly = false) =>
    normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(`/api/admin/notifications/channels?enabled_only=${enabledOnly ? 'true' : 'false'}`)
      ),
      'items',
      'notification_channels_list'
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
    normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/admin/notifications/rules')),
      'groups',
      'notification_rules_list'
    ),

  upsertRules: async (payload) =>
    normalizeArrayField(
      await httpClient.requestJson(authBackendUrl('/api/admin/notifications/rules'), {
        method: 'PUT',
        body: JSON.stringify(payload || {}),
      }),
      'groups',
      'notification_rules_upsert'
    ),

  listJobs: async ({ limit = 50, status = '', eventType = '', channelType = '' } = {}) => {
    const qs = new URLSearchParams();
    qs.set('limit', String(limit));
    if (status) qs.set('status', status);
    if (eventType) qs.set('event_type', eventType);
    if (channelType) qs.set('channel_type', channelType);
    return normalizeJobList(
      await httpClient.requestJson(authBackendUrl(`/api/admin/notifications/jobs?${qs.toString()}`))
    );
  },

  listJobLogs: async (jobId, limit = 20) =>
    normalizeArrayField(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/admin/notifications/jobs/${encodeURIComponent(jobId)}/logs?limit=${encodeURIComponent(limit)}`
        )
      ),
      'items',
      'notification_job_logs_list'
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
    return normalizeInboxList(
      await httpClient.requestJson(authBackendUrl(`/api/me/messages?${qs.toString()}`))
    );
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
