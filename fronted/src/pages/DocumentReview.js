import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import {
  countLines,
  fetchKnowledgePreviewText,
  isTextComparable,
} from '../features/review/documentReviewUtils';
import { useDocumentReviewData } from '../features/review/useDocumentReviewData';
import { useDocumentReviewActions } from '../features/review/useDocumentReviewActions';
import { DocumentReviewBatchSummary } from '../features/review/components/DocumentReviewBatchSummary';
import { DocumentReviewDiffModal } from '../features/review/components/DocumentReviewDiffModal';
import { DocumentReviewOverwriteModal } from '../features/review/components/DocumentReviewOverwriteModal';
import { DocumentReviewTable } from '../features/review/components/DocumentReviewTable';
import { DocumentReviewToolbar } from '../features/review/components/DocumentReviewToolbar';
import { useEscapeClose } from '../shared/hooks/useEscapeClose';
import { DOCUMENT_SOURCE } from '../shared/documents/documentClient';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

const MOBILE_BREAKPOINT = 768;

const DocumentReview = ({ embedded = false }) => {
  const { isReviewer, isAdmin, canDownload } = useAuth();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [error, setError] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffOnly, setDiffOnly] = useState(true);
  const [diffTitle, setDiffTitle] = useState('');
  const [diffOldText, setDiffOldText] = useState('');
  const [diffNewText, setDiffNewText] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const {
    datasets,
    documents,
    loading,
    loadingDatasets,
    refreshDocuments,
    selectedDataset,
    setSelectedDataset,
  } = useDocumentReviewData(setError);

  const activeDocMap = useMemo(() => {
    const map = new Map();
    for (const doc of documents) {
      map.set(doc.doc_id, doc);
    }
    return map;
  }, [documents]);

  const {
    actionLoading,
    batchDownloadLoading,
    batchReviewLoading,
    batchReviewSummary,
    batchSummaryCopied,
    batchSummaryExpanded,
    downloadLoading,
    handleApprove,
    handleBatchApproveAll,
    handleBatchDownload,
    handleBatchRejectAll,
    handleCopyBatchSummary,
    handleDelete,
    handleDownload,
    handleOverwriteKeepOld,
    handleOverwriteUseNew,
    handleReject,
    handleSelectAll,
    handleSelectDoc,
    overwritePrompt,
    selectedDocIds,
    setBatchSummaryExpanded,
    setOverwritePrompt,
  } = useDocumentReviewActions({
    activeDocMap,
    documents,
    refreshDocuments,
    setError,
  });

  const closePreview = useCallback(() => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  }, []);

  const closeDiff = useCallback(() => {
    setDiffOpen(false);
  }, []);
  useEscapeClose(diffOpen, closeDiff);

  const openDiff = useCallback(async (oldDocId, oldFilename, newDocId, newFilename) => {
    setError(null);
    setDiffTitle(`文档对比: ${oldFilename} vs ${newFilename}`);
    setDiffOpen(true);
    setDiffLoading(true);
    setDiffOldText('');
    setDiffNewText('');

    try {
      if (!isTextComparable(oldFilename) || !isTextComparable(newFilename)) {
        throw new Error('仅支持对 md、txt、ini、log 等文本文件进行对比');
      }

      const [oldText, newText] = await Promise.all([
        fetchKnowledgePreviewText(oldDocId),
        fetchKnowledgePreviewText(newDocId),
      ]);

      const maxLines = 2500;
      if (countLines(oldText) > maxLines || countLines(newText) > maxLines) {
        throw new Error('文档内容过长，暂不支持直接在页面中进行全文对比');
      }

      setDiffOldText(oldText);
      setDiffNewText(newText);
    } catch (err) {
      setDiffOpen(false);
      setError(err?.message || '加载文档对比失败');
    } finally {
      setDiffLoading(false);
    }
  }, []);

  const openLocalPreview = useCallback((docId, filename) => {
    setPreviewTarget({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId, filename });
    setPreviewOpen(true);
  }, []);

  const canDownloadFiles = !!canDownload();

  return (
    <div data-testid="document-review-page">
      <DocumentReviewOverwriteModal
        activeDocMap={activeDocMap}
        handleOverwriteKeepOld={handleOverwriteKeepOld}
        handleOverwriteUseNew={handleOverwriteUseNew}
        openDiff={openDiff}
        openLocalPreview={openLocalPreview}
        overwritePrompt={overwritePrompt}
        setOverwritePrompt={setOverwritePrompt}
      />

      <DocumentReviewDiffModal
        diffLoading={diffLoading}
        diffOldText={diffOldText}
        diffNewText={diffNewText}
        diffOnly={diffOnly}
        diffOpen={diffOpen}
        diffTitle={diffTitle}
        onClose={closeDiff}
        onDiffOnlyChange={setDiffOnly}
      />

      <DocumentPreviewModal
        open={previewOpen}
        target={previewTarget}
        onClose={closePreview}
        canDownloadFiles={canDownloadFiles}
      />

      <DocumentReviewToolbar
        batchDownloadLoading={batchDownloadLoading}
        batchReviewLoading={batchReviewLoading}
        canDownload={canDownloadFiles}
        datasets={datasets}
        documents={documents}
        embedded={embedded}
        handleBatchApproveAll={handleBatchApproveAll}
        handleBatchDownload={handleBatchDownload}
        handleBatchRejectAll={handleBatchRejectAll}
        handleSelectAll={handleSelectAll}
        isReviewer={isReviewer()}
        isMobile={isMobile}
        loadingDatasets={loadingDatasets}
        selectedDataset={selectedDataset}
        selectedDocIds={selectedDocIds}
        setSelectedDataset={setSelectedDataset}
      />

      {error ? (
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
          {error}
        </div>
      ) : null}

      <DocumentReviewBatchSummary
        batchReviewSummary={batchReviewSummary}
        batchSummaryCopied={batchSummaryCopied}
        batchSummaryExpanded={batchSummaryExpanded}
        handleCopyBatchSummary={handleCopyBatchSummary}
        isMobile={isMobile}
        setBatchSummaryExpanded={setBatchSummaryExpanded}
        setOverwritePrompt={setOverwritePrompt}
      />

      {loading ? (
        <div style={{ color: '#6b7280' }}>加载中...</div>
      ) : (
        <DocumentReviewTable
          actionLoading={actionLoading}
          canDownload={canDownloadFiles}
          documents={documents}
          downloadLoading={downloadLoading}
          handleApprove={handleApprove}
          handleDelete={handleDelete}
          handleDownload={handleDownload}
          handleReject={handleReject}
          handleSelectAll={handleSelectAll}
          handleSelectDoc={handleSelectDoc}
          isAdmin={isAdmin()}
          isMobile={isMobile}
          isReviewer={isReviewer()}
          openLocalPreview={openLocalPreview}
          selectedDataset={selectedDataset}
          selectedDocIds={selectedDocIds}
        />
      )}
    </div>
  );
};

export default DocumentReview;
