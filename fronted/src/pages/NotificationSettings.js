import React from 'react';
import useNotificationSettingsPage from '../features/notification/settings/useNotificationSettingsPage';
import NotificationChannelsSection from '../features/notification/settings/components/NotificationChannelsSection';
import NotificationHistorySection from '../features/notification/settings/components/NotificationHistorySection';
import NotificationRulesSection from '../features/notification/settings/components/NotificationRulesSection';
import NotificationSettingsHeader from '../features/notification/settings/components/NotificationSettingsHeader';
import { card } from '../features/notification/settings/pageStyles';

const LABELS = {
  email: '邮件',
  dingtalk: '钉钉',
  in_app: '站内信',
  queued: '排队中',
  sent: '已发送',
  failed: '发送失败',
};

const STATUS_LABELS = {
  queued: LABELS.queued,
  sent: LABELS.sent,
  failed: LABELS.failed,
};

const CHANNEL_DESCRIPTIONS = {
  in_app: '用于站内消息的内置信箱通道。',
  email: '通过 SMTP 发送邮件通知。',
  dingtalk: '通过钉钉发送工作通知。',
};

const formatTime = (value) => {
  const ms = Number(value || 0);
  return Number.isFinite(ms) && ms > 0 ? new Date(ms).toLocaleString() : '-';
};

const warningText = (item) => {
  const missing = (item.enabled_channel_types || []).filter(
    (channelType) => !(item.has_enabled_channel_config_by_type || {})[channelType]
  );
  return missing.length
    ? `已启用但未配置：${missing.map((channelType) => LABELS[channelType] || channelType).join('、')}`
    : '';
};

const TABS = [
  { value: 'rules', label: '通知规则', testId: 'notification-tab-rules' },
  { value: 'history', label: '投递历史', testId: 'notification-tab-history' },
  { value: 'channels', label: '通道设置', testId: 'notification-tab-channels' },
];

export default function NotificationSettings() {
  const {
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
  } = useNotificationSettingsPage();

  if (loading) return <div style={{ padding: 12 }}>正在加载通知设置...</div>;

  return (
    <div style={{ maxWidth: 1280, display: 'grid', gap: 16 }} data-testid="notification-settings-page">
      <NotificationSettingsHeader
        activeTab={activeTab}
        onChangeTab={setActiveTab}
        tabs={TABS}
      />

      {error ? (
        <div
          data-testid="notification-error"
          style={{ ...card, borderColor: '#fecaca', background: '#fef2f2', color: '#b91c1c' }}
        >
          {error}
        </div>
      ) : null}
      {notice ? (
        <div style={{ ...card, borderColor: '#bbf7d0', background: '#f0fdf4', color: '#166534' }}>
          {notice}
        </div>
      ) : null}

      {activeTab === 'rules' ? (
        <NotificationRulesSection
          title="通知规则"
          description="为每种事件类型配置应接收通知的通道。"
          rulesGroups={rulesGroups}
          channelTypes={['email', 'dingtalk', 'in_app']}
          labels={LABELS}
          rulesSaving={rulesSaving}
          onSave={saveRules}
          onToggleRule={toggleRule}
          warningText={warningText}
        />
      ) : null}

      {activeTab === 'channels' ? (
        <NotificationChannelsSection
          title="通道设置"
          description="编辑通知通道配置，同时保持现有通知流程稳定。"
          channelTypes={['email', 'dingtalk', 'in_app']}
          labels={LABELS}
          descriptions={CHANNEL_DESCRIPTIONS}
          forms={forms}
          channelBuckets={channelBuckets}
          channelsSaving={channelsSaving}
          onSave={saveChannels}
          onChange={setFormValue}
          formatTime={formatTime}
        />
      ) : null}

      {activeTab === 'history' ? (
        <NotificationHistorySection
          title="投递历史"
          description="查看待发送与已发送任务，筛选结果并展开单任务投递日志。"
          dispatching={dispatching}
          onDispatchPending={dispatchPending}
          historyFilters={historyFilters}
          setHistoryFilter={setHistoryFilter}
          applyHistory={applyHistory}
          resetHistoryFilters={resetHistoryFilters}
          ruleItems={ruleItems}
          channelTypes={['email', 'dingtalk', 'in_app']}
          labels={LABELS}
          statusLabels={STATUS_LABELS}
          historyLoading={historyLoading}
          jobs={jobs}
          logsByJob={logsByJob}
          expandedLogs={expandedLogs}
          eventLabelByType={eventLabelByType}
          formatTime={formatTime}
          onRetryJob={handleRetryJob}
          onResendJob={handleResendJob}
          onToggleLogs={toggleLogs}
        />
      ) : null}
    </div>
  );
}
