import React from 'react';
import DataSecurityCard from './DataSecurityCard';
import { cronToSchedule, formatSchedule, scheduleToCron } from '../scheduleUtils';

const WEEKDAY_OPTIONS = [
  { value: '0', label: '周日' },
  { value: '1', label: '周一' },
  { value: '2', label: '周二' },
  { value: '3', label: '周三' },
  { value: '4', label: '周四' },
  { value: '5', label: '周五' },
  { value: '6', label: '周六' },
];

const DEFAULT_SCHEDULE = { type: 'daily', hour: '18', minute: '30', weekday: '1' };

function padTimePart(value, fallback) {
  const raw = String(value ?? '').trim();
  if (!/^\d{1,2}$/.test(raw)) return fallback;
  return raw.padStart(2, '0');
}

function getResolvedSchedule(cronValue) {
  const raw = String(cronValue || '').trim();
  const parsed = cronToSchedule(raw);
  return {
    schedule: parsed || DEFAULT_SCHEDULE,
    invalid: Boolean(raw) && !parsed,
  };
}

function DataSecurityScheduleEditor({
  title,
  cronValue,
  enabled = true,
  disabled = false,
  testIdPrefix,
  onScheduleChange,
}) {
  const { schedule, invalid } = getResolvedSchedule(cronValue);
  const timeValue = `${padTimePart(schedule.hour, DEFAULT_SCHEDULE.hour)}:${padTimePart(schedule.minute, DEFAULT_SCHEDULE.minute)}`;

  const updateSchedule = (patch) => {
    const next = {
      ...schedule,
      ...patch,
    };
    if (next.type !== 'weekly') {
      delete next.weekday;
    } else if (!String(next.weekday || '').trim()) {
      next.weekday = DEFAULT_SCHEDULE.weekday;
    }
    onScheduleChange(scheduleToCron(next));
  };

  return (
    <div
      style={{
        padding: '12px',
        border: '1px solid #e5e7eb',
        borderRadius: '10px',
        display: 'grid',
        gap: '10px',
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <div style={{ display: 'grid', gap: '4px' }}>
        <strong style={{ color: '#111827' }}>{title}</strong>
        <span style={{ color: '#6b7280', fontSize: '0.85rem' }}>
          当前计划：
          {' '}
          {enabled ? formatSchedule(schedule) : '未启用'}
        </span>
        {invalid ? (
          <span style={{ color: '#b91c1c', fontSize: '0.85rem' }}>
            当前计划格式不受此页面支持，保存后会改为此处选中的每日/每周计划。
          </span>
        ) : null}
      </div>

      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
        <label style={{ display: 'grid', gap: '6px', minWidth: '120px' }}>
          频率
          <select
            value={schedule.type}
            onChange={(e) => updateSchedule({ type: e.target.value })}
            disabled={disabled}
            data-testid={`${testIdPrefix}-type`}
            style={{ padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px' }}
          >
            <option value="daily">每日</option>
            <option value="weekly">每周</option>
          </select>
        </label>

        {schedule.type === 'weekly' ? (
          <label style={{ display: 'grid', gap: '6px', minWidth: '120px' }}>
            星期
            <select
              value={String(schedule.weekday || DEFAULT_SCHEDULE.weekday)}
              onChange={(e) => updateSchedule({ weekday: e.target.value })}
              disabled={disabled}
              data-testid={`${testIdPrefix}-weekday`}
              style={{ padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px' }}
            >
              {WEEKDAY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <label style={{ display: 'grid', gap: '6px', minWidth: '140px' }}>
          时间
          <input
            type="time"
            value={timeValue}
            onChange={(e) => {
              const [hour = DEFAULT_SCHEDULE.hour, minute = DEFAULT_SCHEDULE.minute] = String(
                e.target.value || ''
              ).split(':');
              updateSchedule({
                hour: padTimePart(hour, DEFAULT_SCHEDULE.hour),
                minute: padTimePart(minute, DEFAULT_SCHEDULE.minute),
              });
            }}
            disabled={disabled}
            data-testid={`${testIdPrefix}-time`}
            style={{ padding: '8px', border: '1px solid #d1d5db', borderRadius: '8px' }}
          />
        </label>
      </div>
    </div>
  );
}

export default function DataSecuritySettingsSection({
  isMobile,
  settings,
  localBackupTargetPath,
  onSettingFieldChange,
  onSaveSettings,
  savingSettings,
}) {
  return (
    <DataSecurityCard title="备份高级设置">
      <div style={{ display: 'grid', gap: '12px' }}>
        <div
          style={{
            padding: '12px',
            background: '#f8fafc',
            borderRadius: '10px',
            color: '#475569',
            fontSize: '0.9rem',
          }}
        >
          正式备份固定写入服务器本机目录
          {' '}
          <strong>{localBackupTargetPath || '-'}</strong>
          ，当前页面不再检查、配置或提示远端副本。
        </div>

        <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
          <input
            type="checkbox"
            checked={Boolean(settings?.enabled)}
            onChange={(e) => onSettingFieldChange('enabled', e.target.checked)}
            data-testid="ds-enabled"
          />
          启用定时备份
        </label>

        <DataSecurityScheduleEditor
          title="增量备份计划"
          cronValue={settings?.incremental_schedule}
          enabled={Boolean(settings?.enabled)}
          disabled={!settings?.enabled}
          testIdPrefix="ds-incremental-schedule"
          onScheduleChange={(nextValue) => onSettingFieldChange('incremental_schedule', nextValue)}
        />

        <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
          <input
            type="checkbox"
            checked={Boolean(settings?.full_backup_enabled)}
            onChange={(e) => onSettingFieldChange('full_backup_enabled', e.target.checked)}
            data-testid="ds-full-backup-enabled"
          />
          启用定时全量备份
        </label>

        <DataSecurityScheduleEditor
          title="全量备份计划"
          cronValue={settings?.full_backup_schedule}
          enabled={Boolean(settings?.full_backup_enabled)}
          disabled={!settings?.full_backup_enabled}
          testIdPrefix="ds-full-schedule"
          onScheduleChange={(nextValue) => onSettingFieldChange('full_backup_schedule', nextValue)}
        />

        <label>
          RAGFlow docker-compose.yml 路径
          <input
            value={settings?.ragflow_compose_path || ''}
            onChange={(e) => onSettingFieldChange('ragflow_compose_path', e.target.value)}
            data-testid="ds-ragflow-compose-path"
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              marginTop: '6px',
            }}
          />
        </label>

        <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
          <input
            type="checkbox"
            checked={Boolean(settings?.ragflow_stop_services)}
            onChange={(e) => onSettingFieldChange('ragflow_stop_services', e.target.checked)}
            data-testid="ds-ragflow-stop-services"
          />
          备份前停止 RAGFlow 服务
        </label>

        <label style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
          <input
            type="checkbox"
            checked={Boolean(settings?.full_backup_include_images)}
            onChange={(e) => onSettingFieldChange('full_backup_include_images', e.target.checked)}
            data-testid="ds-full-backup-include-images"
          />
          全量备份包含 Docker 镜像
        </label>

        <label>
          项目数据库路径
          <input
            value={settings?.auth_db_path || 'data/auth.db'}
            onChange={(e) => onSettingFieldChange('auth_db_path', e.target.value)}
            data-testid="ds-auth-db-path"
            style={{
              width: '100%',
              padding: '8px',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              marginTop: '6px',
            }}
          />
        </label>

        <button
          type="button"
          onClick={onSaveSettings}
          disabled={savingSettings}
          data-testid="ds-settings-save"
          style={{
            padding: '10px 14px',
            borderRadius: '8px',
            border: 'none',
            cursor: savingSettings ? 'not-allowed' : 'pointer',
            background: savingSettings ? '#9ca3af' : '#111827',
            color: 'white',
            width: isMobile ? '100%' : 'fit-content',
          }}
        >
          {savingSettings ? '保存中...' : '保存高级设置'}
        </button>
      </div>
    </DataSecurityCard>
  );
}
