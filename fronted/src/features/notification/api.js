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

const normalizeObjectField = (payload, field, action) => {
  const envelope = assertObjectPayload(payload, action);
  const value = envelope[field];
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${action}_invalid_payload`);
  }
  return value;
};

const normalizeJobList = (payload) => ({
  items: normalizeArrayField(payload, 'items', 'notification_jobs_list'),
  count: normalizeCountField(payload, 'count', 'notification_jobs_list'),
});

const normalizeRecipientMapRebuild = (payload) => {
  const action = 'notification_dingtalk_recipient_map_rebuild';
  const envelope = assertObjectPayload(payload, action);
  const channelId = String(envelope.channel_id || '').trim();
  if (!channelId) {
    throw new Error(`${action}_invalid_payload`);
  }
  return {
    channel_id: channelId,
    org_user_count: normalizeCountField(envelope, 'org_user_count', action),
    directory_entry_count: normalizeCountField(envelope, 'directory_entry_count', action),
    alias_entry_count: normalizeCountField(envelope, 'alias_entry_count', action),
    invalid_org_user_count: normalizeCountField(envelope, 'invalid_org_user_count', action),
    invalid_org_users: normalizeArrayField(envelope, 'invalid_org_users', action),
  };
};

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
    normalizeObjectField(
      await httpClient.requestJson(
        authBackendUrl(`/api/admin/notifications/channels/${encodeURIComponent(channelId)}`),
        {
          method: 'PUT',
          body: JSON.stringify(payload || {}),
        }
      ),
      'channel',
      'notification_channel_upsert'
    ),

  rebuildDingtalkRecipientMap: async (channelId) =>
    normalizeRecipientMapRebuild(
      await httpClient.requestJson(
        authBackendUrl(
          `/api/admin/notifications/channels/${encodeURIComponent(channelId)}/recipient-map/rebuild-from-org`
        ),
        {
          method: 'POST',
          body: JSON.stringify({}),
        }
      )
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
    normalizeObjectField(
      await httpClient.requestJson(authBackendUrl(`/api/admin/notifications/jobs/${encodeURIComponent(jobId)}/retry`), {
        method: 'POST',
        body: JSON.stringify({}),
      }),
      'job',
      'notification_job_retry'
    ),

  dispatchPending: async (limit = 100) =>
    normalizeObjectField(
      await httpClient.requestJson(authBackendUrl(`/api/admin/notifications/dispatch?limit=${encodeURIComponent(limit)}`), {
        method: 'POST',
        body: JSON.stringify({}),
      }),
      'dispatch',
      'notification_dispatch'
    ),

  resendJob: async (jobId) =>
    normalizeObjectField(
      await httpClient.requestJson(authBackendUrl(`/api/admin/notifications/jobs/${encodeURIComponent(jobId)}/resend`), {
        method: 'POST',
        body: JSON.stringify({}),
      }),
      'job',
      'notification_job_resend'
    ),

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
    normalizeObjectField(
      await httpClient.requestJson(authBackendUrl(`/api/me/messages/${encodeURIComponent(jobId)}/read-state`), {
        method: 'PATCH',
        body: JSON.stringify({ read: !!read }),
      }),
      'message',
      'notification_message_read_state_update'
    ),

  markAllMyMessagesRead: async () =>
    normalizeObjectField(
      await httpClient.requestJson(authBackendUrl('/api/me/messages/mark-all-read'), {
        method: 'POST',
        body: JSON.stringify({}),
      }),
      'result',
      'notification_messages_mark_all_read'
    ),
};
