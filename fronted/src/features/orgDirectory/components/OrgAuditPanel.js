import React from 'react';

import { actionLabel, entityLabel, formatDateTime } from '../helpers';
import { tdStyle, thStyle } from '../pageStyles';

function AuditChangeText({ log }) {
  if (log.action === 'rebuild') {
    return (
      <div>
        <div style={{ fontWeight: 600 }}>{log.after_name || '组织架构已重建'}</div>
        {log.before_name ? (
          <div style={{ marginTop: 4, color: '#6b7280', fontSize: '0.8rem' }}>
            Excel: {log.before_name}
          </div>
        ) : null}
      </div>
    );
  }

  if (log.action === 'create') return <span>新增: {log.after_name || '-'}</span>;
  if (log.action === 'update') {
    return (
      <span>
        {log.before_name || '-'} {'->'} {log.after_name || '-'}
      </span>
    );
  }
  if (log.action === 'delete') return <span>删除: {log.before_name || '-'}</span>;
  return <span>{log.after_name || log.before_name || '-'}</span>;
}

export default function OrgAuditPanel({
  isMobile,
  auditFilter,
  setAuditFilter,
  refreshAudit,
  auditError,
  auditLogs,
}) {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, minmax(0, 1fr))',
          gap: 8,
        }}
      >
        <select
          value={auditFilter.entity_type}
          onChange={(event) => setAuditFilter((prev) => ({ ...prev, entity_type: event.target.value }))}
          data-testid="org-audit-entity-type"
          style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #d1d5db' }}
        >
          <option value="">全部类型</option>
          <option value="company">公司</option>
          <option value="department">部门</option>
          <option value="org_structure">组织重建</option>
        </select>
        <select
          value={auditFilter.action}
          onChange={(event) => setAuditFilter((prev) => ({ ...prev, action: event.target.value }))}
          data-testid="org-audit-action"
          style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #d1d5db' }}
        >
          <option value="">全部动作</option>
          <option value="create">新增</option>
          <option value="update">更新</option>
          <option value="delete">删除</option>
          <option value="rebuild">重建</option>
        </select>
        <select
          value={String(auditFilter.limit)}
          onChange={(event) => setAuditFilter((prev) => ({ ...prev, limit: Number(event.target.value) }))}
          data-testid="org-audit-limit"
          style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #d1d5db' }}
        >
          <option value="50">50</option>
          <option value="200">200</option>
          <option value="500">500</option>
        </select>
        <button
          type="button"
          data-testid="org-audit-refresh"
          onClick={() => refreshAudit(auditFilter)}
          style={{
            padding: '9px 12px',
            backgroundColor: '#111827',
            color: '#ffffff',
            border: 'none',
            borderRadius: 8,
            cursor: 'pointer',
          }}
        >
          刷新审计
        </button>
      </div>

      {auditError ? (
        <div
          data-testid="org-audit-error"
          style={{
            color: '#991b1b',
            backgroundColor: '#fee2e2',
            border: '1px solid #fecaca',
            borderRadius: 8,
            padding: '10px 12px',
          }}
        >
          错误: {auditError}
        </div>
      ) : null}

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 560 }}>
          <thead>
            <tr>
              <th style={thStyle}>时间</th>
              <th style={thStyle}>类型</th>
              <th style={thStyle}>动作</th>
              <th style={thStyle}>变更内容</th>
              <th style={thStyle}>操作人</th>
            </tr>
          </thead>
          <tbody>
            {auditLogs.map((log) => (
              <tr key={log.id} data-testid={`org-audit-row-${log.id}`}>
                <td style={{ ...tdStyle, whiteSpace: 'nowrap', color: '#6b7280' }}>
                  {formatDateTime(log.created_at_ms)}
                </td>
                <td style={tdStyle}>{entityLabel(log.entity_type)}</td>
                <td style={tdStyle}>{actionLabel(log.action)}</td>
                <td style={tdStyle}>
                  <div data-testid={`org-audit-change-${log.id}`}>
                    <AuditChangeText log={log} />
                  </div>
                </td>
                <td style={tdStyle}>{log.actor_username || log.actor_user_id}</td>
              </tr>
            ))}
            {auditLogs.length === 0 ? (
              <tr>
                <td style={{ ...tdStyle, color: '#6b7280' }} colSpan={5}>
                  暂无记录
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
