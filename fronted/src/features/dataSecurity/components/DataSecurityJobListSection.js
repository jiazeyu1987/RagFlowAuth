import React from 'react';
import DataSecurityCard from './DataSecurityCard';
import { formatTime, getLocalBackupLabel, getStatusColor } from '../dataSecurityHelpers';

export default function DataSecurityJobListSection({ jobs, isMobile, onSelectJob }) {
  return (
    <DataSecurityCard title="备份记录">
      {jobs.length === 0 ? (
        <div style={{ color: '#6b7280' }}>暂无</div>
      ) : (
        <div style={{ display: 'grid', gap: '10px' }}>
          {jobs.map((job) => (
            <div
              key={job.id}
              data-testid={`ds-job-row-${job.id}`}
              style={{
                display: 'flex',
                flexDirection: isMobile ? 'column' : 'row',
                justifyContent: 'space-between',
                alignItems: isMobile ? 'stretch' : 'center',
                padding: '10px 12px',
                border: '1px solid #e5e7eb',
                borderRadius: '10px',
                cursor: 'pointer',
              }}
              onClick={() => onSelectJob(job)}
            >
              <div style={{ display: 'grid', gap: '4px' }}>
                <div
                  style={{
                    display: 'flex',
                    gap: '10px',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                  }}
                >
                  <div style={{ fontWeight: 700 }}>#{job.id}</div>
                  <div style={{ color: getStatusColor(job.status) }}>{job.status}</div>
                  <div style={{ color: '#6b7280' }}>{job.message || ''}</div>
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  Hash: {job.package_hash || '未生成'}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  服务器本机备份: {getLocalBackupLabel(job)}
                  {' '}
                  {job.output_dir ? `| ${job.output_dir}` : ''}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  验证:
                  {' '}
                  {job.verified_at_ms
                    ? `${job.verified_by || '-'} @ ${formatTime(job.verified_at_ms)}`
                    : '未验证'}
                </div>
              </div>

              <div
                style={{
                  color: '#6b7280',
                  fontSize: '0.9rem',
                  textAlign: isMobile ? 'left' : 'right',
                }}
              >
                {formatTime(job.created_at_ms)}
              </div>
            </div>
          ))}
        </div>
      )}
    </DataSecurityCard>
  );
}
