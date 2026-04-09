import React from 'react';
import DataSecurityCard from './DataSecurityCard';
import { formatTime } from '../dataSecurityHelpers';

export default function DataSecurityRestoreDrillsSection({
  isMobile,
  restoreEligibleJobs,
  selectedRestoreJobId,
  restoreDrillBlockedReason,
  canSubmitRestoreDrill,
  canSubmitRealRestore,
  restoreTarget,
  restoreNotes,
  restoreDrills,
  creatingRestoreDrill,
  creatingRealRestore,
  onSelectedRestoreJobIdChange,
  onRestoreTargetChange,
  onRestoreNotesChange,
  onSubmit,
  onRealRestoreSubmit,
}) {
  const submitDisabled = creatingRestoreDrill || !canSubmitRestoreDrill;
  const realRestoreDisabled = creatingRealRestore || creatingRestoreDrill || !canSubmitRealRestore;

  return (
    <DataSecurityCard title="恢复">
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
          先选择一份服务器本机备份。下方分为两种操作：“恢复演练（仅校验）”只验证备份包是否可读、可复制、可比对；
          “真实恢复当前数据”会直接覆盖当前系统的 live `auth.db`。
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
            演练目标标识
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

        <div
          style={{
            display: 'grid',
            gap: '10px',
            gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
          }}
        >
          <div
            style={{
              padding: '12px',
              border: '1px solid #e5e7eb',
              borderRadius: '10px',
              display: 'grid',
              gap: '10px',
            }}
          >
            <div style={{ fontWeight: 600 }}>恢复演练（仅校验）</div>
            <div style={{ color: '#475569', fontSize: '0.9rem' }}>
              不会覆盖当前系统数据，也不会恢复已删除的用户，只会记录一条恢复演练结果。
            </div>
            <button
              type="button"
              onClick={onSubmit}
              data-testid="ds-restore-submit"
              disabled={submitDisabled}
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                border: 'none',
                cursor: submitDisabled ? 'not-allowed' : 'pointer',
                background: submitDisabled ? '#9ca3af' : '#111827',
                color: 'white',
                width: isMobile ? '100%' : 'fit-content',
              }}
            >
              {creatingRestoreDrill ? '记录中...' : '记录恢复演练（不恢复当前数据）'}
            </button>
          </div>

          <div
            style={{
              padding: '12px',
              border: '1px solid #fecaca',
              background: '#fef2f2',
              borderRadius: '10px',
              display: 'grid',
              gap: '10px',
            }}
          >
            <div style={{ fontWeight: 600, color: '#991b1b' }}>真实恢复当前数据</div>
            <div style={{ color: '#991b1b', fontSize: '0.9rem' }}>
              会直接覆盖当前系统数据，可以恢复被删除的用户，也会同时回滚当前用户、权限和配置到所选备份状态。
            </div>
            <button
              type="button"
              onClick={onRealRestoreSubmit}
              data-testid="ds-real-restore-submit"
              disabled={realRestoreDisabled}
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                border: 'none',
                cursor: realRestoreDisabled ? 'not-allowed' : 'pointer',
                background: realRestoreDisabled ? '#fca5a5' : '#b91c1c',
                color: 'white',
                width: isMobile ? '100%' : 'fit-content',
              }}
            >
              {creatingRealRestore ? '恢复中...' : '真实恢复当前数据'}
            </button>
          </div>
        </div>

        {restoreEligibleJobs.length === 0 ? (
          <div style={{ color: '#6b7280' }}>当前没有可用于恢复的服务器本机备份任务。</div>
        ) : null}

        {restoreDrillBlockedReason ? (
          <div
            data-testid="ds-restore-blocked-reason"
            style={{
              padding: '10px 12px',
              background: '#fff7ed',
              color: '#9a3412',
              borderRadius: '10px',
              fontSize: '0.9rem',
            }}
          >
            {restoreDrillBlockedReason}
          </div>
        ) : null}

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
                  target: {item.restore_target} | by: {item.executed_by} | at:{' '}
                  {formatTime(item.executed_at_ms)}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>
                  path: {item.backup_path} | hash: {item.backup_hash}
                </div>
                <div style={{ color: '#374151', fontSize: '0.85rem' }}>
                  package validation: {item.package_validation_status || '-'} | acceptance:{' '}
                  {item.acceptance_status || '-'}
                </div>
                <div style={{ color: '#374151', fontSize: '0.85rem' }}>
                  hash match: {String(Boolean(item.hash_match))} | compare match:{' '}
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
