import React from 'react';

const buttonStyle = (enabled, color) => ({
  padding: '8px 16px',
  backgroundColor: enabled ? color : '#9ca3af',
  color: 'white',
  border: 'none',
  borderRadius: '4px',
  cursor: enabled ? 'pointer' : 'not-allowed',
  fontSize: '0.9rem',
});

const ReviewToolbar = ({
  embedded,
  documents,
  datasets,
  selectedDataset,
  selectedDocIds,
  loadingDatasets,
  batchDownloadLoading,
  batchReviewLoading,
  canReview,
  canDownloadFiles,
  onSelectAll,
  onBatchApproveAll,
  onBatchRejectAll,
  onBatchDownload,
  onDatasetChange,
}) => {
  const hasDocuments = documents.length > 0;
  const allSelected = hasDocuments && selectedDocIds.size === documents.length;
  const canRunBatchDownload = selectedDocIds.size > 0 && !batchDownloadLoading && !batchReviewLoading;

  return (
    <div style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        {embedded ? <div /> : <h2 style={{ margin: 0 }}>文档审核</h2>}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={onSelectAll} disabled={!hasDocuments} style={buttonStyle(hasDocuments, allSelected ? '#6b7280' : '#3b82f6')}>
            {allSelected ? '取消全选' : '全选'}
          </button>

          {canReview && (
            <>
              <button onClick={onBatchApproveAll} disabled={!hasDocuments || !!batchReviewLoading} style={buttonStyle(hasDocuments && !batchReviewLoading, '#10b981')}>
                {batchReviewLoading === 'approve' ? '处理中...' : `全部通过 (${documents.length})`}
              </button>
              <button onClick={onBatchRejectAll} disabled={!hasDocuments || !!batchReviewLoading} style={buttonStyle(hasDocuments && !batchReviewLoading, '#ef4444')}>
                {batchReviewLoading === 'reject' ? '处理中...' : `全部驳回 (${documents.length})`}
              </button>
            </>
          )}

          {canDownloadFiles && (
            <button onClick={onBatchDownload} disabled={!canRunBatchDownload} style={buttonStyle(canRunBatchDownload, '#10b981')}>
              {batchDownloadLoading ? '下载中...' : `批量下载 (${selectedDocIds.size})`}
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
        <select
          value={selectedDataset === null ? '' : selectedDataset}
          onChange={(event) => onDatasetChange(event.target.value)}
          data-testid="docs-dataset-select"
          disabled={loadingDatasets}
          style={{
            padding: '8px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            fontSize: '0.95rem',
            backgroundColor: 'white',
            cursor: 'pointer',
          }}
        >
          {loadingDatasets ? (
            <option>加载中...</option>
          ) : datasets.length === 0 ? (
            <option>暂无知识库</option>
          ) : (
            <>
              <option value="">全部知识库</option>
              {datasets.map((dataset) => (
                <option key={dataset.id} value={dataset.name}>
                  {dataset.name}
                </option>
              ))}
            </>
          )}
        </select>
      </div>
    </div>
  );
};

export default ReviewToolbar;
