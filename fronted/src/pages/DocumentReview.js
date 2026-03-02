import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { useDocumentReview } from '../features/review/useDocumentReview';
import ReviewToolbar from '../features/review/components/ReviewToolbar';
import BatchSummaryCard from '../features/review/components/BatchSummaryCard';
import OverwriteModal from '../features/review/components/OverwriteModal';
import DiffModal from '../features/review/components/DiffModal';
import DocumentReviewTable from '../features/review/components/DocumentReviewTable';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';
import { useEscapeClose } from '../shared/hooks/useEscapeClose';

const DocumentReview = ({ embedded = false }) => {
  const { isReviewer, isAdmin, canDownload } = useAuth();
  const state = useDocumentReview();
  const canReview = isReviewer();
  const canDelete = isAdmin();
  const canDownloadFiles = !!canDownload();
  const overwriteNewDoc = state.overwritePrompt ? state.activeDocMap.get(state.overwritePrompt.newDocId) : null;
  useEscapeClose(state.diffOpen, state.closeDiff);

  return (
    <div>
      <OverwriteModal
        prompt={state.overwritePrompt}
        newDoc={overwriteNewDoc}
        onClose={() => state.setOverwritePrompt(null)}
        onPreview={state.openLocalPreview}
        onOpenDiff={state.openDiff}
        onKeepOld={state.handleOverwriteKeepOld}
        onUseNew={state.handleOverwriteUseNew}
      />

      <DiffModal
        open={state.diffOpen}
        title={state.diffTitle}
        loading={state.diffLoading}
        diffOnly={state.diffOnly}
        oldText={state.diffOldText}
        newText={state.diffNewText}
        onClose={state.closeDiff}
        onToggleDiffOnly={state.setDiffOnly}
      />

      <DocumentPreviewModal open={state.previewOpen} target={state.previewTarget} onClose={state.closePreview} canDownloadFiles={canDownloadFiles} />

      <ReviewToolbar
        embedded={embedded}
        documents={state.documents}
        datasets={state.datasets}
        selectedDataset={state.selectedDataset}
        selectedDocIds={state.selectedDocIds}
        loadingDatasets={state.loadingDatasets}
        batchDownloadLoading={state.batchDownloadLoading}
        batchReviewLoading={state.batchReviewLoading}
        canReview={canReview}
        canDownloadFiles={canDownloadFiles}
        onSelectAll={state.handleSelectAll}
        onBatchApproveAll={state.handleBatchApproveAll}
        onBatchRejectAll={state.handleBatchRejectAll}
        onBatchDownload={state.handleBatchDownload}
        onDatasetChange={state.setSelectedDataset}
      />

      {state.error && (
        <div
          data-testid="docs-error"
          style={{
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '12px 16px',
            borderRadius: '4px',
            marginBottom: '20px',
          }}
        >
          {state.error}
        </div>
      )}

      <BatchSummaryCard
        summary={state.batchReviewSummary}
        expanded={state.batchSummaryExpanded}
        copied={state.batchSummaryCopied}
        onToggleExpanded={() => state.setBatchSummaryExpanded((prev) => !prev)}
        onCopy={state.handleCopyBatchSummary}
        onResolveConflict={state.openConflictFromSummary}
      />

      <DocumentReviewTable
        documents={state.documents}
        loading={state.loading}
        selectedDataset={state.selectedDataset}
        selectedDocIds={state.selectedDocIds}
        actionLoading={state.actionLoading}
        downloadLoading={state.downloadLoading}
        canDownloadFiles={canDownloadFiles}
        canReview={canReview}
        canDelete={canDelete}
        onSelectDoc={state.handleSelectDoc}
        onSelectAll={state.handleSelectAll}
        onPreview={state.openLocalPreview}
        onDownload={state.handleDownload}
        onApprove={state.handleApprove}
        onReject={state.handleReject}
        onDelete={state.handleDelete}
      />
    </div>
  );
};

export default DocumentReview;
