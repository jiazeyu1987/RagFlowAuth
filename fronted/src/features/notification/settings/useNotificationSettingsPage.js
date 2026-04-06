import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { notificationApi } from '../api';
import {
  CHANNEL_TYPES,
  DEFAULTS,
  DINGTALK_DEFAULT_RECIPIENT_MAP,
  DINGTALK_FORM_DEFAULTS,
  INITIAL_HISTORY_FILTERS,
} from './constants';

const toInt = (value, label) => {
  const text = String(value || '').trim();
  if (!text) return undefined;
  const parsed = Number(text);
  if (!Number.isInteger(parsed)) throw new Error(`${label} 必须是整数`);
  return parsed;
};

const clean = (value) => Object.fromEntries(Object.entries(value || {}).filter(([, item]) => item !== '' && item !== undefined && item !== null));

const flattenRules = (groups) => (groups || []).flatMap((group) => (group.items || []).map((item) => ({ ...item, group_key: group.group_key })));

const buildBuckets = (items) => {
  const buckets = { email: [], dingtalk: [], in_app: [] };
  (items || []).forEach((item) => {
    const channelType = String(item?.channel_type || '').trim().toLowerCase();
    if (buckets[channelType]) buckets[channelType].push(item);
  });
  return buckets;
};

const isDefaultDingtalkForm = (value) => {
  const form = value || {};
  return String(form.app_key || '').trim() === DINGTALK_FORM_DEFAULTS.app_key
    && String(form.app_secret || '') === DINGTALK_FORM_DEFAULTS.app_secret
    && String(form.agent_id || '').trim() === DINGTALK_FORM_DEFAULTS.agent_id
    && String(form.recipient_map_text || '').trim() === DINGTALK_FORM_DEFAULTS.recipient_map_text
    && String(form.api_base || '').trim() === DINGTALK_FORM_DEFAULTS.api_base
    && String(form.oapi_base || '').trim() === DINGTALK_FORM_DEFAULTS.oapi_base
    && String(form.timeout_seconds || '').trim() === DINGTALK_FORM_DEFAULTS.timeout_seconds;
};

const emptyForms = () => ({
  email: { ...DEFAULTS.email, host: '', port: '', username: '', password: '', use_tls: true, from_email: '', updated_at_ms: null },
  dingtalk: { ...DEFAULTS.dingtalk, ...DINGTALK_FORM_DEFAULTS, updated_at_ms: null },
  in_app: { ...DEFAULTS.in_app, updated_at_ms: null },
});

