import { useCallback, useEffect, useState } from 'react';
import { notificationApi } from '../api';
import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';
import useNotificationChannelSettings from './useNotificationChannelSettings';
import useNotificationHistory from './useNotificationHistory';
import useNotificationRuleSettings from './useNotificationRuleSettings';

export default function useNotificationSettingsPage() {
  const [activeTab, setActiveTab] = useState('rules');
  const [loading, setLoading] = useState(true);
  const [channelsSaving, setChannelsSaving] = useState(false);
  const [rulesSaving, setRulesSaving] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const {
    channelBuckets,
    forms,
    hydrateChannels,
    setFormValue,
    saveChannels: persistChannels,
  } = useNotificationChannelSettings();
  const {
    rulesGroups,
    ruleItems,
    eventLabelByType,
    hydrateRules,
    toggleRule,
    saveRules: persistRules,
  } = useNotificationRuleSettings();
  const {
    historyLoading,
    jobs,
    logsByJob,
    expandedLogs,
    historyFilters,
    loadHistory,
    setHistoryFilter,
    resetHistoryFilters,
    toggleLogs,
    retryJob,
    resendJob,
    dispatchPending: runDispatchPending,
    historyFiltersRef,
  } = useNotificationHistory();

  const loadPage = useCallback(async ({ keepNotice = false } = {}) => {
    if (!keepNotice) setNotice('');
    setError('');
    setLoading(true);
    try {
      const [nextChannels, nextRulesGroups] = await Promise.all([
        notificationApi.listChannels(false),
        notificationApi.listRules(),
      ]);
      hydrateChannels(nextChannels);
      hydrateRules(nextRulesGroups);
      await loadHistory(historyFiltersRef.current);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, '加载通知设置失败'));
    } finally {
      setLoading(false);
    }
  }, [historyFiltersRef, hydrateChannels, hydrateRules, loadHistory]);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  const saveChannels = useCallback(async () => {
    setError('');
    setNotice('');
    setChannelsSaving(true);
    try {
      await persistChannels();
      setNotice('通知通道已保存');
      await loadPage({ keepNotice: true });
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, '保存通知通道失败'));
    } finally {
      setChannelsSaving(false);
    }
  }, [loadPage, persistChannels]);

  const saveRules = useCallback(async () => {
    setError('');
    setNotice('');
    setRulesSaving(true);
    try {
      await persistRules();
      setNotice('通知规则已保存');
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, '保存通知规则失败'));
    } finally {
      setRulesSaving(false);
    }
  }, [persistRules]);

  const applyHistory = useCallback(async (filters = historyFiltersRef.current) => {
    setError('');
    try {
      await loadHistory(filters);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, '加载通知历史失败'));
    }
  }, [historyFiltersRef, loadHistory]);

  const handleResetHistoryFilters = useCallback(async () => {
    setError('');
    try {
      await resetHistoryFilters();
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, '加载通知历史失败'));
    }
  }, [resetHistoryFilters]);

  const handleToggleLogs = useCallback(async (jobId) => {
    try {
      await toggleLogs(jobId);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, '加载通知任务日志失败'));
    }
  }, [toggleLogs]);

  const runJobAction = useCallback(async (action, successText) => {
    setError('');
    setNotice('');
    try {
      await action();
      setNotice(successText);
      await loadHistory(historyFiltersRef.current);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, '通知任务操作失败'));
    }
  }, [historyFiltersRef, loadHistory]);

  const handleRetryJob = useCallback(async (jobId) => {
    await runJobAction(() => retryJob(jobId), `任务 ${jobId} 已重试`);
  }, [retryJob, runJobAction]);

  const handleResendJob = useCallback(async (jobId) => {
    await runJobAction(() => resendJob(jobId), `任务 ${jobId} 已重发`);
  }, [resendJob, runJobAction]);

  const dispatchPending = useCallback(async () => {
    setDispatching(true);
    try {
      await runJobAction(() => runDispatchPending(100), '已派发待处理任务');
    } finally {
      setDispatching(false);
    }
  }, [runDispatchPending, runJobAction]);

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
    resetHistoryFilters: handleResetHistoryFilters,
    toggleLogs: handleToggleLogs,
    handleRetryJob,
    handleResendJob,
    dispatchPending,
  };
}
