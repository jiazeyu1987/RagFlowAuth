import React from 'react';
import { formatTime } from '../documentAuditHelpers';
import {
  BASE_HEADER_CELL_STYLE,
  OTHER_USER_TEXT,
  STATUS_LABELS,
  STATUS_STYLES,
  getDocumentsEmptyText,
} from '../documentAuditView';
import DocumentAuditSignatureManifest from './DocumentAuditSignatureManifest';

export default function DocumentAuditDocumentsTable({
  documents,
  filterKb,
  filterStatus,
  resolveDisplayName,
  onOpenVersionsDialog,
}) {
  return (
    <>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1120px' }}>
          <thead style={{ backgroundColor: '#f9fafb' }}>
            <tr>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>知识库</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>文件名</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>上传者</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>审核者</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>状态</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>上传时间</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>审核时间</th>
              <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>版本历史</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc, index) => (
              <tr
                key={doc.doc_id}
                data-testid={`audit-doc-row-${doc.doc_id}`}
                style={{
                  borderBottom: '1px solid #e5e7eb',
                  backgroundColor: index % 2 === 0 ? 'white' : '#f9fafb',
                }}
              >
                <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{doc.kb_id}</td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{doc.filename}</td>
                <td style={{ display: 'none' }}>
                  <div style={{ fontWeight: 600 }}>v{doc.version_no || 1}</div>
                  <div style={{ color: '#6b7280', fontSize: '0.8rem', marginTop: 4 }}>
                    {doc.is_current === false ? '历史版本' : '当前记录'}
                  </div>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                  {resolveDisplayName(doc.uploaded_by, doc.uploaded_by_name)}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                  {doc.reviewed_by
                    ? resolveDisplayName(doc.reviewed_by, doc.reviewed_by_name)
                    : OTHER_USER_TEXT}
                </td>
                <td style={{ padding: '12px 16px' }}>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      color: 'white',
                      fontSize: '0.85rem',
                      ...(STATUS_STYLES[doc.status] || { backgroundColor: '#6b7280' }),
                    }}
                  >
                    {STATUS_LABELS[doc.status] || doc.status}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                  {formatTime(doc.uploaded_at_ms)}
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                  {doc.reviewed_at_ms ? formatTime(doc.reviewed_at_ms) : '-'}
                </td>
                <td style={{ display: 'none' }}>
                  <DocumentAuditSignatureManifest item={doc} />
                </td>
                <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>
                  <button
                    type="button"
                    onClick={() => onOpenVersionsDialog(doc)}
                    data-testid={`audit-doc-versions-${doc.doc_id}`}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#eff6ff',
                      color: '#1d4ed8',
                      border: '1px solid #bfdbfe',
                      borderRadius: '6px',
                      cursor: 'pointer',
                    }}
                  >
                    查看版本历史
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {documents.length === 0 ? (
        <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
          {getDocumentsEmptyText(Boolean(filterKb || filterStatus))}
        </div>
      ) : null}
    </>
  );
}

