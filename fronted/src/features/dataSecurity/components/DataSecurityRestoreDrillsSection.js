import React from 'react';
import DataSecurityCard from './DataSecurityCard';
import { formatTime } from '../dataSecurityHelpers';

export default function DataSecurityRestoreDrillsSection({
  isMobile,
  restoreEligibleJobs,
  selectedRestoreJobId,
  restoreTarget,
  restoreNotes,
  restoreDrills,
  creatingRestoreDrill,
  onSelectedRestoreJobIdChange,
  onRestoreTargetChange,
  onRestoreNotesChange,
  onSubmit,
}) {
  return (
    <DataSecurityCard title="恢复演练">
      <div style={{ display: 'grid', gap: '10px' }}>
        <div
          style={{
            padding: '12px',
            background: '#f8fafc',
            borderRadius: '10px',
            color: '#475569',
            fontSize: '0.9rem',
          }}
        >
          恢复演练仅使用服务器本机备份目录中生成的备份包。
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
            gap: '10px',
          }}
        >
          <label>
            服务器本机备份任务
            <select
              data-testid="ds-restore-job-select"
              value={selectedRestoreJobId}
              onChange={(e) => onSelectedRestoreJobIdChange(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                marginTop: '6px',
              }}
            >
              <option value="">请选择</option>
              {restoreEligibleJobs.map((job) => (
                <option key={job.id} value={String(job.id)}>
                  #{job.id} {job.kind || '-'} {job.status || '-'}
                </option>
              ))}
            </select>
          </label>

          <label>
            恢复目标
            <input
              data-testid="ds-restore-target"
              value={restoreTarget}
              onChange={(e) => onRestoreTargetChange(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                marginTop: '6px',
              }}
            />
          </label>

          <label>
            验证备注
            <input
              data-testid="ds-restore-notes"
              value={restoreNotes}
              onChange={(e) => onRestoreNotesChange(e.target.value)}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                marginTop: '6px',
              }}
            />
          </label>
        </div>

        {restoreEligibleJobs.length === 0 ? (
          <div style={{ color: '#6b7280' }}>当前没有可用于恢复演练的服务器本机备份任务。</div>
        ) : null}

        <button
          type="button"
          onClick={onSubmit}
          data-testid="ds-restore-submit"
          disabled={creatingRestoreDrill}
          style={{
            padding: '10px 14px',
            borderRadius: '8px',
            border: 'none',
            cursor: creatingRestoreDrill ? 'not-allowed' : 'pointer',
            background: creatingRestoreDrill ? '#9ca3af' : '#111827',
            color: 'white',
            width: isMobile ? '100%' : 'fit-content',
          }}
        >
          {creatingRestoreDrill ? '记录中...' : '记录恢复演练'}
        </button>

        {restoreDrills.length === 0 ? (
          <div style={{ color: '#6b7280' }}>暂无恢复演练记录</div>
        ) : (
          <div style={{ display: 'grid', gap: '10px' }}>
            {restoreDrills.map((item) => (
              <div
                key={item.drill_id}
                data-testid={`ds-restore-row-${item.drill_id}`}
                style={{
                  padding: '10px 12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '10px',
                  display: 'grid',
                  gap: '4px',
                }}
              >
                <div style={{ fontWeight: 600 }}>
                  {item.drill_id} / job #{item.job_id} / {item.result}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
                  target: {item.restore_target} | by: {item.executed_by} | at:
                  {' '}
                  {formatTime(item.executed_at_ms)}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  path: {item.backup_path} | hash: {item.backup_hash}
                </div>
                <div style={{ color: '#374151', fontSize: '0.85rem' }}>
                  package validation: {item.package_validation_status || '-'} | acceptance:
                  {' '}
                  {item.acceptance_status || '-'}
                </div>
                <div style={{ color: '#374151', fontSize: '0.85rem' }}>
                  hash match: {String(Boolean(item.hash_match))} | compare match:
                  {' '}
                  {String(Boolean(item.compare_match))}
                </div>
                {item.actual_backup_hash ? (
                  <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                    actual hash: {item.actual_backup_hash}
                  </div>
                ) : null}
                {item.restored_auth_db_path ? (
                  <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                    restored auth.db: {item.restored_auth_db_path}
                  </div>
                ) : null}
                {item.verification_notes ? (
                  <div style={{ color: '#374151', fontSize: '0.9rem' }}>
                    notes: {item.verification_notes}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </DataSecurityCard>
  );
}