const buildForms = (items) => {
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
    const config = ding.config || {};
    const recipientMap = config.recipient_map && !Array.isArray(config.recipient_map) && typeof config.recipient_map === 'object' && Object.keys(config.recipient_map).length > 0
      ? config.recipient_map
      : DINGTALK_DEFAULT_RECIPIENT_MAP;
    forms.dingtalk = {
      channelId: ding.channel_id || DEFAULTS.dingtalk.channelId,
      name: ding.name || DEFAULTS.dingtalk.name,
      enabled: !!ding.enabled,
      app_key: String(config.app_key || DINGTALK_FORM_DEFAULTS.app_key),
      app_secret: String(config.app_secret || DINGTALK_FORM_DEFAULTS.app_secret),
      agent_id: config.agent_id === undefined || config.agent_id === null || config.agent_id === '' ? DINGTALK_FORM_DEFAULTS.agent_id : String(config.agent_id),
      recipient_map_text: JSON.stringify(recipientMap, null, 2),
      api_base: String(config.api_base || DINGTALK_FORM_DEFAULTS.api_base),
      oapi_base: String(config.oapi_base || DINGTALK_FORM_DEFAULTS.oapi_base),
      timeout_seconds: config.timeout_seconds === undefined || config.timeout_seconds === null || config.timeout_seconds === '' ? DINGTALK_FORM_DEFAULTS.timeout_seconds : String(config.timeout_seconds),
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

export default function useNotificationSettingsPage() {
  const [activeTab, setActiveTab] = useState('rules');
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [channelsSaving, setChannelsSaving] = useState(false);
  const [rulesSaving, setRulesSaving] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [channels, setChannels] = useState([]);
  const [forms, setForms] = useState(emptyForms());
  const [rulesGroups, setRulesGroups] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [logsByJob, setLogsByJob] = useState({});
  const [expandedLogs, setExpandedLogs] = useState({});
  const [historyFilters, setHistoryFilters] = useState(INITIAL_HISTORY_FILTERS);
  const historyFiltersRef = useRef(INITIAL_HISTORY_FILTERS);

  useEffect(() => {
    historyFiltersRef.current = historyFilters;
  }, [historyFilters]);

  const channelBuckets = useMemo(() => buildBuckets(channels), [channels]);
  const ruleItems = useMemo(() => flattenRules(rulesGroups), [rulesGroups]);
  const eventLabelByType = useMemo(
    () => Object.fromEntries(ruleItems.map((item) => [item.event_type, item.event_label])),
    [ruleItems]
  );

  const loadHistory = useCallback(async (filters = historyFiltersRef.current) => {
    setHistoryLoading(true);
    try {
      const response = await notificationApi.listJobs({
        limit: 100,
        eventType: filters.eventType,
        channelType: filters.channelType,
        status: filters.status,
      });
      setJobs(response.items);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const loadPage = useCallback(async ({ keepNotice = false } = {}) => {
    if (!keepNotice) setNotice('');
    setError('');
    setLoading(true);
    try {
      const [nextChannels, nextRulesGroups] = await Promise.all([
        notificationApi.listChannels(false),
        notificationApi.listRules(),
      ]);
      setChannels(nextChannels);
      setForms(buildForms(nextChannels));
      setRulesGroups(nextRulesGroups);
      await loadHistory(historyFiltersRef.current);
    } catch (requestError) {
      setError(requestError?.message || '加载通知设置失败');
    } finally {
      setLoading(false);
    }
  }, [loadHistory]);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  const setFormValue = useCallback((channelType, field, value) => {
    setForms((prev) => ({ ...prev, [channelType]: { ...prev[channelType], [field]: value } }));
  }, []);

  const saveChannels = useCallback(async () => {
    setError('');
    setNotice('');
    const requests = [];
    try {
      const email = forms.email;
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
      if (channelBuckets.dingtalk.length > 0 || ding.enabled || !isDefaultDingtalkForm(ding)) {
        let recipientMap = {};
        try {
          recipientMap = JSON.parse(String(ding.recipient_map_text || '{}'));
        } catch {
          throw new Error('钉钉 recipient_map 必须是合法 JSON');
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
    } catch (requestError) {
      setError(requestError?.message || '基础渠道配置校验失败');
      return;
    }

    setChannelsSaving(true);
    try {
      for (const item of requests) {
        await notificationApi.upsertChannel(item.channelId, item.payload);
      }
      setNotice('基础渠道配置已保存');
      await loadPage({ keepNotice: true });
    } catch (requestError) {
      setError(requestError?.message || '保存基础渠道配置失败');
    } finally {
      setChannelsSaving(false);
    }
  }, [channelBuckets, forms, loadPage]);

  const toggleRule = useCallback((eventType, channelType) => {
    setRulesGroups((prev) => prev.map((group) => ({
      ...group,
      items: (group.items || []).map((item) => {
        if (item.event_type !== eventType) return item;
        const exists = (item.enabled_channel_types || []).includes(channelType);
        const next = exists
          ? item.enabled_channel_types.filter((value) => value !== channelType)
          : [...(item.enabled_channel_types || []), channelType];
        return { ...item, enabled_channel_types: CHANNEL_TYPES.filter((value) => next.includes(value)) };
      }),
    })));
  }, []);

  const saveRules = useCallback(async () => {
    setError('');
    setNotice('');
    setRulesSaving(true);
    try {
      const nextRulesGroups = await notificationApi.upsertRules({
        items: flattenRules(rulesGroups).map((item) => ({
          event_type: item.event_type,
          enabled_channel_types: item.enabled_channel_types || [],
        })),
      });
      setRulesGroups(nextRulesGroups);
      setNotice('通知规则已保存');
    } catch (requestError) {
      setError(requestError?.message || '保存通知规则失败');
    } finally {
      setRulesSaving(false);
    }
  }, [rulesGroups]);

  const setHistoryFilter = useCallback((field, value) => {
    setHistoryFilters((prev) => ({ ...prev, [field]: value }));
  }, []);

  const applyHistory = useCallback(async (filters = historyFiltersRef.current) => {
    setError('');
    try {
      await loadHistory(filters);
    } catch (requestError) {
      setError(requestError?.message || '加载发送历史失败');
    }
  }, [loadHistory]);

  const resetHistoryFilters = useCallback(async () => {
    setHistoryFilters(INITIAL_HISTORY_FILTERS);
    await applyHistory(INITIAL_HISTORY_FILTERS);
  }, [applyHistory]);

  const toggleLogs = useCallback(async (jobId) => {
    const key = String(jobId);
    if (expandedLogs[key]) {
      setExpandedLogs((prev) => ({ ...prev, [key]: false }));
      return;
    }
    try {
      if (!logsByJob[key]) {
        const items = await notificationApi.listJobLogs(jobId, 20);
        setLogsByJob((prev) => ({ ...prev, [key]: items }));
      }
      setExpandedLogs((prev) => ({ ...prev, [key]: true }));
    } catch (requestError) {
      setError(requestError?.message || '加载任务日志失败');
    }
  }, [expandedLogs, logsByJob]);

  const runJobAction = useCallback(async (action, successText) => {
    setError('');
    setNotice('');
    try {
      await action();
      setNotice(successText);
      await loadHistory(historyFiltersRef.current);
    } catch (requestError) {
      setError(requestError?.message || '通知任务操作失败');
    }
  }, [loadHistory]);

  const handleRetryJob = useCallback(async (jobId) => {
    await runJobAction(() => notificationApi.retryJob(jobId), `任务 ${jobId} 已重试`);
  }, [runJobAction]);

  const handleResendJob = useCallback(async (jobId) => {
    await runJobAction(() => notificationApi.resendJob(jobId), `任务 ${jobId} 已重发`);
  }, [runJobAction]);

  const dispatchPending = useCallback(async () => {
    setDispatching(true);
    try {
      await runJobAction(() => notificationApi.dispatchPending(100), '待发送任务已触发分发');
    } finally {
      setDispatching(false);
    }
  }, [runJobAction]);

  return {
    activeTab,
    loading,
    historyLoading,
    channelsSaving,
    rulesSaving,
    dispatching,
    error,
    notice,
    channelBuckets,
    forms,
    rulesGroups,
    ruleItems,
    eventLabelByType,
    jobs,
    logsByJob,
    expandedLogs,
    historyFilters,
    setActiveTab,
    setFormValue,
    saveChannels,
    toggleRule,
    saveRules,
    setHistoryFilter,
    applyHistory,
    resetHistoryFilters,
    toggleLogs,
    handleRetryJob,
    handleResendJob,
    dispatchPending,
  };
}
