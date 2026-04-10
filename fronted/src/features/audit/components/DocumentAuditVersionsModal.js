import React from 'react';
import { formatTime } from '../documentAuditHelpers';
import {
  BASE_HEADER_CELL_STYLE,
  getEffectiveStatusLabel,
  getVersionLoadingText,
  getVersionsEmptyText,
} from '../documentAuditView';
import DocumentAuditSignatureManifest from './DocumentAuditSignatureManifest';

const getArchivedTimeText = (item, currentDocId) => {
  if (item?.archived_at_ms) {
    return formatTime(item.archived_at_ms);
  }
  if (item?.doc_id === currentDocId || item?.is_current) {
    return '当前版本未归档';
  }
  return '未记录归档时间';
};

export default function DocumentAuditVersionsModal({
  versionsDialog,
  onClose,
  resolveDisplayName,
}) {
  if (!versionsDialog.open) return null;

  return (
    <div
      data-testid="audit-versions-modal"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(17, 24, 39, 0.42)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        zIndex: 60,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 'min(1100px, 100%)',
          maxHeight: '88vh',
          backgroundColor: 'white',
          borderRadius: '12px',
          border: '1px solid #e5e7eb',
          padding: '16px',
          overflow: 'auto',
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 12,
            alignItems: 'flex-start',
            marginBottom: 12,
          }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>
              版本历史: {versionsDialog.doc?.filename || '-'}
            </div>
            <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: 6 }}>
              逻辑文档 ID: {versionsDialog.logicalDocId || '-'}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              color: '#374151',
            }}
          >
            关闭
          </button>
        </div>

        {versionsDialog.loading ? (
          <div style={{ padding: '24px 8px', color: '#6b7280' }}>{getVersionLoadingText()}</div>
        ) : versionsDialog.error ? (
          <div
            data-testid="audit-versions-error"
            style={{
              padding: '12px 14px',
              background: '#fee2e2',
              color: '#991b1b',
              borderRadius: 8,
            }}
          >
            {versionsDialog.error}
          </div>
        ) : versionsDialog.items.length === 0 ? (
          <div style={{ padding: '24px 8px', color: '#6b7280' }}>{getVersionsEmptyText()}</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1260px' }}>
              <thead style={{ backgroundColor: '#f9fafb' }}>
                <tr>
                  <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>版本</th>
                  <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>文件名</th>
                  <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>生效状态</th>
                  <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>上传者</th>
                  <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>上传时间</th>
                  <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>归档时间</th>
                  <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>电子签名</th>
                  <th style={{ ...BASE_HEADER_CELL_STYLE, color: '#374151' }}>SHA256</th>
                </tr>
              </thead>
              <tbody>
                {versionsDialog.items.map((item, index) => (
                  <tr
                    key={item.doc_id}
                    data-testid={`audit-version-row-${item.doc_id}`}
                    style={{
                      borderBottom: '1px solid #e5e7eb',
                      backgroundColor: index % 2 === 0 ? 'white' : '#f9fafb',
                    }}
                  >
                    <td style={{ padding: '12px 16px', fontWeight: 600 }}>v{item.version_no || 1}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{item.filename}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          padding: '4px 8px',
                          borderRadius: '999px',
                          backgroundColor:
                            item.doc_id === versionsDialog.currentDocId ? '#dcfce7' : '#f3f4f6',
                          color:
                            item.doc_id === versionsDialog.currentDocId ? '#166534' : '#374151',
                          fontSize: '0.85rem',
                        }}
                      >
                        {getEffectiveStatusLabel(item, versionsDialog.currentDocId)}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', color: '#6b7280' }}>
                      {resolveDisplayName(item.uploaded_by, item.uploaded_by_name)}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#6b7280' }}>
                      {formatTime(item.uploaded_at_ms)}
                    </td>
                    <td style={{ padding: '12px 16px', color: '#6b7280' }}>
                      {getArchivedTimeText(item, versionsDialog.currentDocId)}
                    </td>
                    <td style={{ padding: '12px 16px', minWidth: '260px' }}>
                      <DocumentAuditSignatureManifest item={item} />
                    </td>
                    <td
                      style={{
                        padding: '12px 16px',
                        fontFamily:
                          "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
                        fontSize: '0.82rem',
                        wordBreak: 'break-all',
                      }}
                    >
                      {item.file_sha256 || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
