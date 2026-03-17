import React from 'react';

export function DocumentReviewToolbar({
  batchDownloadLoading,
  batchReviewLoading,
  canDownload,
  datasets,
  documents,
  embedded,
  handleBatchApproveAll,
  handleBatchDownload,
  handleBatchRejectAll,
  handleSelectAll,
  isReviewer,
  isMobile,
  loadingDatasets,
  selectedDataset,
  selectedDocIds,
  setSelectedDataset,
}) {
  const allSelected = documents.length > 0 && selectedDocIds.size === documents.length;

  return (
    <div style={{ marginBottom: '24px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'stretch' : 'center',
          flexDirection: isMobile ? 'column' : 'row',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        {embedded ? <div /> : <h2 style={{ margin: 0 }}>文档审核</h2>}
        <div
          style={{
            display: 'flex',
            gap: '8px',
            flexDirection: isMobile ? 'column' : 'row',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          <button
            onClick={handleSelectAll}
            disabled={documents.length === 0}
            style={{
              padding: '8px 16px',
              backgroundColor: allSelected ? '#6b7280' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: documents.length === 0 ? 'not-allowed' : 'pointer',
              fontSize: '0.9rem',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {allSelected ? '取消全选' : '全选'}
          </button>
          {isReviewer && (
            <>
              <button
                onClick={handleBatchApproveAll}
                disabled={documents.length === 0 || !!batchReviewLoading}
                style={{
                  padding: '8px 16px',
                  backgroundColor: documents.length > 0 && !batchReviewLoading ? '#10b981' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: documents.length > 0 && !batchReviewLoading ? 'pointer' : 'not-allowed',
                  fontSize: '0.9rem',
                  width: isMobile ? '100%' : 'auto',
                }}
              >
                {batchReviewLoading === 'approve' ? '处理中...' : `一键通过 (${documents.length})`}
              </button>
              <button
                onClick={handleBatchRejectAll}
                disabled={documents.length === 0 || !!batchReviewLoading}
                style={{
                  padding: '8px 16px',
                  backgroundColor: documents.length > 0 && !batchReviewLoading ? '#ef4444' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: documents.length > 0 && !batchReviewLoading ? 'pointer' : 'not-allowed',
                  fontSize: '0.9rem',
                  width: isMobile ? '100%' : 'auto',
                }}
              >
                {batchReviewLoading === 'reject' ? '处理中...' : `一键驳回 (${documents.length})`}
              </button>
            </>
          )}
          {canDownload && (
            <button
              onClick={handleBatchDownload}
              disabled={selectedDocIds.size === 0 || batchDownloadLoading || !!batchReviewLoading}
              style={{
                padding: '8px 16px',
                backgroundColor:
                  selectedDocIds.size > 0 && !batchDownloadLoading && !batchReviewLoading ? '#10b981' : '#9ca3af',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor:
                  selectedDocIds.size > 0 && !batchDownloadLoading && !batchReviewLoading ? 'pointer' : 'not-allowed',
                fontSize: '0.9rem',
                width: isMobile ? '100%' : 'auto',
              }}
            >
              {batchDownloadLoading ? '下载中...' : `批量下载 (${selectedDocIds.size})`}
            </button>
          )}
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          gap: '16px',
          alignItems: isMobile ? 'stretch' : 'center',
          flexDirection: isMobile ? 'column' : 'row',
        }}
      >
        <select
          value={selectedDataset === null ? '' : selectedDataset}
          onChange={(e) => setSelectedDataset(e.target.value)}
          data-testid="docs-dataset-select"
          disabled={loadingDatasets}
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
          {loadingDatasets ? (
            <option value="">加载中...</option>
          ) : (
            <>
              <option value="">全部知识库</option>
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.name}>
                  {ds.name}
                </option>
              ))}
            </>
          )}
        </select>
      </div>
    </div>
  );
}
