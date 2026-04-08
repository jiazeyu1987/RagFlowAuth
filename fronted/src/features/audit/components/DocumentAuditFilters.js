import React from 'react';
import { getCountLabel } from '../documentAuditView';

export default function DocumentAuditFilters({
  isMobile,
  activeTab,
  knowledgeBases,
  filterKb,
  filterStatus,
  filteredDocumentsCount,
  filteredDeletionsCount,
  filteredDownloadsCount,
  onFilterKbChange,
  onFilterStatusChange,
  onResetFilters,
}) {
  const withStatus = activeTab === 'documents';
  const showReset = withStatus ? Boolean(filterKb || filterStatus) : Boolean(filterKb);
  const count = withStatus
    ? filteredDocumentsCount
    : activeTab === 'deletions'
      ? filteredDeletionsCount
      : filteredDownloadsCount;

  return (
    <div
      style={{
        display: 'flex',
        gap: '16px',
        alignItems: isMobile ? 'stretch' : 'center',
        flexDirection: isMobile ? 'column' : 'row',
        flexWrap: 'wrap',
      }}
    >
      <div>
        <label style={{ marginRight: '8px', fontSize: '0.9rem', color: '#6b7280' }}>
          知识库
        </label>
        <select
          value={filterKb}
          onChange={(event) => onFilterKbChange(event.target.value)}
          data-testid={withStatus ? 'audit-filter-kb' : undefined}
          style={{
            padding: '8px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            fontSize: '0.95rem',
            backgroundColor: 'white',
            cursor: 'pointer',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          <option value="">全部知识库</option>
          {knowledgeBases.map((kb) => (
            <option key={kb} value={kb}>
              {kb}
            </option>
          ))}
        </select>
      </div>

      {withStatus ? (
        <div>
          <label style={{ marginRight: '8px', fontSize: '0.9rem', color: '#6b7280' }}>
            状态
          </label>
          <select
            value={filterStatus}
            onChange={(event) => onFilterStatusChange(event.target.value)}
            data-testid="audit-filter-status"
            style={{
              padding: '8px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              fontSize: '0.95rem',
              backgroundColor: 'white',
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            <option value="">全部状态</option>
            <option value="pending">待审核</option>
            <option value="approved">已通过</option>
            <option value="rejected">已驳回</option>
          </select>
        </div>
      ) : null}

      {showReset ? (
        <button
          type="button"
          onClick={onResetFilters}
          data-testid={withStatus ? 'audit-filter-reset' : undefined}
          style={{
            padding: '8px 16px',
            backgroundColor: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.9rem',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          重置
        </button>
      ) : null}

      <span
        style={{
          marginLeft: isMobile ? 0 : 'auto',
          fontSize: '0.9rem',
          color: '#6b7280',
          alignSelf: isMobile ? 'flex-start' : 'auto',
        }}
      >
        {getCountLabel(count)}
      </span>
    </div>
  );
}

