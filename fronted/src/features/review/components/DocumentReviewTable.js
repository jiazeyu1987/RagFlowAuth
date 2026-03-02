import React from 'react';

const tableContainerStyle = {
  backgroundColor: 'white',
  borderRadius: '8px',
  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
  overflow: 'hidden',
};

const thStyle = {
  padding: '12px 16px',
  textAlign: 'left',
  borderBottom: '1px solid #e5e7eb',
};

const actionButtonStyle = {
  padding: '6px 12px',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.9rem',
  marginRight: '8px',
};

const statusLabel = (status) => {
  if (status === 'pending') return '待审核';
  if (status === 'approved') return '已通过';
  if (status === 'rejected') return '已驳回';
  return status;
};

const DocumentReviewTable = ({
  documents,
  loading,
  selectedDataset,
  selectedDocIds,
  actionLoading,
  downloadLoading,
  canDownloadFiles,
  canReview,
  canDelete,
  onSelectDoc,
  onSelectAll,
  onPreview,
  onDownload,
  onApprove,
  onReject,
  onDelete,
}) => {
  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div style={tableContainerStyle}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ backgroundColor: '#f9fafb' }}>
          <tr>
            <th style={{ ...thStyle, textAlign: 'center', width: '50px' }}>
              <input
                type="checkbox"
                checked={documents.length > 0 && selectedDocIds.size === documents.length}
                onChange={onSelectAll}
                disabled={documents.length === 0}
                style={{ cursor: documents.length === 0 ? 'not-allowed' : 'pointer' }}
              />
            </th>
            <th style={thStyle}>文件名称</th>
            <th style={thStyle}>状态</th>
            <th style={thStyle}>知识库</th>
            <th style={thStyle}>上传者</th>
            <th style={thStyle}>上传时间</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => {
            const rowBusy = actionLoading === doc.doc_id;
            const downloading = downloadLoading === doc.doc_id;
            return (
              <tr key={doc.doc_id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={selectedDocIds.has(doc.doc_id)}
                    onChange={() => onSelectDoc(doc.doc_id)}
                    style={{ cursor: 'pointer' }}
                  />
                </td>
                <td style={{ padding: '12px 16px' }}>{doc.filename}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span
                    style={{
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: doc.status === 'pending' ? '#f59e0b' : doc.status === 'approved' ? '#10b981' : '#ef4444',
                      color: 'white',
                      fontSize: '0.85rem',
                    }}
                  >
                    {statusLabel(doc.status)}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{doc.kb_id}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{doc.uploaded_by_name || doc.uploaded_by}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                  {new Date(doc.uploaded_at_ms).toLocaleString('zh-CN')}
                </td>
                <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                  {doc.status === 'pending' && (
                    <button
                      onClick={() => onPreview(doc.doc_id, doc.filename)}
                      data-testid={`docs-preview-${String(doc.doc_id || '')}`}
                      style={{ ...actionButtonStyle, backgroundColor: '#10b981' }}
                    >
                      预览
                    </button>
                  )}

                  {canDownloadFiles && (
                    <button
                      onClick={() => onDownload(doc.doc_id)}
                      disabled={downloading}
                      style={{
                        ...actionButtonStyle,
                        backgroundColor: downloading ? '#9ca3af' : '#3b82f6',
                        cursor: downloading ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {downloading ? '下载中...' : '下载'}
                    </button>
                  )}

                  {doc.status === 'pending' && canReview ? (
                    <>
                      <button
                        onClick={() => onApprove(doc.doc_id)}
                        disabled={rowBusy}
                        data-testid={`docs-approve-${doc.doc_id}`}
                        style={{
                          ...actionButtonStyle,
                          backgroundColor: rowBusy ? '#9ca3af' : '#10b981',
                          cursor: rowBusy ? 'not-allowed' : 'pointer',
                        }}
                      >
                        {rowBusy ? '处理中...' : '通过'}
                      </button>
                      <button
                        onClick={() => onReject(doc.doc_id)}
                        disabled={rowBusy}
                        data-testid={`docs-reject-${doc.doc_id}`}
                        style={{
                          ...actionButtonStyle,
                          backgroundColor: rowBusy ? '#9ca3af' : '#ef4444',
                          cursor: rowBusy ? 'not-allowed' : 'pointer',
                        }}
                      >
                        驳回
                      </button>
                    </>
                  ) : doc.status !== 'pending' ? (
                    <span style={{ color: '#9ca3af', fontSize: '0.85rem', marginRight: '8px' }}>
                      {doc.status === 'approved' ? '已审核' : '已处理'}
                    </span>
                  ) : null}

                  {canDelete && (
                    <button
                      onClick={() => onDelete(doc.doc_id)}
                      disabled={rowBusy}
                      data-testid={`docs-delete-${doc.doc_id}`}
                      style={{
                        ...actionButtonStyle,
                        marginRight: 0,
                        backgroundColor: rowBusy ? '#9ca3af' : '#dc2626',
                        cursor: rowBusy ? 'not-allowed' : 'pointer',
                      }}
                    >
                      删除
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {documents.length === 0 && (
        <div data-testid="docs-empty" style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
          {selectedDataset ? '当前知识库下暂无待审核文档' : '暂无待审核文档'}
        </div>
      )}
    </div>
  );
};

export default DocumentReviewTable;
