import {
  CHANNEL_TYPES,
  DEFAULTS,
  DINGTALK_DEFAULT_RECIPIENT_MAP,
  DINGTALK_FORM_DEFAULTS,
} from './constants';

export const toInt = (value, label) => {
  const text = String(value || '').trim();
  if (!text) return undefined;
  const parsed = Number(text);
  if (!Number.isInteger(parsed)) throw new Error(`${label}必须为整数`);
  return parsed;
};

export const clean = (value) =>
  Object.fromEntries(
    Object.entries(value || {}).filter(([, item]) => item !== '' && item !== undefined && item !== null)
  );

export const asObject = (value) => (value && typeof value === 'object' && !Array.isArray(value) ? value : {});

export const flattenRules = (groups) =>
  (groups || []).flatMap((group) => (group.items || []).map((item) => ({ ...item, group_key: group.group_key })));

export const buildBuckets = (items) => {
  const buckets = { email: [], dingtalk: [], in_app: [] };
  (items || []).forEach((item) => {
    const channelType = String(item?.channel_type || '').trim().toLowerCase();
    if (buckets[channelType]) buckets[channelType].push(item);
  });
  return buckets;
};

export const isDefaultDingtalkForm = (value) => {
  const form = value || {};
  return String(form.app_key || '').trim() === DINGTALK_FORM_DEFAULTS.app_key
    && String(form.app_secret || '') === DINGTALK_FORM_DEFAULTS.app_secret
    && String(form.agent_id || '').trim() === DINGTALK_FORM_DEFAULTS.agent_id
    && String(form.recipient_map_text || '').trim() === DINGTALK_FORM_DEFAULTS.recipient_map_text
    && String(form.api_base || '').trim() === DINGTALK_FORM_DEFAULTS.api_base
    && String(form.oapi_base || '').trim() === DINGTALK_FORM_DEFAULTS.oapi_base
    && String(form.timeout_seconds || '').trim() === DINGTALK_FORM_DEFAULTS.timeout_seconds;
};

export const emptyForms = () => ({
  email: { ...DEFAULTS.email, host: '', port: '', username: '', password: '', use_tls: true, from_email: '', updated_at_ms: null },
  dingtalk: { ...DEFAULTS.dingtalk, ...DINGTALK_FORM_DEFAULTS, updated_at_ms: null },
  in_app: { ...DEFAULTS.in_app, updated_at_ms: null },
});

export const buildForms = (items) => {
  const forms = emptyForms();
  const buckets = buildBuckets(items);
  const email = buckets.email[0];
  const ding = buckets.dingtalk[0];
  const inApp = buckets.in_app[0];
  if (email) {
    const config = email.config || {};
    forms.email = {
      channelId: email.channel_id || DEFAULTS.email.channelId,
      name: email.name || DEFAULTS.email.name,
      enabled: !!email.enabled,
      host: String(config.host || ''),
      port: config.port === undefined || config.port === null ? '' : String(config.port),
      username: String(config.username || ''),
      password: String(config.password || ''),
      use_tls: config.use_tls === undefined ? true : !!config.use_tls,
      from_email: String(config.from_email || ''),
      updated_at_ms: email.updated_at_ms || null,
    };
  }
  if (ding) {
    const config = asObject(ding.config);
    const hasStoredRecipientMap = Object.prototype.hasOwnProperty.call(config, 'recipient_map');
    const recipientMap = hasStoredRecipientMap
      ? asObject(config.recipient_map)
      : DINGTALK_DEFAULT_RECIPIENT_MAP;
    forms.dingtalk = {
      channelId: ding.channel_id || DEFAULTS.dingtalk.channelId,
      name: ding.name || DEFAULTS.dingtalk.name,
      enabled: !!ding.enabled,
      app_key: String(config.app_key || DINGTALK_FORM_DEFAULTS.app_key),
      app_secret: String(config.app_secret || DINGTALK_FORM_DEFAULTS.app_secret),
      agent_id:
        config.agent_id === undefined || config.agent_id === null || config.agent_id === ''
          ? DINGTALK_FORM_DEFAULTS.agent_id
          : String(config.agent_id),
      recipient_map_text: JSON.stringify(recipientMap, null, 2),
      api_base: String(config.api_base || DINGTALK_FORM_DEFAULTS.api_base),
      oapi_base: String(config.oapi_base || DINGTALK_FORM_DEFAULTS.oapi_base),
      timeout_seconds:
        config.timeout_seconds === undefined || config.timeout_seconds === null || config.timeout_seconds === ''
          ? DINGTALK_FORM_DEFAULTS.timeout_seconds
          : String(config.timeout_seconds),
      updated_at_ms: ding.updated_at_ms || null,
    };
  }
  if (inApp) {
    forms.in_app = {
      channelId: inApp.channel_id || DEFAULTS.in_app.channelId,
      name: inApp.name || DEFAULTS.in_app.name,
      enabled: !!inApp.enabled,
      updated_at_ms: inApp.updated_at_ms || null,
    };
  }
  return forms;
};

export const normalizeEnabledRuleChannelTypes = (next) =>
  CHANNEL_TYPES.filter((value) => next.includes(value));
