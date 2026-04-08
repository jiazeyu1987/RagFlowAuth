import { useCallback, useMemo, useState } from 'react';
import { notificationApi } from '../api';
import { asObject, buildBuckets, buildForms, clean, emptyForms, isDefaultDingtalkForm, toInt } from './helpers';

export default function useNotificationChannelSettings() {
  const [channels, setChannels] = useState([]);
  const [forms, setForms] = useState(emptyForms());

  const channelBuckets = useMemo(() => buildBuckets(channels), [channels]);

  const hydrateChannels = useCallback((items) => {
    setChannels(items || []);
    setForms(buildForms(items || []));
  }, []);

  const setFormValue = useCallback((channelType, field, value) => {
    setForms((prev) => ({ ...prev, [channelType]: { ...prev[channelType], [field]: value } }));
  }, []);

  const saveChannels = useCallback(async () => {
    const requests = [];
    const email = forms.email;
    const existingEmailConfig = asObject(channelBuckets.email[0]?.config);
    if (
      channelBuckets.email.length > 0
      || email.enabled
      || ['host', 'port', 'username', 'password', 'from_email'].some((field) => String(email[field] || '').trim())
    ) {
      requests.push({
        channelId: email.channelId,
        payload: {
          channel_type: 'email',
          name: email.name,
          enabled: !!email.enabled,
          config: clean({
            ...existingEmailConfig,
            host: String(email.host || '').trim(),
            port: toInt(email.port, '邮件端口'),
            username: String(email.username || '').trim(),
            password: String(email.password || ''),
            use_tls: !!email.use_tls,
            from_email: String(email.from_email || '').trim(),
          }),
        },
      });
    }

    const ding = forms.dingtalk;
    const existingDingtalkConfig = asObject(channelBuckets.dingtalk[0]?.config);
    if (channelBuckets.dingtalk.length > 0 || ding.enabled || !isDefaultDingtalkForm(ding)) {
      let recipientMap = {};
      try {
        recipientMap = JSON.parse(String(ding.recipient_map_text || '{}'));
      } catch {
        throw new Error('钉钉 recipient_map 必须是有效 JSON');
      }
      if (recipientMap === null || Array.isArray(recipientMap) || typeof recipientMap !== 'object') {
        throw new Error('钉钉 recipient_map 必须是对象');
      }
      requests.push({
        channelId: ding.channelId,
        payload: {
          channel_type: 'dingtalk',
          name: ding.name,
          enabled: !!ding.enabled,
          config: clean({
            ...existingDingtalkConfig,
            app_key: String(ding.app_key || '').trim(),
            app_secret: String(ding.app_secret || ''),
            agent_id: String(ding.agent_id || '').trim(),
            recipient_map: recipientMap,
            api_base: String(ding.api_base || '').trim(),
            oapi_base: String(ding.oapi_base || '').trim(),
            timeout_seconds: toInt(ding.timeout_seconds, '钉钉超时时间'),
          }),
        },
      });
    }

    requests.push({
      channelId: forms.in_app.channelId,
      payload: {
        channel_type: 'in_app',
        name: forms.in_app.name,
        enabled: !!forms.in_app.enabled,
        config: {},
      },
    });

    for (const item of requests) {
      await notificationApi.upsertChannel(item.channelId, item.payload);
    }
  }, [channelBuckets, forms]);

  return {
    channels,
    channelBuckets,
    forms,
    hydrateChannels,
    setFormValue,
    saveChannels,
  };
}
