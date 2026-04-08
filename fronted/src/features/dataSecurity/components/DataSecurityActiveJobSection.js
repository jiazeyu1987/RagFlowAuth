import React from 'react';
import DataSecurityCard from './DataSecurityCard';
import { formatTime, getLocalBackupLabel, getStatusColor } from '../dataSecurityHelpers';

function ProgressBar({ value }) {
  const pct = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div
      style={{
        width: '100%',
        background: '#e5e7eb',
        borderRadius: '999px',
        height: '10px',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: `${pct}%`,
          height: '10px',
          background: pct >= 100 ? '#10b981' : '#3b82f6',
          transition: 'width 0.2s',
        }}
      />
    </div>
  );
}

export default function DataSecurityActiveJobSection({ activeJob, isMobile }) {
  return (
    <DataSecurityCard title="备份进度">
      {activeJob ? (
        <>
          <div
            data-testid="ds-active-job"
            style={{
              display: 'flex',
              flexDirection: isMobile ? 'column' : 'row',
              justifyContent: 'space-between',
              gap: '10px',
              alignItems: isMobile ? 'stretch' : 'center',
            }}
          >
            <div style={{ display: 'grid', gap: '6px' }}>
              <div
                data-testid="ds-active-job-status"
                style={{ fontWeight: 600, color: getStatusColor(activeJob.status) }}
              >
                #{activeJob.id} {activeJob.status}
              </div>
              <div
                data-testid="ds-active-job-message"
                style={{ color: '#6b7280', fontSize: '0.9rem' }}
              >
                {activeJob.message || ''}
              </div>
              <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                服务器本机备份: {getLocalBackupLabel(activeJob)}
                {' '}
                {activeJob.output_dir ? `| ${activeJob.output_dir}` : ''}
              </div>
            </div>

            <div
              style={{
                minWidth: isMobile ? 'auto' : '140px',
                textAlign: isMobile ? 'left' : 'right',
                color: '#6b7280',
              }}
            >
              {activeJob.started_at_ms ? formatTime(activeJob.started_at_ms) : ''}
            </div>
          </div>

          <div style={{ marginTop: '10px' }}>
            <ProgressBar value={activeJob.progress} />
            <div
              data-testid="ds-active-job-progress"
              style={{ marginTop: '6px', color: '#6b7280', fontSize: '0.9rem' }}
            >
              {activeJob.progress}%
            </div>
          </div>

          {activeJob.detail ? (
            <div
              data-testid="ds-active-job-detail"
              style={{
                marginTop: '10px',
                padding: '10px',
                background: '#fef2f2',
                color: '#991b1b',
                borderRadius: '8px',
              }}
            >
              {activeJob.detail}
            </div>
          ) : null}
        </>
      ) : (
        <div style={{ color: '#6b7280' }}>暂无备份记录</div>
      )}
    </DataSecurityCard>
  );
}
