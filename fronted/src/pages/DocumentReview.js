import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { reviewApi } from '../features/review/api';
import { knowledgeApi } from '../features/knowledge/api';
import { authBackendUrl } from '../config/backend';
import ReactMarkdown from 'react-markdown';
import { httpClient } from '../shared/http/httpClient';
import ReactDiffViewer from 'react-diff-viewer-continued';

const DocumentReview = ({ embedded = false }) => {
  const { user, isReviewer, isAdmin, canDownload } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedDocIds, setSelectedDocIds] = useState(new Set());
  const [downloadLoading, setDownloadLoading] = useState(null);
  const [batchDownloadLoading, setBatchDownloadLoading] = useState(false);

  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null); // null=未加载；''=全部；其它=知识库
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [overwritePrompt, setOverwritePrompt] = useState(null); // { newDocId, oldDoc, normalized }
  const [previewing, setPreviewing] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDocName, setPreviewDocName] = useState(null);
  const [previewKind, setPreviewKind] = useState(null); // 'md' | 'text' | 'blob'
  const [previewText, setPreviewText] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
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
    if (previewUrl) window.URL.revokeObjectURL(previewUrl);
    setPreviewOpen(false);
    setPreviewDocName(null);
    setPreviewKind(null);
    setPreviewText(null);
    setPreviewUrl(null);
  };

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
    const response = await httpClient.request(authBackendUrl(`/api/knowledge/documents/${docId}/preview`), { method: 'GET' });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data?.detail || `预览失败 (${response.status})`);
    }
    const blob = await response.blob();
    return await blob.text();
  };

  const openDiff = async (oldDocId, oldFilename, newDocId, newFilename) => {
    setError(null);
    setDiffTitle(`对比：${oldFilename}  vs  ${newFilename}`);
    setDiffOpen(true);
    setDiffLoading(true);
    setDiffOldText('');
    setDiffNewText('');
    try {
      if (!isTextComparable(oldFilename) || !isTextComparable(newFilename)) {
        throw new Error('对比功能仅支持：md/txt/ini/log');
      }
      const [oldText, newText] = await Promise.all([fetchLocalPreviewText(oldDocId), fetchLocalPreviewText(newDocId)]);
      const maxLines = 2500;
      if (countLines(oldText) > maxLines || countLines(newText) > maxLines) {
        throw new Error('文件太大，无法在页面里对比；请下载后用工具对比。');
      }
      setDiffOldText(oldText);
      setDiffNewText(newText);
    } catch (e) {
      setDiffOpen(false);
      setError(e.message || '对比失败');
    } finally {
      setDiffLoading(false);
    }
  };

  const openLocalPreview = async (docId, filename) => {
    setError(null);
    setPreviewing(true);
    setPreviewOpen(true);
    setPreviewDocName(filename || `document_${docId}`);
    setPreviewKind(null);
    setPreviewText(null);
    if (previewUrl) window.URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);

    try {
      const response = await httpClient.request(authBackendUrl(`/api/knowledge/documents/${docId}/preview`), { method: 'GET' });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data?.detail || `预览失败 (${response.status})`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      setPreviewUrl(url);

      if (isMarkdownFile(filename)) {
        const text = await blob.text();
        setPreviewKind('md');
        setPreviewText(text);
      } else if (isPlainTextFile(filename)) {
        const text = await blob.text();
        setPreviewKind('text');
        setPreviewText(text);
      } else {
        setPreviewKind('blob');
      }
    } catch (e) {
      closePreview();
      setError(e.message || '预览失败');
    } finally {
      setPreviewing(false);
    }
  };

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        setLoadingDatasets(true);

        // 获取知识库列表（后端已经根据权限组过滤过了）
        const data = await knowledgeApi.listRagflowDatasets();
        const datasets = data.datasets || [];

        setDatasets(datasets);

        if (datasets.length > 0) {
          // 默认显示“全部”
          setSelectedDataset('');
        } else {
          setError('您没有被分配任何知识库权限，请联系管理员');
        }
      } catch (err) {
        console.error('Failed to load datasets:', err);
        setError('无法加载知识库列表，请检查网络连接');
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

      if (!window.confirm('确定要审核通过该文档吗？')) return;
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
      `检测到可能重复文件。\n\n旧文件：${oldDoc.filename}\n新文件：${activeDocMap.get(newDocId)?.filename || ''}\n\n是否用“新文件”覆盖旧文件？（会先删除旧文件，再上传新文件）`
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
    const ok = window.confirm(`将驳回新文件并保留旧文件：${oldDoc.filename}\n确定吗？`);
    if (!ok) return;
    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.reject(newDocId, '检测到重复文件，选择保留旧文件');
      setOverwritePrompt(null);
      fetchRagflowDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (docId) => {
    const notes = window.prompt('请输入驳回原因（可选）');
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

    if (!window.confirm('确定要删除该文档吗？此操作不可恢复。')) return;

    setActionLoading(docId);
    try {
      console.log('[DocumentReview] Calling authClient.deleteDocument...');
      await knowledgeApi.deleteLocalDocument(docId);
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
      await knowledgeApi.downloadLocalDocument(docId);
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
      setError('请先选择要下载的文档');
      return;
    }

    setBatchDownloadLoading(true);
    try {
      await knowledgeApi.batchDownloadLocalDocuments(Array.from(selectedDocIds));
      setSelectedDocIds(new Set());
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchDownloadLoading(false);
    }
  };

  return (
    <div>
      {overwritePrompt && (
        <div
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
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>检测到可能重复文件</div>
              <button
                type="button"
                onClick={() => setOverwritePrompt(null)}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ×
              </button>
            </div>

            <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }}>
                <div style={{ fontWeight: 700, marginBottom: '6px', color: '#b91c1c' }}>旧文件（已通过）</div>
                <div style={{ color: '#111827' }}>{overwritePrompt.oldDoc.filename}</div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
                  上传时间：{overwritePrompt.oldDoc.uploaded_at_ms ? new Date(overwritePrompt.oldDoc.uploaded_at_ms).toLocaleString('zh-CN') : ''}
                </div>
                <div style={{ marginTop: '10px' }}>
                  <button
                    type="button"
                    onClick={() => openLocalPreview(overwritePrompt.oldDoc.doc_id, overwritePrompt.oldDoc.filename)}
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
                    在线查看旧文件
                  </button>
                  <button
                    type="button"
                    onClick={() => knowledgeApi.downloadLocalDocument(overwritePrompt.oldDoc.doc_id)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid #d1d5db',
                      background: 'white',
                      cursor: 'pointer',
                    }}
                  >
                    下载旧文件
                  </button>
                </div>
              </div>

              <div style={{ border: '1px solid #e5e7eb', borderRadius: '10px', padding: '12px' }}>
                <div style={{ fontWeight: 700, marginBottom: '6px', color: '#1d4ed8' }}>新文件（待审核）</div>
                <div style={{ color: '#111827' }}>{activeDocMap.get(overwritePrompt.newDocId)?.filename || ''}</div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: '6px' }}>
                  归一化名称：{overwritePrompt.normalized || ''}
                </div>
                <div style={{ marginTop: '10px' }}>
                  <button
                    type="button"
                    onClick={() => openLocalPreview(overwritePrompt.newDocId, activeDocMap.get(overwritePrompt.newDocId)?.filename || '')}
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
                    在线查看新文件
                  </button>
                  <button
                    type="button"
                    onClick={() => knowledgeApi.downloadLocalDocument(overwritePrompt.newDocId)}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '8px',
                      border: '1px solid #d1d5db',
                      background: 'white',
                      cursor: 'pointer',
                      marginRight: '8px',
                    }}
                  >
                    下载新文件
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
                对比差异
              </button>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                type="button"
                onClick={handleOverwriteKeepOld}
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid #d1d5db',
                  background: 'white',
                  cursor: 'pointer',
                }}
              >
                保留旧文件（驳回新文件）
              </button>
              <button
                type="button"
                onClick={handleOverwriteUseNew}
                style={{
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#3b82f6',
                  color: 'white',
                  cursor: 'pointer',
                }}
              >
                使用新文件覆盖
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
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{diffTitle || '对比差异'}</div>
              <button
                type="button"
                onClick={() => setDiffOpen(false)}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ×
              </button>
            </div>

            <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ display: 'flex', gap: '8px', alignItems: 'center', color: '#374151' }}>
                <input type="checkbox" checked={diffOnly} onChange={(e) => setDiffOnly(e.target.checked)} />
                只看差异
              </label>
              <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>绿色=新增，红色=删除，灰色=未变化</div>
            </div>

            <div style={{ marginTop: '10px', flex: 1, overflow: 'auto', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
              {diffLoading ? (
                <div style={{ padding: '24px', color: '#6b7280' }}>正在生成对比…</div>
              ) : (
                <div style={{ padding: '12px' }}>
                  <ReactDiffViewer
                    oldValue={diffOldText || ''}
                    newValue={diffNewText || ''}
                    splitView={true}
                    showDiffOnly={diffOnly}
                    disableWordDiff={false}
                    compareMethod="diffLines"
                    leftTitle="旧文件"
                    rightTitle="新文件"
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

      {previewOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 60,
            padding: '16px',
          }}
          onClick={closePreview}
        >
          <div
            style={{
              width: 'min(980px, 100%)',
              background: 'white',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              padding: '16px',
              height: '80vh',
              display: 'flex',
              flexDirection: 'column',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
              <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{previewDocName || '在线查看'}</div>
              <button
                type="button"
                onClick={closePreview}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ×
              </button>
            </div>

            <div style={{ marginTop: '12px', flex: 1, overflow: 'auto' }}>
              {previewing ? (
                <div style={{ color: '#6b7280', padding: '24px' }}>加载中…</div>
              ) : previewKind === 'md' ? (
                <div style={{ padding: '24px' }}>
                  <div style={{ fontSize: '0.875rem', lineHeight: '1.6', color: '#1f2937' }}>
                    <ReactMarkdown>{previewText || ''}</ReactMarkdown>
                  </div>
                </div>
              ) : previewKind === 'text' ? (
                <pre
                  style={{
                    margin: 0,
                    padding: '24px',
                    fontSize: '0.875rem',
                    lineHeight: '1.6',
                    color: '#111827',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily:
                      "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
                  }}
                >
                  {previewText || ''}
                </pre>
              ) : previewUrl ? (
                <iframe title={previewDocName || 'preview'} src={previewUrl} style={{ width: '100%', height: '100%', border: 'none' }} />
              ) : (
                <div style={{ color: '#6b7280', padding: '24px' }}>无法预览</div>
              )}
            </div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          {embedded ? <div /> : <h2 style={{ margin: 0 }}>文档管理</h2>}
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
            {canDownload() && (
              <button
                onClick={handleBatchDownload}
                disabled={selectedDocIds.size === 0 || batchDownloadLoading}
                style={{
                  padding: '8px 16px',
                  backgroundColor: selectedDocIds.size > 0 && !batchDownloadLoading ? '#10b981' : '#9ca3af',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: selectedDocIds.size > 0 && !batchDownloadLoading ? 'pointer' : 'not-allowed',
                  fontSize: '0.9rem',
                }}
              >
                {batchDownloadLoading ? '下载中...' : `下载选中 (${selectedDocIds.size})`}
              </button>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <select
            value={selectedDataset === null ? '' : selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
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
            ) : (
              <>
                <option value="">全部</option>
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
        <div style={{
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          padding: '12px 16px',
          borderRadius: '4px',
          marginBottom: '20px',
        }}>
          {error}
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
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>文档名称</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>状态</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>知识库</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>上传者</th>
                <th style={{ padding: '12px 16px', textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>上传时间</th>
                <th style={{ padding: '12px 16px', textAlign: 'right', borderBottom: '1px solid #e5e7eb' }}>操作</th>
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
                      {doc.status === 'pending' ? '待审核' : doc.status === 'approved' ? '已通过' : doc.status === 'rejected' ? '已驳回' : doc.status}
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
                        {downloadLoading === doc.doc_id ? '下载中...' : '下载'}
                      </button>
                    )}
                    {doc.status === 'pending' && isReviewer() ? (
                      <>
                        <button
                          onClick={() => handleApprove(doc.doc_id)}
                          disabled={actionLoading === doc.doc_id}
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
                          {actionLoading === doc.doc_id ? '处理中...' : '通过'}
                        </button>
                        <button
                          onClick={() => handleReject(doc.doc_id)}
                          disabled={actionLoading === doc.doc_id}
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
                          驳回
                        </button>
                      </>
                    ) : doc.status !== 'pending' ? (
                      <span style={{ color: '#9ca3af', fontSize: '0.85rem', marginRight: '8px' }}>
                        {doc.status === 'approved' ? '已通过' : '已驳回'}
                      </span>
                    ) : null}
                    {isAdmin() && (
                      <button
                        onClick={() => handleDelete(doc.doc_id)}
                        disabled={actionLoading === doc.doc_id}
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
                        删除
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {documents.length === 0 && (
            <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
              {selectedDataset ? `该知识库暂无待审核文档` : '请选择知识库'}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DocumentReview;
