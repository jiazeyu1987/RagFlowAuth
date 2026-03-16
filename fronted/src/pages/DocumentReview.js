import React, { useCallback, useMemo, useState } from 'react';
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
import { normalizeDisplayError } from '../shared/utils/displayError';

const DocumentReview = ({ embedded = false }) => {
  const { isReviewer, isAdmin, canDownload } = useAuth();
  const [error, setError] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffOnly, setDiffOnly] = useState(true);
  const [diffTitle, setDiffTitle] = useState(null);
  const [diffOldText, setDiffOldText] = useState('');
  const [diffNewText, setDiffNewText] = useState('');

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
    const m = new Map();
    for (const d of documents) m.set(d.doc_id, d);
    return m;
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
    handleOverwriteRename,
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

  const closePreview = () => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  };

  const closeDiff = useCallback(() => {
    setDiffOpen(false);
  }, []);
  useEscapeClose(diffOpen, closeDiff);

  const openDiff = async (oldDocId, oldFilename, newDocId, newFilename) => {
    setError(null);
    setDiffTitle(`文档对比：${oldFilename} 与 ${newFilename}`);
    setDiffOpen(true);
    setDiffLoading(true);
    setDiffOldText('');
    setDiffNewText('');
    try {
      if (!isTextComparable(oldFilename) || !isTextComparable(newFilename)) {
        throw new Error('仅支持对比文本类文件');
      }
      const [oldText, newText] = await Promise.all([fetchKnowledgePreviewText(oldDocId), fetchKnowledgePreviewText(newDocId)]);
      const maxLines = 2500;
      if (countLines(oldText) > maxLines || countLines(newText) > maxLines) {
        throw new Error('文本过长，暂不支持对比超出限制行数的文件');
      }
      setDiffOldText(oldText);
      setDiffNewText(newText);
    } catch (e) {
      setDiffOpen(false);
      setError(normalizeDisplayError(e?.message ?? e, '加载对比内容失败'));
    } finally {
      setDiffLoading(false);
    }
  };

  const openLocalPreview = async (docId, filename) => {
    setPreviewTarget({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId, filename });
    setPreviewOpen(true);
  };

  return (
    <div data-testid="document-review-page">
      <DocumentReviewOverwriteModal
        activeDocMap={activeDocMap}
        handleOverwriteKeepOld={handleOverwriteKeepOld}
        handleOverwriteRename={handleOverwriteRename}
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
        onClose={() => setDiffOpen(false)}
        onDiffOnlyChange={setDiffOnly}
      />

      <DocumentPreviewModal open={previewOpen} target={previewTarget} onClose={closePreview} canDownloadFiles={!!canDownload()} />

      <DocumentReviewToolbar
        batchDownloadLoading={batchDownloadLoading}
        batchReviewLoading={batchReviewLoading}
        canDownload={canDownload()}
        datasets={datasets}
        documents={documents}
        embedded={embedded}
        handleBatchApproveAll={handleBatchApproveAll}
        handleBatchDownload={handleBatchDownload}
        handleBatchRejectAll={handleBatchRejectAll}
        handleSelectAll={handleSelectAll}
        isReviewer={isReviewer()}
        loadingDatasets={loadingDatasets}
        selectedDataset={selectedDataset}
        selectedDocIds={selectedDocIds}
        setSelectedDataset={setSelectedDataset}
      />

      {error && (
        <div data-testid="docs-error" style={{
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          padding: '12px 16px',
          borderRadius: '4px',
          marginBottom: '20px',
        }}>
          {error}
        </div>
      )}

      <DocumentReviewBatchSummary
        batchReviewSummary={batchReviewSummary}
        batchSummaryCopied={batchSummaryCopied}
        batchSummaryExpanded={batchSummaryExpanded}
        handleCopyBatchSummary={handleCopyBatchSummary}
        setBatchSummaryExpanded={setBatchSummaryExpanded}
        setOverwritePrompt={setOverwritePrompt}
      />

      {loading ? (
        <div>加载中...</div>
      ) : (
        <DocumentReviewTable
          actionLoading={actionLoading}
          canDownload={canDownload()}
          documents={documents}
          downloadLoading={downloadLoading}
          handleApprove={handleApprove}
          handleDelete={handleDelete}
          handleDownload={handleDownload}
          handleReject={handleReject}
          handleSelectAll={handleSelectAll}
          handleSelectDoc={handleSelectDoc}
          isAdmin={isAdmin()}
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
