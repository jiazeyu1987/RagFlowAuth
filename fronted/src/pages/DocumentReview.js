import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { reviewApi } from '../features/review/api';
import { knowledgeApi } from '../features/knowledge/api';
import ReactDiffViewer from 'react-diff-viewer-continued';
import { useEscapeClose } from '../shared/hooks/useEscapeClose';
import documentClient, { DOCUMENT_SOURCE } from '../shared/documents/documentClient';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';


const DocumentReview = ({ embedded = false }) => {
  const { user, isReviewer, isAdmin, canDownload } = useAuth();
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
  const [selectedDataset, setSelectedDataset] = useState(null); // null=鏈姞杞斤紱''=鍏ㄩ儴锛涘叾瀹?鐭ヨ瘑搴?
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [overwritePrompt, setOverwritePrompt] = useState(null); // { newDocId, oldDoc, normalized }
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffOnly, setDiffOnly] = useState(true);
  const [diffTitle, setDiffTitle] = useState(null);
  const [diffOldText, setDiffOldText] = useState('');
  const [diffNewText, setDiffNewText] = useState('');

  const activeDocMap = useMemo(() => {
    const m = new Map();
    for (const d of documents) m.set(d.doc_id, d);
    return m;
  }, [documents]);
  const closePreview = () => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  };

  const closeDiff = useCallback(() => {
    setDiffOpen(false);
  }, []);
  useEscapeClose(diffOpen, closeDiff);

  const isMarkdownFile = (filename) => {
    if (!filename) return false;
    const ext = filename.toLowerCase().split('.').pop();
    return ext === 'md' || ext === 'markdown';
  };

  const isPlainTextFile = (filename) => {
    if (!filename) return false;
    const ext = filename.toLowerCase().split('.').pop();
    return ext === 'txt' || ext === 'ini' || ext === 'log';
  };

  const isTextComparable = (filename) => isMarkdownFile(filename) || isPlainTextFile(filename);

  const countLines = (s) => {
    const t = String(s || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    if (!t) return 0;
    return t.split('\n').length;
  };
  const fetchLocalPreviewText = async (docId) => {
    const data = await documentClient.preview({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
    if (data?.type !== 'text') {
      throw new Error(data?.message || 'Preview failed: not a text document');
    }
    return String(data.content || '');
  };

  const openDiff = async (oldDocId, oldFilename, newDocId, newFilename) => {
    setError(null);
    setDiffTitle(`???${oldFilename} vs ${newFilename}`);
    setDiffOpen(true);
    setDiffLoading(true);
    setDiffOldText('');
    setDiffNewText('');
    try {
      if (!isTextComparable(oldFilename) || !isTextComparable(newFilename)) {
        throw new Error('????????md/txt/ini/log');
      }
      const [oldText, newText] = await Promise.all([fetchLocalPreviewText(oldDocId), fetchLocalPreviewText(newDocId)]);
      const maxLines = 2500;
      if (countLines(oldText) > maxLines || countLines(newText) > maxLines) {
        throw new Error('????????????????????????');
      }
      setDiffOldText(oldText);
      setDiffNewText(newText);
    } catch (e) {
      setDiffOpen(false);
      setError(e.message || '????');
    } finally {
      setDiffLoading(false);
    }
  };
  const openLocalPreview = async (docId, filename) => {
    setPreviewTarget({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId, filename });
    setPreviewOpen(true);
  };

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        setLoadingDatasets(true);

        // 鑾峰彇鐭ヨ瘑搴撳垪琛紙鍚庣宸茬粡鏍规嵁鏉冮檺缁勮繃婊よ繃浜嗭級
        const data = await knowledgeApi.listRagflowDatasets();
        const datasets = data.datasets || [];

        setDatasets(datasets);

        if (datasets.length > 0) {
          // 榛樿鏄剧ず鈥滃叏閮ㄢ€?
          setSelectedDataset('');
        } else {
          setError('鎮ㄦ病鏈夎鍒嗛厤浠讳綍鐭ヨ瘑搴撴潈闄愶紝璇疯仈绯荤鐞嗗憳');
        }
      } catch (err) {
        console.error('Failed to load datasets:', err);
        setError('?????????????????');
        setDatasets([]);
      } finally {
        setLoadingDatasets(false);
      }
    };

    fetchDatasets();
  }, []);

  const fetchRagflowDocuments = useCallback(async () => {
    if (selectedDataset === null) return;

    try {
      setLoading(true);
      if (selectedDataset === '') {
        console.log('Fetching local pending documents for ALL authorized KBs');
        const data = await knowledgeApi.listLocalDocuments({ status: 'pending' });
        console.log('Local pending documents response:', data);
        setDocuments(data.documents || []);
        return;
      }

      console.log('Fetching local pending documents for KB:', selectedDataset);
      const data = await knowledgeApi.listLocalDocuments({ status: 'pending', kb_id: selectedDataset });
      console.log('Local pending documents response:', data);
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Failed to fetch pending documents:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedDataset]);

  useEffect(() => {
    fetchRagflowDocuments();
  }, [fetchRagflowDocuments]);

  const handleApprove = async (docId) => {
    setError(null);
    setActionLoading(docId);
    try {
      const conflict = await reviewApi.getConflict(docId);
      if (conflict?.conflict && conflict?.existing) {
        setOverwritePrompt({ newDocId: docId, oldDoc: conflict.existing, normalized: conflict.normalized_name });
        return;
      }

      if (!window.confirm('????????????')) return;
      await reviewApi.approve(docId);
      fetchRagflowDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOverwriteUseNew = async () => {
    if (!overwritePrompt) return;
    const { newDocId, oldDoc } = overwritePrompt;
    const ok = window.confirm(
      `??????????\n\n????${oldDoc.filename}\n????${activeDocMap.get(newDocId)?.filename || ''}\n\n??????????????????????????????`
    );
    if (!ok) return;

    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.approveOverwrite(newDocId, oldDoc.doc_id);
      setOverwritePrompt(null);
      fetchRagflowDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOverwriteKeepOld = async () => {
    if (!overwritePrompt) return;
    const { newDocId, oldDoc } = overwritePrompt;
    const ok = window.confirm(`?????????????${oldDoc.filename}\n????`);
    if (!ok) return;
    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.reject(newDocId, '???????????????');
      setOverwritePrompt(null);
      fetchRagflowDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (docId) => {
    const notes = window.prompt('???????????');
    if (notes === null) return;

    setActionLoading(docId);
    try {
      await reviewApi.reject(docId, notes);
      fetchRagflowDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (docId) => {
    console.log('[DocumentReview] handleDelete called with docId:', docId);
    console.log('[DocumentReview] User role:', user?.role);
    console.log('[DocumentReview] isAdmin():', isAdmin());

    if (!window.confirm('??????????????????')) return;

    setActionLoading(docId);
    try {
      console.log('[DocumentReview] Calling documentClient.delete...');
      await documentClient.delete({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
      console.log('[DocumentReview] Delete successful, refreshing documents...');
      fetchRagflowDocuments();
    } catch (err) {
      console.error('[DocumentReview] Delete failed:', err);
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDownload = async (docId) => {
    setDownloadLoading(docId);
    try {
      await documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloadLoading(null);
    }
  };

  const handleSelectDoc = (docId) => {
    const newSelected = new Set(selectedDocIds);
    if (newSelected.has(docId)) {
      newSelected.delete(docId);
    } else {
      newSelected.add(docId);
    }
    setSelectedDocIds(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedDocIds.size === documents.length) {
      setSelectedDocIds(new Set());
    } else {
      setSelectedDocIds(new Set(documents.map(d => d.doc_id)));
    }
  };

  const handleBatchDownload = async () => {
    if (selectedDocIds.size === 0) {
      setError('璇峰厛閫夋嫨瑕佷笅杞界殑鏂囨。');
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
  };

  const handleBatchApproveAll = async () => {
    if (documents.length === 0) {
      setError('当前没有待审核文档。');
      return;
    }
    if (!window.confirm(`确定要一键通过当前列表中的 ${documents.length} 个待审核文档吗？`)) return;

    setBatchReviewLoading('approve');
    setBatchReviewSummary(null);
    setBatchSummaryExpanded(false);
    setBatchSummaryCopied(false);
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
        }),
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
          conflicted: conflicted.map((item) => ({
            docId: item.doc.doc_id,
            filename: item.doc.filename,
            detail: item.conflict?.existing?.filename ? `与已通过文档重复：${item.conflict.existing.filename}` : '检测到命名冲突',
          })),
          checkFailed: conflictCheckFailed.map((item) => ({
            docId: item.doc.doc_id,
            filename: item.doc.filename,
            detail: item.conflictError,
          })),
          failedItems: [],
        });
        setError(
          `批量审批未执行：冲突 ${conflicted.length}，检查失败 ${conflictCheckFailed.length}${firstConflict ? `。首个文档：${firstConflict}` : ''}`,
        );
        return;
      }

      const result = await reviewApi.approveBatch(approvableDocs.map((doc) => doc.doc_id));
      setBatchReviewSummary({
        mode: 'approve',
        successCount: result.success_count,
        failedCount: result.failed_count,
        conflicted: conflicted.map((item) => ({
          docId: item.doc.doc_id,
          filename: item.doc.filename,
          detail: item.conflict?.existing?.filename ? `与已通过文档重复：${item.conflict.existing.filename}` : '检测到命名冲突',
        })),
        checkFailed: conflictCheckFailed.map((item) => ({
          docId: item.doc.doc_id,
          filename: item.doc.filename,
          detail: item.conflictError,
        })),
        failedItems: result.failed_items || [],
      });
      await fetchRagflowDocuments();
      setSelectedDocIds(new Set());
      if (result.failed_count > 0 || conflicted.length > 0 || conflictCheckFailed.length > 0) {
        const firstFailure = result.failed_items?.[0];
        const firstConflict = conflicted[0]?.doc?.filename || conflictCheckFailed[0]?.doc?.filename || '';
        setError(
          `批量审批完成：成功 ${result.success_count}，失败 ${result.failed_count}，冲突跳过 ${conflicted.length}，检查失败 ${conflictCheckFailed.length}${firstFailure ? `。首个失败：${firstFailure.doc_id} - ${firstFailure.detail}` : firstConflict ? `。首个跳过：${firstConflict}` : ''}`,
        );
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchReviewLoading(null);
    }
  };

  const handleBatchRejectAll = async () => {
    if (documents.length === 0) {
      setError('当前没有待审核文档。');
      return;
    }
    const notes = window.prompt('请输入批量驳回原因（可选）');
    if (notes === null) return;
    if (!window.confirm(`确定要一键驳回当前列表中的 ${documents.length} 个待审核文档吗？`)) return;

    setBatchReviewLoading('reject');
    setBatchReviewSummary(null);
    setBatchSummaryExpanded(false);
    setBatchSummaryCopied(false);
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
      await fetchRagflowDocuments();
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
  };

  const buildBatchSummaryText = () => {
    if (!batchReviewSummary) return '';
    const lines = [
      batchReviewSummary.mode === 'approve' ? '批量审批明细' : '批量驳回明细',
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
  };

  const handleCopyBatchSummary = async () => {
    try {
      await navigator.clipboard.writeText(buildBatchSummaryText());
      setBatchSummaryCopied(true);
      window.setTimeout(() => setBatchSummaryCopied(false), 1500);
    } catch (err) {
      setError(err.message || '复制失败');
    }
  };

  return (
    <div>
      {overwritePrompt && (
        <div data-testid="docs-overwrite-modal"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 50,
            padding: '16px',
          }}
          onClick={() => setOverwritePrompt(null)}
        >
          <div
            style={{
              width: 'min(820px, 100%)',
              background: 'white',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              padding: '16px',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>妫€娴嬪埌鍙兘閲嶅鏂囦欢</div>
              <button
                type="button"
                onClick={() => setOverwritePrompt(null)} data-testid="docs-overwrite-close"
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                脳
              </button>
            </div>

            <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }}>
                <div style={{ fontWeight: 700, marginBottom: '6px', color: '#b91c1c' }}>????????</div>
                <div style={{ color: '#111827' }}>{overwritePrompt.oldDoc.filename}</div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
                  ?????{overwritePrompt.oldDoc.uploaded_at_ms ? new Date(overwritePrompt.oldDoc.uploaded_at_ms).toLocaleString('zh-CN') : ''}
                </div>
                <div style={{ marginTop: '10px' }}>
                  <button
                    type="button"
                    onClick={() => openLocalPreview(overwritePrompt.oldDoc.doc_id, overwritePrompt.oldDoc.filename)} data-testid="docs-overwrite-old-preview"
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: 'none',
                      background: '#10b981',
                      color: 'white',
                      cursor: 'pointer',
                      marginRight: '8px',
                    }}
                  >
                    ???????
                  </button>
                  <button
                    type="button"
                    onClick={() => documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId: overwritePrompt.oldDoc.doc_id })}
                    data-testid="docs-overwrite-old-download"
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid #d1d5db',
                      background: 'white',
                      cursor: 'pointer',
                    }}
                  >
                    ?????
                  </button>
                </div>
              </div>

              <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }}>
                <div style={{ fontWeight: 700, marginBottom: '6px', color: '#1d4ed8' }}>????????</div>
                <div style={{ color: '#111827' }}>{activeDocMap.get(overwritePrompt.newDocId)?.filename || ''}</div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
                  ??????{overwritePrompt.normalized || ''}
                </div>
                <div style={{ marginTop: '10px' }}>
                  <button
                    type="button"
                    onClick={() => openLocalPreview(overwritePrompt.newDocId, activeDocMap.get(overwritePrompt.newDocId)?.filename || '')} data-testid="docs-overwrite-new-preview"
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: 'none',
                      background: '#10b981',
                      color: 'white',
                      cursor: 'pointer',
                      marginRight: '8px',
                    }}
                  >
                    ???????
                  </button>
                  <button
                    type="button"
                    onClick={() => documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId: overwritePrompt.newDocId })}
                    data-testid="docs-overwrite-new-download"
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid #d1d5db',
                      background: 'white',
                      cursor: 'pointer',
                      marginRight: '8px',
                    }}
                  >
                    ?????
                  </button>
                </div>
              </div>
            </div>

            <div style={{ marginTop: '14px', display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() =>
                  openDiff(
                    overwritePrompt.oldDoc.doc_id,
                    overwritePrompt.oldDoc.filename,
                    overwritePrompt.newDocId,
                    activeDocMap.get(overwritePrompt.newDocId)?.filename || ''
                  )
                }
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid #d1d5db',
                  background: 'white',
                  cursor: 'pointer',
                }}
              >
                瀵规瘮宸紓
              </button>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={handleOverwriteKeepOld} data-testid="docs-overwrite-keep-old"
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid #d1d5db',
                  background: 'white',
                  cursor: 'pointer',
                }}
              >
                淇濈暀鏃ф枃浠讹紙椹冲洖鏂版枃浠讹級
              </button>
              <button
                type="button"
                onClick={handleOverwriteUseNew} data-testid="docs-overwrite-use-new"
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#3b82f6',
                  color: 'white',
                  cursor: 'pointer',
                }}
              >
                ???????
              </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {diffOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 70,
            padding: '16px',
          }}
          onClick={() => setDiffOpen(false)}
        >
          <div
            style={{
              width: 'min(1200px, 100%)',
              background: 'white',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              padding: '16px',
              height: '82vh',
              display: 'flex',
              flexDirection: 'column',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{diffTitle || '瀵规瘮宸紓'}</div>
              <button
                type="button"
                onClick={() => setDiffOpen(false)}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                脳
              </button>
            </div>

            <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ display: 'flex', gap: '8px', alignItems: 'center', color: '#374151' }}>
                <input type="checkbox" checked={diffOnly} onChange={(e) => setDiffOnly(e.target.checked)} />
                鍙湅宸紓
              </label>
              <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>??=?????=?????=???</div>
            </div>

            <div style={{ marginTop: '10px', flex: 1, overflow: 'auto', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
              {diffLoading ? (
                <div style={{ padding: '24px', color: '#6b7280' }}>??????...</div>
              ) : (
                <div style={{ padding: '12px' }}>
                  <ReactDiffViewer
                    oldValue={diffOldText || ''}
                    newValue={diffNewText || ''}
                    splitView={true}
                    showDiffOnly={diffOnly}
                    disableWordDiff={false}
                    compareMethod="diffLines"
                    leftTitle="???"
                    rightTitle="???"
                    styles={{
                      variables: {
                        light: {
                          diffViewerBackground: '#ffffff',
                          addedBackground: '#dcfce7',
                          removedBackground: '#fee2e2',
                          gutterBackground: '#f9fafb',
                          gutterBackgroundDark: '#f3f4f6',
                          highlightBackground: '#fff7ed',
                        },
                      },
                      contentText: { fontSize: 12 },
                      line: { fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace" },
                    }}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <DocumentPreviewModal open={previewOpen} target={previewTarget} onClose={closePreview} canDownloadFiles={!!canDownload()} />


      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          {embedded ? <div /> : <h2 style={{ margin: 0 }}>????</h2>}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleSelectAll}
              disabled={documents.length === 0}
              style={{
                padding: '8px 16px',
                backgroundColor: selectedDocIds.size === documents.length ? '#6b7280' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: documents.length === 0 ? 'not-allowed' : 'pointer',
                fontSize: '0.9rem',
              }}
            >
              {selectedDocIds.size === documents.length ? '取消全选' : '全选'}
            </button>
            {isReviewer() && (
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
                  }}
                >
                  {batchReviewLoading === 'approve' ? '???...' : `?????? (${documents.length})`}
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
                  }}
                >
                  {batchReviewLoading === 'reject' ? '???...' : `?????? (${documents.length})`}
                </button>
              </>
            )}
            {canDownload() && (
              <button
                onClick={handleBatchDownload}
                disabled={selectedDocIds.size === 0 || batchDownloadLoading || !!batchReviewLoading}
                style={{
                  padding: '8px 16px',
                  backgroundColor: selectedDocIds.size > 0 && !batchDownloadLoading && !batchReviewLoading ? '#10b981' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: selectedDocIds.size > 0 && !batchDownloadLoading && !batchReviewLoading ? 'pointer' : 'not-allowed',
                  fontSize: '0.9rem',
                }}
              >
                {batchDownloadLoading ? '???...' : `???? (${selectedDocIds.size})`}
              </button>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
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
            }}
          >
              <option>???...</option>
              <option>鍔犺浇涓?..</option>
            ) : (
              <>
                <option value="">鍏ㄩ儴</option>
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

      {batchReviewSummary && (
        <div
          style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #dbeafe',
            color: '#1e3a8a',
            padding: '12px 16px',
            borderRadius: '6px',
            marginBottom: '20px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', marginBottom: '8px' }}>
            <div style={{ fontWeight: 600 }}>
              {batchReviewSummary.mode === 'approve' ? '??????' : '??????'}
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => setBatchSummaryExpanded((prev) => !prev)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: '1px solid #93c5fd',
                  background: 'white',
                  color: '#1d4ed8',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                }}
              >
                {batchSummaryExpanded ? '\u6536\u8d77' : '\u5c55\u5f00\u5168\u90e8'}
              </button>
              <button
                type="button"
                onClick={handleCopyBatchSummary}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: '1px solid #93c5fd',
                  background: 'white',
                  color: '#1d4ed8',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                }}
              >
                {batchSummaryCopied ? '\u5df2\u590d\u5236' : '\u590d\u5236\u660e\u7ec6'}
              </button>
            </div>
          </div>
          <div style={{ fontSize: '0.95rem', marginBottom: '8px' }}>
            {`?? ${batchReviewSummary.successCount}??? ${batchReviewSummary.failedCount}????? ${batchReviewSummary.conflicted.length}????? ${batchReviewSummary.checkFailed.length}`}
          </div>
          {batchReviewSummary.failedItems.length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{ fontWeight: 600, color: '#991b1b' }}>???</div>
              {batchReviewSummary.failedItems.slice(0, batchSummaryExpanded ? batchReviewSummary.failedItems.length : 10).map((item) => (
                <div key={`failed-${item.doc_id}`} style={{ fontSize: '0.9rem', color: '#374151' }}>
                  {`${item.doc_id}: ${item.detail}`}
                </div>
              ))}
            </div>
          )}
          {batchReviewSummary.conflicted.length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{ fontWeight: 600, color: '#92400e' }}>????</div>
              {batchReviewSummary.conflicted.slice(0, batchSummaryExpanded ? batchReviewSummary.conflicted.length : 10).map((item) => (
                <div
                  key={`conflict-${item.docId}`}
                  style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem', color: '#374151', marginBottom: '4px' }}
                >
                  <span style={{ flex: 1 }}>{`${item.filename}: ${item.detail}`}</span>
                  {item.existing && (
                    <button
                      type="button"
                      onClick={() => setOverwritePrompt({ newDocId: item.docId, oldDoc: item.existing, normalized: item.normalized || '' })}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        border: '1px solid #d97706',
                        background: '#fff7ed',
                        color: '#9a3412',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                      }}
                    >
                      {'\u5904\u7406'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {batchReviewSummary.checkFailed.length > 0 && (
            <div>
              <div style={{ fontWeight: 600, color: '#7c2d12' }}>????</div>
              {batchReviewSummary.checkFailed.slice(0, batchSummaryExpanded ? batchReviewSummary.checkFailed.length : 10).map((item) => (
                <div key={`check-${item.docId}`} style={{ fontSize: '0.9rem', color: '#374151' }}>
                  {`${item.filename}: ${item.detail}`}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div>Loading...</div>
      ) : (
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{ backgroundColor: '#f9fafb' }}>
              <tr>
                <th style={{ padding: '12px 16px', textAlign: 'center', borderBottom: '1px solid #e5e7eb', width: '50px' }}>
                  <input
                    type="checkbox"
                    checked={documents.length > 0 && selectedDocIds.size === documents.length}
                    onChange={handleSelectAll}
                    disabled={documents.length === 0}
                    style={{ cursor: documents.length === 0 ? 'not-allowed' : 'pointer' }}
                  />
                </th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>鏂囨。鍚嶇О</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>??</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>???</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>???</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>涓婁紶鏃堕棿</th>
                <th style={{ padding: '12px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb' }}>鎿嶄綔</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
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
                    <span style={{
                      display: 'inline-block',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor: doc.status === 'pending' ? '#f59e0b' : '#10b981',
                      color: 'white',
                      fontSize: '0.85rem',
                    }}>
                      {doc.status === 'pending' ? '???' : doc.status === 'approved' ? '???' : doc.status === 'rejected' ? '???' : doc.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#6b7280' }}>
                    {doc.kb_id}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#6b7280' }}>
                    {doc.uploaded_by_name || doc.uploaded_by}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                    {new Date(doc.uploaded_at_ms).toLocaleString('zh-CN')}
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    {doc.status === 'pending' && (
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
                        鏌ョ湅
                      </button>
                    )}
                    {canDownload() && (
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
                        {downloadLoading === doc.doc_id ? '???...' : '??'}
                      </button>
                    )}
                    {doc.status === 'pending' && isReviewer() ? (
                      <>
                        <button
                          onClick={() => handleApprove(doc.doc_id)}
                          disabled={actionLoading === doc.doc_id}
                          data-testid={`docs-approve-${doc.doc_id}`}
                          style={{
                            padding: '6px 12px',
                            backgroundColor: actionLoading === doc.doc_id ? '#9ca3af' : '#10b981',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: actionLoading === doc.doc_id ? 'not-allowed' : 'pointer',
                            fontSize: '0.9rem',
                            marginRight: '8px',
                          }}
                        >
                          {actionLoading === doc.doc_id ? '???...' : '??'}
                        </button>
                        <button
                          onClick={() => handleReject(doc.doc_id)}
                          disabled={actionLoading === doc.doc_id}
                          data-testid={`docs-reject-${doc.doc_id}`}
                          style={{
                            padding: '6px 12px',
                            backgroundColor: actionLoading === doc.doc_id ? '#9ca3af' : '#ef4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: actionLoading === doc.doc_id ? 'not-allowed' : 'pointer',
                            fontSize: '0.9rem',
                            marginRight: '8px',
                          }}
                        >
                          椹冲洖
                        </button>
                      </>
                          ??
                      <span style={{ color: '#9ca3af', fontSize: '0.85rem', marginRight: '8px' }}>
                        {doc.status === 'approved' ? '???' : '???'}
                      </span>
                    ) : null}
                    {isAdmin() && (
                      <button
                        onClick={() => handleDelete(doc.doc_id)}
                        disabled={actionLoading === doc.doc_id}
                        data-testid={`docs-delete-${doc.doc_id}`}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: actionLoading === doc.doc_id ? '#9ca3af' : '#dc2626',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: actionLoading === doc.doc_id ? 'not-allowed' : 'pointer',
                          fontSize: '0.9rem',
                        }}
                      >
                        鍒犻櫎
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {documents.length === 0 && (
            <div data-testid="docs-empty" style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
              {selectedDataset ? '???????????' : '??????'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DocumentReview;

