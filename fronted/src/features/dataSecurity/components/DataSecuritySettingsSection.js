import React from 'react';
import DataSecurityCard from './DataSecurityCard';

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
