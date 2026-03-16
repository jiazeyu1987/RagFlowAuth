import { useCallback, useState } from 'react';
import documentClient, { DOCUMENT_SOURCE } from '../../shared/documents/documentClient';
import { reviewApi } from './api';
import {
  buildApproveBatchSummary,
  buildBatchSummaryText,
  buildRejectBatchSummary,
  collectConflictChecks,
} from './documentReviewUtils';
import { normalizeDisplayError } from '../../shared/utils/displayError';

export function useDocumentReviewActions({
  activeDocMap,
  documents,
  refreshDocuments,
  setError,
}) {
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedDocIds, setSelectedDocIds] = useState(new Set());
  const [downloadLoading, setDownloadLoading] = useState(null);
  const [batchDownloadLoading, setBatchDownloadLoading] = useState(false);
  const [batchReviewLoading, setBatchReviewLoading] = useState(null);
  const [batchReviewSummary, setBatchReviewSummary] = useState(null);
  const [batchSummaryExpanded, setBatchSummaryExpanded] = useState(false);
  const [batchSummaryCopied, setBatchSummaryCopied] = useState(false);
  const [overwritePrompt, setOverwritePrompt] = useState(null);

  const resetBatchFeedback = useCallback(() => {
    setBatchReviewSummary(null);
    setBatchSummaryExpanded(false);
    setBatchSummaryCopied(false);
  }, []);

  const handleApprove = useCallback(async (docId) => {
    setError(null);
    setActionLoading(docId);
    try {
      const conflict = await reviewApi.getConflict(docId);
      if (conflict?.conflict && conflict?.existing) {
        setOverwritePrompt({ newDocId: docId, oldDoc: conflict.existing, normalized: conflict.normalized_name });
        return;
      }

      if (!window.confirm('确定要通过这个文档吗？')) return;
      await reviewApi.approve(docId);
      await refreshDocuments();
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '审核通过失败'));
    } finally {
      setActionLoading(null);
    }
  }, [refreshDocuments, setError]);

  const handleOverwriteUseNew = useCallback(async () => {
    if (!overwritePrompt) return;
    const { newDocId, oldDoc } = overwritePrompt;
    const ok = window.confirm(
      `确定用新文档覆盖旧文档吗？\n\n旧文档：${oldDoc.filename}\n新文档：${activeDocMap.get(newDocId)?.filename || ''}\n\n该操作会将旧文档替换为新文档，并通过当前待审核文档。`,
    );
    if (!ok) return;

    const overwriteReason = window.prompt('请输入覆盖原因');
    if (overwriteReason === null) return;
    const normalizedReason = String(overwriteReason || '').trim();
    if (!normalizedReason) {
      setError('覆盖原因不能为空');
      return;
    }

    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.approveOverwrite(newDocId, oldDoc.doc_id, normalizedReason);
      setOverwritePrompt(null);
      await refreshDocuments();
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '覆盖文档失败'));
    } finally {
      setActionLoading(null);
    }
  }, [activeDocMap, overwritePrompt, refreshDocuments, setError]);

  const handleOverwriteKeepOld = useCallback(async () => {
    if (!overwritePrompt) return;
    const { newDocId, oldDoc } = overwritePrompt;
    const ok = window.confirm(`确定保留旧文档 ${oldDoc.filename} 并跳过新文档吗？`);
    if (!ok) return;

    const skipReason = window.prompt('请输入跳过原因（可选）');
    if (skipReason === null) return;

    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.resolveConflictSkip(newDocId, String(skipReason || '').trim() || null);
      setOverwritePrompt(null);
      await refreshDocuments();
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '跳过冲突失败'));
    } finally {
      setActionLoading(null);
    }
  }, [overwritePrompt, refreshDocuments, setError]);

  const handleOverwriteRename = useCallback(async () => {
    if (!overwritePrompt) return;
    const { newDocId } = overwritePrompt;
    const currentFilename = String(activeDocMap.get(newDocId)?.filename || '').trim();
    const renamed = window.prompt('请输入新的文件名', currentFilename);
    if (renamed === null) return;
    const normalizedFilename = String(renamed || '').trim();
    if (!normalizedFilename) {
      setError('文件名不能为空');
      return;
    }

    const renameReason = window.prompt('请输入重命名原因（可选）');
    if (renameReason === null) return;

    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.resolveConflictRename(newDocId, normalizedFilename, String(renameReason || '').trim() || null);
      setOverwritePrompt(null);
      await refreshDocuments();
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '重命名文档失败'));
    } finally {
      setActionLoading(null);
    }
  }, [activeDocMap, overwritePrompt, refreshDocuments, setError]);

  const handleReject = useCallback(async (docId) => {
    const notes = window.prompt('请输入驳回原因');
    if (notes === null) return;

    setActionLoading(docId);
    try {
      await reviewApi.reject(docId, notes);
      await refreshDocuments();
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '驳回文档失败'));
    } finally {
      setActionLoading(null);
    }
  }, [refreshDocuments, setError]);

  const handleDelete = useCallback(async (docId) => {
    if (!window.confirm('确定要删除这个文档吗？删除后不可恢复。')) return;

    setActionLoading(docId);
    try {
      await documentClient.delete({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
      await refreshDocuments();
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '删除文档失败'));
    } finally {
      setActionLoading(null);
    }
  }, [refreshDocuments, setError]);

  const handleDownload = useCallback(async (docId) => {
    setDownloadLoading(docId);
    try {
      await documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '批量下载失败'));
    } finally {
      setDownloadLoading(null);
    }
  }, [setError]);

  const handleSelectDoc = useCallback((docId) => {
    setSelectedDocIds((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedDocIds((prev) => (
      prev.size === documents.length ? new Set() : new Set(documents.map((doc) => doc.doc_id))
    ));
  }, [documents]);

  const handleBatchDownload = useCallback(async () => {
    if (selectedDocIds.size === 0) {
      setError('请先选择要下载的文档。');
      return;
    }

    setBatchDownloadLoading(true);
    try {
      await documentClient.batchDownloadKnowledgeToBrowser(Array.from(selectedDocIds));
      setSelectedDocIds(new Set());
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '批量审核失败'));
    } finally {
      setBatchDownloadLoading(false);
    }
  }, [selectedDocIds, setError]);

  const handleBatchApproveAll = useCallback(async () => {
    if (documents.length === 0) {
      setError('当前没有待审核文档。');
      return;
    }
    if (!window.confirm(`确定要一键通过当前列表中的 ${documents.length} 个待审核文档吗？`)) return;

    setBatchReviewLoading('approve');
    resetBatchFeedback();
    setError(null);
    try {
      const conflictChecks = await collectConflictChecks(documents, reviewApi);
      const conflicted = conflictChecks.filter((item) => item.conflict?.conflict && item.conflict?.existing);
      const conflictCheckFailed = conflictChecks.filter((item) => item.conflictError);
      const approvableDocs = conflictChecks
        .filter((item) => !item.conflictError && !(item.conflict?.conflict && item.conflict?.existing))
        .map((item) => item.doc);

      if (approvableDocs.length === 0) {
        const firstConflict = conflicted[0]?.doc?.filename || conflictCheckFailed[0]?.doc?.filename || '';
        setBatchReviewSummary(
          buildApproveBatchSummary(conflictChecks, {
            success_count: 0,
            failed_count: 0,
            failed_items: [],
          }),
        );
        setError(
          `批量审核未执行：冲突 ${conflicted.length}，检查失败 ${conflictCheckFailed.length}${firstConflict ? `。首个文档：${firstConflict}` : ''}`,
        );
        return;
      }

      const result = await reviewApi.approveBatch(approvableDocs.map((doc) => doc.doc_id));
      setBatchReviewSummary(buildApproveBatchSummary(conflictChecks, result));
      await refreshDocuments();
      setSelectedDocIds(new Set());
      if (result.failed_count > 0 || conflicted.length > 0 || conflictCheckFailed.length > 0) {
        const firstFailure = result.failed_items?.[0];
        const firstConflict = conflicted[0]?.doc?.filename || conflictCheckFailed[0]?.doc?.filename || '';
        setError(
          `批量审核完成：成功 ${result.success_count}，失败 ${result.failed_count}，冲突跳过 ${conflicted.length}，检查失败 ${conflictCheckFailed.length}${firstFailure ? `。首个失败：${firstFailure.doc_id} - ${normalizeDisplayError(firstFailure.detail, '请查看详情')}` : firstConflict ? `。首个跳过：${firstConflict}` : ''}`,
        );
      }
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '批量驳回失败'));
    } finally {
      setBatchReviewLoading(null);
    }
  }, [documents, refreshDocuments, resetBatchFeedback, setError]);

  const handleBatchRejectAll = useCallback(async () => {
    if (documents.length === 0) {
      setError('当前没有待审核文档。');
      return;
    }
    const notes = window.prompt('请输入批量驳回原因（可选）');
    if (notes === null) return;
    if (!window.confirm(`确定要一键驳回当前列表中的 ${documents.length} 个待审核文档吗？`)) return;

    setBatchReviewLoading('reject');
    resetBatchFeedback();
    setError(null);
    try {
      const result = await reviewApi.rejectBatch(documents.map((doc) => doc.doc_id), notes);
      setBatchReviewSummary(buildRejectBatchSummary(result));
      await refreshDocuments();
      setSelectedDocIds(new Set());
      if (result.failed_count > 0) {
        const firstFailure = result.failed_items?.[0];
        setError(`批量驳回完成：成功 ${result.success_count}，失败 ${result.failed_count}${firstFailure ? `。首个失败：${firstFailure.doc_id} - ${normalizeDisplayError(firstFailure.detail, '请查看详情')}` : ''}`);
      }
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '批量驳回失败'));
    } finally {
      setBatchReviewLoading(null);
    }
  }, [documents, refreshDocuments, resetBatchFeedback, setError]);

  const handleCopyBatchSummary = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(buildBatchSummaryText(batchReviewSummary));
      setBatchSummaryCopied(true);
      window.setTimeout(() => setBatchSummaryCopied(false), 1500);
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '复制失败'));
    }
  }, [batchReviewSummary, setError]);

  return {
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
  };
}
