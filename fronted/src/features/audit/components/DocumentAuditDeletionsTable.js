import React from 'react';
import { formatTime } from '../documentAuditHelpers';
import {
  BASE_HEADER_CELL_STYLE,
  OTHER_USER_TEXT,
  getDeletionsEmptyText,
} from '../documentAuditView';

export default function DocumentAuditDeletionsTable({
  deletions,
  filterKb,
  resolveDisplayName,
}) {
  return (
    <>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1000px' }}>
          <thead style={{ backgroundColor: '#fee2e2' }}>
            <tr>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#991b1b' }}>知识库</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#991b1b' }}>文件名</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#991b1b' }}>原上传者</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#991b1b' }}>原审核者</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#991b1b' }}>删除者</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#991b1b' }}>删除时间</th>
            </tr>
          </thead>
          <tbody>
            {deletions.map((item, index) => (
              <tr
                key={item.id}
                data-testid={`audit-deletion-row-${item.id}`}
                style={{
                  borderBottom: '1px solid #e5e7eb',
                  backgroundColor: index % 2 === 0 ? 'white' : '#fef2f2',
                }}
              >
                <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{item.kb_id}</td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{item.filename}</td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                  {resolveDisplayName(item.original_uploader, item.original_uploader_name)}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                  {item.original_reviewer
                    ? resolveDisplayName(item.original_reviewer, item.original_reviewer_name)
                    : OTHER_USER_TEXT}
                </td>
                <td
                  style={{
                    padding: '12px 16px',
                    fontSize: '0.9rem',
                    color: '#dc2626',
                    fontWeight: '500',
                  }}
                >
                  {resolveDisplayName(item.deleted_by, item.deleted_by_name)}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                  {formatTime(item.deleted_at_ms)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {deletions.length === 0 ? (
        <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
          {getDeletionsEmptyText(Boolean(filterKb))}
        </div>
      ) : null}
    </>
  );
}

