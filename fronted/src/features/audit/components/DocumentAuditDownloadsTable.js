import React from 'react';
import { formatTime } from '../documentAuditHelpers';
import { BASE_HEADER_CELL_STYLE, getDownloadsEmptyText } from '../documentAuditView';

export default function DocumentAuditDownloadsTable({
  downloads,
  filterKb,
  resolveDisplayName,
}) {
  return (
    <>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1000px' }}>
          <thead style={{ backgroundColor: '#d1fae5' }}>
            <tr>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#065f46' }}>知识库</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#065f46' }}>文件名</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#065f46' }}>下载者</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#065f46' }}>下载时间</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#065f46' }}>类型</th>
            </tr>
          </thead>
          <tbody>
            {downloads.map((item, index) => (
              <tr
                key={item.id}
                data-testid={`audit-download-row-${item.id}`}
                style={{
                  borderBottom: '1px solid #e5e7eb',
                  backgroundColor: index % 2 === 0 ? 'white' : '#f0fdf4',
                }}
              >
                <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{item.kb_id}</td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{item.filename}</td>
                <td
                  style={{
                    padding: '12px 16px',
                    fontSize: '0.9rem',
                    color: '#059669',
                    fontWeight: '500',
                  }}
                >
                  {resolveDisplayName(item.downloaded_by, item.downloaded_by_name)}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                  {formatTime(item.downloaded_at_ms)}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      color: 'white',
                      fontSize: '0.85rem',
                      backgroundColor: item.is_batch ? '#059669' : '#10b981',
                    }}
                  >
                    {item.is_batch ? '批量下载' : '单个下载'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {downloads.length === 0 ? (
        <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
          {getDownloadsEmptyText(Boolean(filterKb))}
        </div>
      ) : null}
    </>
  );
}

