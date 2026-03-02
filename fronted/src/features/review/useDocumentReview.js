import { useCallback, useEffect, useMemo, useState } from 'react';
import { reviewApi } from './api';
import { knowledgeApi } from '../knowledge/api';
import documentClient, { DOCUMENT_SOURCE } from '../../shared/documents/documentClient';
import { countLines, isTextComparable } from './utils';

const buildConflictSummaryItem = (item) => ({
  docId: item.doc.doc_id,
  filename: item.doc.filename,
  detail: item.conflict?.existing?.filename ? `与已通过文档重名：${item.conflict.existing.filename}` : '检测到命名冲突',
  existing: item.conflict?.existing || null,
  normalized: item.conflict?.normalized_name || '',
});

const buildConflictCheckFailedItem = (item) => ({
  docId: item.doc.doc_id,
  filename: item.doc.filename,
  detail: item.conflictError,
});

export const useDocumentReview = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedDocIds, setSelectedDocIds] = useState(new Set());
  const [downloadLoading, setDownloadLoading] = useState(null);
  const [batchDownloadLoading, setBatchDownloadLoading] = useState(false);
  const [batchReviewLoading, setBatchReviewLoading] = useState(null);
  const [batchReviewSummary, setBatchReviewSummary] = useState(null);
  const [batchSummaryExpanded, setBatchSummaryExpanded] = useState(false);
  const [batchSummaryCopied, setBatchSummaryCopied] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [overwritePrompt, setOverwritePrompt] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffOnly, setDiffOnly] = useState(true);
  const [diffTitle, setDiffTitle] = useState(null);
  const [diffOldText, setDiffOldText] = useState('');
  const [diffNewText, setDiffNewText] = useState('');

  const activeDocMap = useMemo(() => {
    const map = new Map();
    for (const document of documents) map.set(document.doc_id, document);
    return map;
  }, [documents]);

  const closePreview = useCallback(() => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  }, []);

  const closeDiff = useCallback(() => {
    setDiffOpen(false);
  }, []);

  const openLocalPreview = useCallback((docId, filename) => {
    setPreviewTarget({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId, filename });
    setPreviewOpen(true);
  }, []);

  const fetchLocalPreviewText = useCallback(async (docId) => {
    const data = await documentClient.preview({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
    if (data?.type !== 'text') {
      throw new Error(data?.message || '预览失败：仅支持文本文件');
    }
    return String(data.content || '');
  }, []);

  const openDiff = useCallback(async (oldDocId, oldFilename, newDocId, newFilename) => {
    setError(null);
    setDiffTitle(`文件差异：${oldFilename} vs ${newFilename}`);
    setDiffOpen(true);
    setDiffLoading(true);
    setDiffOldText('');
    setDiffNewText('');

    try {
      if (!isTextComparable(oldFilename) || !isTextComparable(newFilename)) {
        throw new Error('仅支持对比 md/txt/ini/log 文本文件');
      }

      const [oldText, newText] = await Promise.all([fetchLocalPreviewText(oldDocId), fetchLocalPreviewText(newDocId)]);
      const maxLines = 2500;
      if (countLines(oldText) > maxLines || countLines(newText) > maxLines) {
        throw new Error('文件过大，暂不支持在线差异对比，请下载后本地比较');
      }

      setDiffOldText(oldText);
      setDiffNewText(newText);
    } catch (err) {
      setDiffOpen(false);
      setError(err.message || '差异对比失败');
    } finally {
      setDiffLoading(false);
    }
  }, [fetchLocalPreviewText]);

  const fetchDocuments = useCallback(async () => {
    if (selectedDataset === null) return;

    try {
      setLoading(true);
      const params = selectedDataset === '' ? { status: 'pending' } : { status: 'pending', kb_id: selectedDataset };
      const data = await knowledgeApi.listLocalDocuments(params);
      setDocuments(Array.isArray(data?.documents) ? data.documents : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedDataset]);

  useEffect(() => {
    const loadDatasets = async () => {
      try {
        setLoadingDatasets(true);
        const data = await knowledgeApi.listRagflowDatasets();
        const nextDatasets = Array.isArray(data?.datasets) ? data.datasets : [];
        setDatasets(nextDatasets);
        if (nextDatasets.length > 0) {
          setSelectedDataset('');
        } else {
          setError('当前没有可用知识库，无法加载待审核文档');
        }
      } catch (err) {
        setError('加载知识库失败');
        setDatasets([]);
      } finally {
        setLoadingDatasets(false);
      }
    };

    loadDatasets();
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  useEffect(() => {
    setSelectedDocIds((prev) => {
      if (prev.size === 0) return prev;
      const validIds = new Set(documents.map((document) => document.doc_id));
      const next = new Set([...prev].filter((docId) => validIds.has(docId)));
      return next.size === prev.size ? prev : next;
    });
  }, [documents]);

  const handleApprove = useCallback(async (docId) => {
    setError(null);
    setActionLoading(docId);
    try {
      const conflict = await reviewApi.getConflict(docId);
      if (conflict?.conflict && conflict?.existing) {
        setOverwritePrompt({ newDocId: docId, oldDoc: conflict.existing, normalized: conflict.normalized_name });
        return;
      }

      if (!window.confirm('确认通过该文档吗？')) return;
      await reviewApi.approve(docId);
      await fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [fetchDocuments]);

  const handleOverwriteUseNew = useCallback(async () => {
    if (!overwritePrompt) return;

    const { newDocId, oldDoc } = overwritePrompt;
    const ok = window.confirm(
      `确认使用新文档覆盖已存在文档吗？\n\n旧文档：${oldDoc.filename}\n新文档：${activeDocMap.get(newDocId)?.filename || ''}\n\n该操作会保留新文档并替换旧文档内容。`
    );
    if (!ok) return;

    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.approveOverwrite(newDocId, oldDoc.doc_id);
      setOverwritePrompt(null);
      await fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [activeDocMap, fetchDocuments, overwritePrompt]);

  const handleOverwriteKeepOld = useCallback(async () => {
    if (!overwritePrompt) return;

    const { newDocId, oldDoc } = overwritePrompt;
    const ok = window.confirm(`确认保留旧文档 ${oldDoc.filename} 并驳回新文档吗？`);
    if (!ok) return;

    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.reject(newDocId, '与已通过文档冲突，保留旧版本');
      setOverwritePrompt(null);
      await fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [fetchDocuments, overwritePrompt]);

  const handleReject = useCallback(async (docId) => {
    const notes = window.prompt('请输入驳回原因');
    if (notes === null) return;

    setActionLoading(docId);
    try {
      await reviewApi.reject(docId, notes);
      await fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [fetchDocuments]);

  const handleDelete = useCallback(async (docId) => {
    if (!window.confirm('确认删除该文档吗？删除后不可恢复。')) return;

    setActionLoading(docId);
    try {
      await documentClient.delete({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
      await fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [fetchDocuments]);

  const handleDownload = useCallback(async (docId) => {
    setDownloadLoading(docId);
    try {
      await documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloadLoading(null);
    }
  }, []);

  const handleSelectDoc = useCallback((docId) => {
    setSelectedDocIds((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) next.delete(docId);
      else next.add(docId);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedDocIds((prev) => {
      if (prev.size === documents.length) return new Set();
      return new Set(documents.map((document) => document.doc_id));
    });
  }, [documents]);

  const handleBatchDownload = useCallback(async () => {
    if (selectedDocIds.size === 0) {
      setError('请先选择要下载的文档');
      return;
    }

    setBatchDownloadLoading(true);
    try {
      await documentClient.batchDownloadKnowledgeToBrowser(Array.from(selectedDocIds));
      setSelectedDocIds(new Set());
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchDownloadLoading(false);
    }
  }, [selectedDocIds]);

  const resetBatchSummaryState = useCallback(() => {
    setBatchReviewSummary(null);
    setBatchSummaryExpanded(false);
    setBatchSummaryCopied(false);
  }, []);

  const handleBatchApproveAll = useCallback(async () => {
    if (documents.length === 0) {
      setError('当前没有待审核文档。');
      return;
    }
    if (!window.confirm(`确认一键通过当前列表中的 ${documents.length} 个待审核文档吗？`)) return;

    setBatchReviewLoading('approve');
    resetBatchSummaryState();
    setError(null);
    try {
      const conflictChecks = await Promise.all(
        documents.map(async (doc) => {
          try {
            const conflict = await reviewApi.getConflict(doc.doc_id);
            return { doc, conflict };
          } catch (err) {
            return { doc, conflictError: err.message || '冲突检查失败' };
          }
        })
      );

      const conflicted = conflictChecks.filter((item) => item.conflict?.conflict && item.conflict?.existing);
      const conflictCheckFailed = conflictChecks.filter((item) => item.conflictError);
      const approvableDocs = conflictChecks
        .filter((item) => !item.conflictError && !(item.conflict?.conflict && item.conflict?.existing))
        .map((item) => item.doc);

      if (approvableDocs.length === 0) {
        const firstConflict = conflicted[0]?.doc?.filename || conflictCheckFailed[0]?.doc?.filename || '';
        setBatchReviewSummary({
          mode: 'approve',
          successCount: 0,
          failedCount: 0,
          conflicted: conflicted.map(buildConflictSummaryItem),
          checkFailed: conflictCheckFailed.map(buildConflictCheckFailedItem),
          failedItems: [],
        });
        setError(`批量审核未执行：冲突 ${conflicted.length}，检查失败 ${conflictCheckFailed.length}${firstConflict ? `。首个文档：${firstConflict}` : ''}`);
        return;
      }

      const result = await reviewApi.approveBatch(approvableDocs.map((doc) => doc.doc_id));
      setBatchReviewSummary({
        mode: 'approve',
        successCount: result.success_count,
        failedCount: result.failed_count,
        conflicted: conflicted.map(buildConflictSummaryItem),
        checkFailed: conflictCheckFailed.map(buildConflictCheckFailedItem),
        failedItems: result.failed_items || [],
      });

      await fetchDocuments();
      setSelectedDocIds(new Set());

      if (result.failed_count > 0 || conflicted.length > 0 || conflictCheckFailed.length > 0) {
        const firstFailure = result.failed_items?.[0];
        const firstConflict = conflicted[0]?.doc?.filename || conflictCheckFailed[0]?.doc?.filename || '';
        setError(
          `批量审核完成：成功 ${result.success_count}，失败 ${result.failed_count}，冲突跳过 ${conflicted.length}，检查失败 ${conflictCheckFailed.length}${
            firstFailure ? `。首个失败：${firstFailure.doc_id} - ${firstFailure.detail}` : firstConflict ? `。首个跳过：${firstConflict}` : ''
          }`
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchReviewLoading(null);
    }
  }, [documents, fetchDocuments, resetBatchSummaryState]);

  const handleBatchRejectAll = useCallback(async () => {
    if (documents.length === 0) {
      setError('当前没有待审核文档。');
      return;
    }

    const notes = window.prompt('请输入批量驳回原因（可选）');
    if (notes === null) return;
    if (!window.confirm(`确认一键驳回当前列表中的 ${documents.length} 个待审核文档吗？`)) return;

    setBatchReviewLoading('reject');
    resetBatchSummaryState();
    setError(null);
    try {
      const result = await reviewApi.rejectBatch(documents.map((doc) => doc.doc_id), notes);
      setBatchReviewSummary({
        mode: 'reject',
        successCount: result.success_count,
        failedCount: result.failed_count,
        conflicted: [],
        checkFailed: [],
        failedItems: result.failed_items || [],
      });

      await fetchDocuments();
      setSelectedDocIds(new Set());

      if (result.failed_count > 0) {
        const firstFailure = result.failed_items?.[0];
        setError(`批量驳回完成：成功 ${result.success_count}，失败 ${result.failed_count}${firstFailure ? `。首个失败：${firstFailure.doc_id} - ${firstFailure.detail}` : ''}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchReviewLoading(null);
    }
  }, [documents, fetchDocuments, resetBatchSummaryState]);

  const buildBatchSummaryText = useCallback(() => {
    if (!batchReviewSummary) return '';

    const lines = [
      batchReviewSummary.mode === 'approve' ? '批量审核明细' : '批量驳回明细',
      `成功 ${batchReviewSummary.successCount}，失败 ${batchReviewSummary.failedCount}，冲突跳过 ${batchReviewSummary.conflicted.length}，检查失败 ${batchReviewSummary.checkFailed.length}`,
    ];

    if (batchReviewSummary.failedItems.length > 0) {
      lines.push('失败项');
      batchReviewSummary.failedItems.forEach((item) => lines.push(`${item.doc_id}: ${item.detail}`));
    }
    if (batchReviewSummary.conflicted.length > 0) {
      lines.push('冲突跳过');
      batchReviewSummary.conflicted.forEach((item) => lines.push(`${item.filename}: ${item.detail}`));
    }
    if (batchReviewSummary.checkFailed.length > 0) {
      lines.push('检查失败');
      batchReviewSummary.checkFailed.forEach((item) => lines.push(`${item.filename}: ${item.detail}`));
    }

    return lines.join('\n');
  }, [batchReviewSummary]);

  const handleCopyBatchSummary = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(buildBatchSummaryText());
      setBatchSummaryCopied(true);
      window.setTimeout(() => setBatchSummaryCopied(false), 1500);
    } catch (err) {
      setError(err.message || '复制失败');
    }
  }, [buildBatchSummaryText]);

  const openConflictFromSummary = useCallback((item) => {
    if (!item?.existing) return;
    setOverwritePrompt({
      newDocId: item.docId,
      oldDoc: item.existing,
      normalized: item.normalized || '',
    });
  }, []);

  return {
    documents,
    loading,
    error,
    actionLoading,
    selectedDocIds,
    downloadLoading,
    batchDownloadLoading,
    batchReviewLoading,
    batchReviewSummary,
    batchSummaryExpanded,
    batchSummaryCopied,
    datasets,
    selectedDataset,
    loadingDatasets,
    overwritePrompt,
    previewOpen,
    previewTarget,
    diffOpen,
    diffLoading,
    diffOnly,
    diffTitle,
    diffOldText,
    diffNewText,
    activeDocMap,
    closePreview,
    closeDiff,
    setDiffOnly,
    setSelectedDataset,
    setBatchSummaryExpanded,
    setOverwritePrompt,
    openLocalPreview,
    openDiff,
    handleApprove,
    handleOverwriteUseNew,
    handleOverwriteKeepOld,
    handleReject,
    handleDelete,
    handleDownload,
    handleSelectDoc,
    handleSelectAll,
    handleBatchDownload,
    handleBatchApproveAll,
    handleBatchRejectAll,
    handleCopyBatchSummary,
    openConflictFromSummary,
  };
};
