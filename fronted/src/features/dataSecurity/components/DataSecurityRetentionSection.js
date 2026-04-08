import React from 'react';
import DataSecurityCard from './DataSecurityCard';

export default function DataSecurityRetentionSection({
  isMobile,
  settings,
  localBackupTargetPath,
  onSettingFieldChange,
  onSaveRetention,
  savingRetention,
}) {
  return (
    <DataSecurityCard title="备份保留策略">
      <div style={{ display: 'grid', gap: '12px' }}>
        <div style={{ padding: '12px', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>服务器本机备份路径</div>
          <div style={{ marginTop: '6px', color: '#111827', wordBreak: 'break-all' }}>
            {localBackupTargetPath || '-'}
          </div>
          <div style={{ marginTop: '8px', color: '#6b7280', fontSize: '0.85rem' }}>
            备份数量:
            {' '}
            <span style={{ color: '#111827', fontWeight: 700 }}>
              {Number(settings?.local_backup_pack_count ?? 0)}
            </span>
          </div>
        </div>

        <div
          style={{
            padding: '12px',
            background: '#f8fafc',
            borderRadius: '10px',
            color: '#475569',
            fontSize: '0.9rem',
          }}
        >
          正式备份只保存在服务器本机目录，不再检查和提示远端副本。
        </div>

        <div
          style={{
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '10px',
            alignItems: isMobile ? 'stretch' : 'center',
          }}
        >
          <label
            style={{
              display: 'flex',
              flexDirection: isMobile ? 'column' : 'row',
              gap: '10px',
              alignItems: isMobile ? 'stretch' : 'center',
            }}
          >
            保留最多备份至
            <input
              type="number"
              min={1}
              max={100}
              step={1}
              value={settings?.backup_retention_max ?? 30}
              onChange={(e) => {
                const raw = Number(e.target.value);
                const nextValue = Math.max(1, Math.min(100, Number.isFinite(raw) ? raw : 30));
                onSettingFieldChange('backup_retention_max', nextValue);
              }}
              style={{
                width: isMobile ? '100%' : '90px',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                boxSizing: 'border-box',
              }}
            />
            个（1~100）
          </label>

          <button
            type="button"
            onClick={onSaveRetention}
            disabled={savingRetention}
            data-testid="ds-retention-save"
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              cursor: savingRetention ? 'not-allowed' : 'pointer',
              background: savingRetention ? '#9ca3af' : '#111827',
              color: 'white',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {savingRetention ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </DataSecurityCard>
  );
}
