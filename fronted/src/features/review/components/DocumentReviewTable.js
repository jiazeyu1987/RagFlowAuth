import React from 'react';

export function DocumentReviewTable({
  actionLoading,
  canDownload,
  documents,
  downloadLoading,
  handleApprove,
  handleDelete,
  handleDownload,
  handleReject,
  handleSelectAll,
  handleSelectDoc,
  isAdmin,
  isReviewer,
  openLocalPreview,
  selectedDataset,
  selectedDocIds,
}) {
  const isAllSelected = documents.length > 0 && selectedDocIds.size === documents.length;

  if (documents.length === 0) {
    return (
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          overflow: 'hidden',
        }}
      >
        <div data-testid="docs-empty" style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
          {selectedDataset ? '当前知识库下没有待审核文档' : '暂无待审核文档'}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        overflow: 'hidden',
      }}
    >
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead style={{ backgroundColor: '#f9fafb' }}>
          <tr>
            <th style={{ padding: '12px 16px', textAlign: 'center', borderBottom: '1px solid #e5e7eb', width: '50px' }}>
              <input
                type="checkbox"
                checked={isAllSelected}
                onChange={handleSelectAll}
                disabled={documents.length === 0}
                style={{ cursor: documents.length === 0 ? 'not-allowed' : 'pointer' }}
              />
            </th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>文档名称</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>状态</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>知识库</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>上传人</th>
            <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>上传时间</th>
            <th style={{ padding: '12px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb' }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => {
            const isPending = doc.status === 'pending';
            const isLoading = actionLoading === doc.doc_id;
            const statusLabel = doc.status === 'pending'
              ? '待审核'
              : doc.status === 'approved'
                ? '已通过'
                : doc.status === 'rejected'
                  ? '已驳回'
                  : doc.status;
            const statusColor = doc.status === 'pending' ? '#f59e0b' : doc.status === 'approved' ? '#10b981' : '#6b7280';

            return (
              <tr key={doc.doc_id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                  <input
                    type="checkbox"
                    checked={selectedDocIds.has(doc.doc_id)}
                    onChange={() => handleSelectDoc(doc.doc_id)}
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
                      backgroundColor: statusColor,
                      color: 'white',
                      fontSize: '0.85rem',
                    }}
                  >
                    {statusLabel}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{doc.kb_id}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280' }}>{doc.uploaded_by_name || doc.uploaded_by}</td>
                <td style={{ padding: '12px 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                  {new Date(doc.uploaded_at_ms).toLocaleString('zh-CN')}
                </td>
                <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                  {isPending && (
                    <button
                      onClick={() => openLocalPreview(doc.doc_id, doc.filename)}
                      data-testid={`docs-preview-${String(doc.doc_id || '')}`}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#10b981',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        marginRight: '8px',
                      }}
                    >
                      查看
                    </button>
                  )}
                  {canDownload && (
                    <button
                      onClick={() => handleDownload(doc.doc_id)}
                      disabled={downloadLoading === doc.doc_id}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: downloadLoading === doc.doc_id ? '#9ca3af' : '#3b82f6',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: downloadLoading === doc.doc_id ? 'not-allowed' : 'pointer',
                        fontSize: '0.9rem',
                        marginRight: '8px',
                      }}
                    >
                      {downloadLoading === doc.doc_id ? '下载中...' : '下载'}
                    </button>
                  )}
                  {isPending && isReviewer ? (
                    <>
                      <button
                        onClick={() => handleApprove(doc.doc_id)}
                        disabled={isLoading}
                        data-testid={`docs-approve-${doc.doc_id}`}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: isLoading ? '#9ca3af' : '#10b981',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: isLoading ? 'not-allowed' : 'pointer',
                          fontSize: '0.9rem',
                          marginRight: '8px',
                        }}
                      >
                        {isLoading ? '处理中...' : '通过'}
                      </button>
                      <button
                        onClick={() => handleReject(doc.doc_id)}
                        disabled={isLoading}
                        data-testid={`docs-reject-${doc.doc_id}`}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: isLoading ? '#9ca3af' : '#ef4444',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: isLoading ? 'not-allowed' : 'pointer',
                          fontSize: '0.9rem',
                          marginRight: '8px',
                        }}
                      >
                        驳回
                      </button>
                    </>
                  ) : (
                    <span style={{ color: '#9ca3af', fontSize: '0.85rem', marginRight: '8px' }}>
                      {doc.status === 'approved' ? '已处理' : '不可审核'}
                    </span>
                  )}
                  {isAdmin && (
                    <button
                      onClick={() => handleDelete(doc.doc_id)}
                      disabled={isLoading}
                      data-testid={`docs-delete-${doc.doc_id}`}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: isLoading ? '#9ca3af' : '#dc2626',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: isLoading ? 'not-allowed' : 'pointer',
                        fontSize: '0.9rem',
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
    </div>
  );
}
