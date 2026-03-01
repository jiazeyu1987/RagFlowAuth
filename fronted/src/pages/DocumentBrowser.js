import React, { useEffect, useMemo, useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import authClient from '../api/authClient';
import documentClient, { DOCUMENT_SOURCE } from '../shared/documents/documentClient';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

const Spinner = ({ size = 16 }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
    style={{
      animation: 'spin 1s linear infinite',
    }}
  >
    <circle
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
      fill="none"
      strokeDasharray="32"
      strokeDashoffset="32"
      style={{
        strokeDashoffset: '32',
        animation: 'dash 1.5s ease-in-out infinite',
      }}
    />
  </svg>
);

const injectSpinnerStyles = () => {
  if (typeof document !== 'undefined' && !document.getElementById('spinner-styles')) {
    const style = document.createElement('style');
    style.id = 'spinner-styles';
    style.textContent = `
      @keyframes spin {
        100% { transform: rotate(360deg); }
      }
      @keyframes dash {
        0% { stroke-dasharray: 1, 150; stroke-dashoffset: 0; }
        50% { stroke-dasharray: 90, 150; stroke-dashoffset: -35; }
        100% { stroke-dasharray: 90, 150; stroke-dashoffset: -124; }
      }
    `;
    document.head.appendChild(style);
  }
};

if (typeof window !== 'undefined') {
  injectSpinnerStyles();
}

const DocumentBrowser = () => {
  const location = useLocation();
  const { user, can, canDownload, accessibleKbs } = useAuth();
  const [datasets, setDatasets] = useState([]);
  const [datasetFilterKeyword, setDatasetFilterKeyword] = useState('');
  const [recentDatasetKeywords, setRecentDatasetKeywords] = useState([]);
  const [documents, setDocuments] = useState({});
  const [documentErrors, setDocumentErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedDatasets, setExpandedDatasets] = useState(new Set());
  const [actionLoading, setActionLoading] = useState({});
  const [selectedDocs, setSelectedDocs] = useState({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const handleViewRef = useRef(null);
  const [canDeleteDocs, setCanDeleteDocs] = useState(false);

  useEffect(() => {
    fetchAllDatasets();
  }, [accessibleKbs, user]); // 当用户权限变化时重新加载

  useEffect(() => {
    const storageKey = `ragflowauth_recent_dataset_keywords_v1:${user?.user_id || 'anon'}`;
    try {
      const raw = window.localStorage.getItem(storageKey);
      const arr = JSON.parse(raw || '[]');
      if (Array.isArray(arr)) {
        setRecentDatasetKeywords(arr.filter((x) => typeof x === 'string' && x.trim()).slice(0, 5));
      } else {
        setRecentDatasetKeywords([]);
      }
    } catch {
      setRecentDatasetKeywords([]);
    }
  }, [user?.user_id]);

  // Handle navigation from search page - locate and preview specific document
  useEffect(() => {
    if (location.state?.documentId && datasets.length > 0) {
      const { documentId, documentName, datasetId } = location.state;

      // Find the dataset name from datasetId
      const targetDataset = datasets.find(ds => ds.id === datasetId);
      if (!targetDataset) {
        setError(`无法找到知识库: ${datasetId}`);
        return;
      }

      const datasetName = targetDataset.name || targetDataset.id;

      // Expand the dataset
      setExpandedDatasets(prev => new Set([...prev, datasetName]));

      // Fetch documents for this dataset if not already loaded
      if (!documents[datasetName]) {
        fetchDocumentsForDataset(datasetName);
      }

      // Wait for documents to load, then preview the target document
      const checkAndPreview = setInterval(() => {
        if (documents[datasetName] && documents[datasetName].length > 0) {
          clearInterval(checkAndPreview);

          const targetDoc = documents[datasetName].find(doc => doc.id === documentId);
          if (targetDoc) {
            handleViewRef.current?.(documentId, datasetName);
          } else {
            setError(`无法在知识库 "${datasetName}" 中找到文档: ${documentName}`);
          }
        }
      }, 500);

      // Cleanup interval after 10 seconds
      setTimeout(() => clearInterval(checkAndPreview), 10000);
    }
  }, [location.state, datasets, documents]);

  // 当用户切换时，清空之前的文档数据
  useEffect(() => {
    setDocuments({});
    setDocumentErrors({});
    setExpandedDatasets(new Set());
    setSelectedDocs({});
  }, [user?.user_id]);

  useEffect(() => {
    setCanDeleteDocs(can('ragflow_documents', 'delete'));
  }, [can, user?.user_id]);

  useEffect(() => {
    if (datasets.length > 0) {
      datasets.forEach((dataset) => {
        if (!documents[dataset.name]) {
          fetchDocumentsForDataset(dataset.name);
        }
      });
    }
  }, [datasets, documents]);

  const fetchAllDatasets = async () => {
    try {
      setLoading(true);

      // 获取所有知识库（后端已经根据权限组过滤过了）
      const data = await authClient.listRagflowDatasets();
      const datasets = data.datasets || [];

      // 直接使用后端返回的数据，不需要前端再次过滤
      setDatasets(datasets);

      // 如果没有知识库，显示提示
      if (datasets.length === 0) {
        setError('您没有被分配任何知识库权限，请联系管理员');
      } else {
        setError(null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchDocumentsForDataset = async (datasetName) => {
    try {
      setDocumentErrors((prev) => {
        const next = { ...prev };
        delete next[datasetName];
        return next;
      });
      const data = await authClient.listRagflowDocuments(datasetName);
      setDocuments(prev => ({
        ...prev,
        [datasetName]: data.documents || []
      }));
    } catch (err) {
      console.error(`Failed to fetch documents for ${datasetName}:`, err);
      setDocumentErrors(prev => ({
        ...prev,
        [datasetName]: err?.message || '\u52a0\u8f7d\u6587\u6863\u5931\u8d25'
      }));
      setDocuments(prev => ({
        ...prev,
        [datasetName]: []
      }));
    }
  };

  const normalizedKeyword = (datasetFilterKeyword || '').trim().toLowerCase();
  const visibleDatasets = useMemo(() => {
    if (!normalizedKeyword) return datasets;
    return datasets.filter((d) => {
      const name = String(d?.name || '').toLowerCase();
      const id = String(d?.id || '').toLowerCase();
      return name.includes(normalizedKeyword) || id.includes(normalizedKeyword);
    });
  }, [datasets, normalizedKeyword]);

  const toggleDataset = (datasetName) => {
    const newExpanded = new Set(expandedDatasets);
    if (newExpanded.has(datasetName)) {
      newExpanded.delete(datasetName);
    } else {
      newExpanded.add(datasetName);
      if (!documents[datasetName]) {
        fetchDocumentsForDataset(datasetName);
      }
    }
    setExpandedDatasets(newExpanded);
  };

  const expandAll = () => {
    const allDatasets = new Set(visibleDatasets.map(d => d.name));
    setExpandedDatasets(allDatasets);
    visibleDatasets.forEach((dataset) => {
      if (!documents[dataset.name]) {
        fetchDocumentsForDataset(dataset.name);
      }
    });
  };

  const collapseAll = () => {
    setExpandedDatasets(new Set());
  };

  const refreshAll = () => {
    setDocuments({});
    datasets.forEach((dataset) => {
      fetchDocumentsForDataset(dataset.name);
    });
  };

  const handleView = async (docId, datasetName) => {
    const doc = documents[datasetName]?.find(d => d.id === docId);
    const docName = doc?.name || `document_${docId}`;

    setPreviewTarget({ source: DOCUMENT_SOURCE.RAGFLOW, docId, datasetName, filename: docName });
    setPreviewOpen(true);
  };

  handleViewRef.current = handleView;

  const closePreview = () => {
    setPreviewOpen(false);
    setPreviewTarget(null);
  };

  const handleDownload = async (docId, datasetName) => {
    const doc = documents[datasetName]?.find(d => d.id === docId);
    const docName = doc?.name || `document_${docId}`;

    try {
      setActionLoading(prev => ({ ...prev, [`${docId}-download`]: true }));
      await documentClient.downloadToBrowser({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId,
        datasetName,
        filename: docName,
      });
    } catch (err) {
      setError(err.message || '下载失败');
    } finally {
      setActionLoading(prev => ({ ...prev, [`${docId}-download`]: false }));
    }
  };

  const handleDelete = async (docId, datasetName) => {
    if (!window.confirm('确定要删除该文档吗？此操作不可恢复。')) return;

    try {
      setActionLoading(prev => ({ ...prev, [`${docId}-delete`]: true }));
      await documentClient.delete({ source: DOCUMENT_SOURCE.RAGFLOW, docId, datasetName });

      setDocuments(prev => {
        const updated = { ...prev };
        if (updated[datasetName]) {
          updated[datasetName] = updated[datasetName].filter(d => d.id !== docId);
        }
        return updated;
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [`${docId}-delete`]: false }));
    }
  };

  const canDelete = () => {
    return canDeleteDocs;
  };

  const handleSelectDoc = (docId, datasetName) => {
    setSelectedDocs(prev => {
      const datasetSelections = prev[datasetName] || [];
      const newSelections = datasetSelections.includes(docId)
        ? datasetSelections.filter(id => id !== docId)
        : [...datasetSelections, docId];
      return {
        ...prev,
        [datasetName]: newSelections
      };
    });
  };

  const handleSelectAllInDataset = (datasetName) => {
    const datasetDocs = documents[datasetName] || [];
    const currentSelections = selectedDocs[datasetName] || [];
    const allSelected = datasetDocs.length > 0 && currentSelections.length === datasetDocs.length;

    setSelectedDocs(prev => ({
      ...prev,
      [datasetName]: allSelected ? [] : datasetDocs.map(d => d.id)
    }));
  };

  const isDocSelected = (docId, datasetName) => {
    return (selectedDocs[datasetName] || []).includes(docId);
  };

  const isAllSelectedInDataset = (datasetName) => {
    const datasetDocs = documents[datasetName] || [];
    const currentSelections = selectedDocs[datasetName] || [];
    return datasetDocs.length > 0 && currentSelections.length === datasetDocs.length;
  };

  const getSelectedCount = () => {
    return Object.values(selectedDocs).reduce((total, selections) => total + selections.length, 0);
  };

  const clearAllSelections = () => {
    setSelectedDocs({});
  };

  const handleBatchDownload = async () => {
    const batchDownloadKey = 'batch-download';
    const allSelectedDocs = [];

    Object.entries(selectedDocs).forEach(([datasetName, docIds]) => {
      docIds.forEach(docId => {
        const doc = documents[datasetName]?.find(d => d.id === docId);
        if (doc) {
          allSelectedDocs.push({
            doc_id: docId,
            dataset: datasetName,
            name: doc.name
          });
        }
      });
    });

    if (allSelectedDocs.length === 0) {
      setError('请至少选择一个文档');
      return;
    }

    try {
      setError(null);
      setActionLoading(prev => ({ ...prev, [batchDownloadKey]: true }));

      await documentClient.batchDownloadRagflowToBrowser(allSelectedDocs);

      clearAllSelections();
    } catch (err) {
      setError(err.message || '批量下载失败');
    } finally {
      setActionLoading(prev => ({ ...prev, [batchDownloadKey]: false }));
    }
  };

  const getStatusColor = (status) => {
    if (status === 'ready') return '#10b981';
    if (status === 'processing') return '#f59e0b';
    return '#6b7280';
  };

  const getStatusName = (status) => {
    const names = {
      'ready': '就绪',
      'processing': '处理中',
      'failed': '失败',
    };
    return names[status] || status;
  };

  const getTotalDocumentCount = () => {
    return datasets.reduce((total, dataset) => {
      return total + (documents[dataset.name]?.length || 0);
    }, 0);
  };

  const commitDatasetKeywordToHistory = (value) => {
    const v = String(value || '').trim();
    if (!v) return;

    const next = [v, ...(recentDatasetKeywords || [])]
      .filter((x) => typeof x === 'string' && x.trim())
      .filter((x, idx, arr) => arr.findIndex((y) => y.toLowerCase() === x.toLowerCase()) === idx)
      .slice(0, 5);

    setRecentDatasetKeywords(next);
    try {
      const storageKey = `ragflowauth_recent_dataset_keywords_v1:${user?.user_id || 'anon'}`;
      window.localStorage.setItem(storageKey, JSON.stringify(next));
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '16px' }}>⏳</div>
          <div style={{ color: '#6b7280' }}>加载中...</div>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="browser-page">
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ margin: '0 0 8px 0' }}>文档浏览</h2>
        <p style={{ margin: 0, color: '#6b7280', fontSize: '0.9rem' }}>
          查看所有知识库中的文档
        </p>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
        <button
          onClick={expandAll}
          data-testid="browser-expand-all"
          style={{
            padding: '8px 16px',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          展开全部
        </button>
        <button
          onClick={collapseAll}
          data-testid="browser-collapse-all"
          style={{
            padding: '8px 16px',
            backgroundColor: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          折叠全部
        </button>
        <button
          onClick={refreshAll}
          data-testid="browser-refresh-all"
          style={{
            padding: '8px 16px',
            backgroundColor: '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          刷新
        </button>
        {getSelectedCount() > 0 && canDownload() && (
          <>
            <button
              onClick={handleBatchDownload}
              disabled={actionLoading['batch-download']}
              data-testid="browser-batch-download"
              style={{
                padding: '8px 16px',
                backgroundColor: '#8b5cf6',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              {actionLoading['batch-download'] ? (
                <>
                  <Spinner size={14} />
                  <span>打包中</span>
                </>
              ) : (
                `批量下载 (${getSelectedCount()})`
              )}
            </button>
            <button
              onClick={clearAllSelections}
              data-testid="browser-clear-selection"
              style={{
                padding: '8px 16px',
                backgroundColor: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem',
              }}
            >
              清除选择
            </button>
          </>
        )}
      </div>

      <div style={{
        backgroundColor: '#f9fafb',
        padding: '16px',
        borderRadius: '8px',
        marginBottom: '24px',
      }}>
        <div style={{ display: 'flex', gap: '32px', fontSize: '0.9rem' }}>
          <div>
            <span style={{ color: '#6b7280' }}>知识库数量: </span>
            <strong>{visibleDatasets.length}{visibleDatasets.length !== datasets.length ? ` / ${datasets.length}` : ''}</strong>
          </div>
          <div>
            <span style={{ color: '#6b7280' }}>文档总数: </span>
            <strong>{getTotalDocumentCount()}</strong>
          </div>
        </div>
      </div>

      <div style={{
        backgroundColor: 'white',
        padding: '16px',
        borderRadius: '8px',
        border: '1px solid #e5e7eb',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '6px' }}>知识库筛选（关键词）</div>
            <input
              value={datasetFilterKeyword}
              onChange={(e) => setDatasetFilterKeyword(e.target.value)}
              onBlur={() => commitDatasetKeywordToHistory(datasetFilterKeyword)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  commitDatasetKeywordToHistory(datasetFilterKeyword);
                }
              }}
              placeholder="输入关键词，只显示包含该关键词的知识库（名称或ID）"
              data-testid="browser-dataset-filter"
              list="browser-dataset-filter-recent"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '6px',
                border: '1px solid #d1d5db',
                outline: 'none',
              }}
            />
            <datalist id="browser-dataset-filter-recent">
              {(recentDatasetKeywords || []).map((k) => (
                <option key={k} value={k} />
              ))}
            </datalist>
          </div>
          <button
            type="button"
            onClick={() => setDatasetFilterKeyword('')}
            data-testid="browser-dataset-filter-clear"
            style={{
              padding: '10px 14px',
              backgroundColor: '#f3f4f6',
              color: '#111827',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              cursor: 'pointer',
              marginTop: '22px',
              whiteSpace: 'nowrap',
            }}
          >
            清空
          </button>
        </div>

        {(recentDatasetKeywords || []).length > 0 && (
          <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>最近:</div>
            {(recentDatasetKeywords || []).slice(0, 5).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setDatasetFilterKeyword(k)}
                style={{
                  padding: '4px 10px',
                  border: '1px solid #d1d5db',
                  backgroundColor: '#fff',
                  borderRadius: '999px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  color: '#374151',
                }}
                title="点击填入关键词"
              >
                {k}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div style={{
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          padding: '12px 16px',
          borderRadius: '4px',
          marginBottom: '20px',
        }} data-testid="browser-error">
          {error}
        </div>
      )}

      {datasets.length === 0 ? (
        <div style={{
          backgroundColor: 'white',
          padding: '48px',
          borderRadius: '8px',
          textAlign: 'center',
          color: '#6b7280',
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📚</div>
          <div>暂无知识库</div>
        </div>
      ) : visibleDatasets.length === 0 ? (
        <div style={{
          backgroundColor: 'white',
          padding: '48px',
          borderRadius: '8px',
          textAlign: 'center',
          color: '#6b7280',
          border: '1px solid #e5e7eb',
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '12px' }}>🔎</div>
          <div style={{ fontWeight: 700, marginBottom: '6px', color: '#374151' }}>没有匹配的知识库</div>
          <div style={{ fontSize: '0.9rem' }}>请调整关键词，或点击“清空”显示全部。</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {visibleDatasets.map((dataset) => {
            const datasetDocs = documents[dataset.name] || [];
            const datasetError = documentErrors[dataset.name] || '';
            const isExpanded = expandedDatasets.has(dataset.name);
            const loadingDocs = !Object.prototype.hasOwnProperty.call(documents, dataset.name) && !datasetError;

            return (
              <div
                key={dataset.id}
                data-testid={`browser-dataset-${dataset.id}`}
                style={{
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                  overflow: 'hidden',
                }}
              >
                <div
                  onClick={() => toggleDataset(dataset.name)}
                  data-testid={`browser-dataset-toggle-${dataset.id}`}
                  style={{
                    padding: '16px 20px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    backgroundColor: '#f9fafb',
                    transition: 'background-color 0.2s',
                  }}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#f3f4f6'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = '#f9fafb'}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{
                      fontSize: '1.5rem',
                      transition: 'transform 0.2s',
                      transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    }}>
                      ▶
                    </div>
                    <div>
                      <div style={{ fontWeight: 'bold', fontSize: '1.1rem', color: '#1f2937' }}>
                        {dataset.name}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#6b7280', marginTop: '4px' }}>
                        {loadingDocs ? '加载中...' : `${datasetDocs.length} 个文档`}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {datasetDocs.length > 0 && (
                      <span style={{
                        padding: '4px 8px',
                        backgroundColor: '#dbeafe',
                        color: '#1e40af',
                        borderRadius: '4px',
                        fontSize: '0.85rem',
                      }}>
                        {datasetDocs.length}
                      </span>
                    )}
                  </div>
                </div>

                {isExpanded && (
                  <div style={{ padding: '16px 20px' }}>
                    {loadingDocs ? (
                      <div style={{ textAlign: 'center', padding: '32px', color: '#6b7280' }}>
                        加载文档中...
                      </div>
                    ) : datasetError ? (
                      <div style={{ textAlign: 'center', padding: '32px', color: '#dc2626' }}>
                        <div style={{ marginBottom: '10px' }}>Load failed: {datasetError}</div>
                        <button
                          onClick={() => fetchDocumentsForDataset(dataset.name)}
                          style={{
                            padding: '8px 14px',
                            backgroundColor: '#2563eb',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '0.9rem',
                          }}
                        >
                          Retry
                        </button>
                      </div>
                    ) : datasetDocs.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: '32px', color: '#6b7280' }}>
                        No documents in this knowledge base
                      </div>
                    ) : (
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                            <th style={{ padding: '12px 8px', textAlign: 'left', fontSize: '0.9rem', color: '#6b7280', width: '40px' }}>
                              <input
                                type="checkbox"
                                checked={isAllSelectedInDataset(dataset.name)}
                                onChange={() => handleSelectAllInDataset(dataset.name)}
                                data-testid={`browser-dataset-selectall-${dataset.id}`}
                                style={{ cursor: 'pointer' }}
                              />
                            </th>
                            <th style={{ padding: '12px 8px', textAlign: 'left', fontSize: '0.9rem', color: '#6b7280' }}>
                              文档名称
                            </th>
                            <th style={{ padding: '12px 8px', textAlign: 'left', fontSize: '0.9rem', color: '#6b7280' }}>
                              状态
                            </th>
                            <th style={{ padding: '12px 8px', textAlign: 'center', fontSize: '0.9rem', color: '#6b7280' }}>
                              文档ID
                            </th>
                            <th style={{ padding: '12px 8px', textAlign: 'right', fontSize: '0.9rem', color: '#6b7280' }}>
                              操作
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {datasetDocs.map((doc) => (
                            <tr
                              key={doc.id}
                              data-testid={`browser-doc-row-${dataset.id}-${doc.id}`}
                              style={{ borderBottom: '1px solid #f3f4f6' }}
                            >
                              <td style={{ padding: '12px 8px', width: '40px' }}>
                                <input
                                  type="checkbox"
                                  checked={isDocSelected(doc.id, dataset.name)}
                                  onChange={() => handleSelectDoc(doc.id, dataset.name)}
                                  data-testid={`browser-doc-select-${dataset.id}-${doc.id}`}
                                  style={{ cursor: 'pointer' }}
                                />
                              </td>
                              <td style={{ padding: '12px 8px', fontSize: '0.95rem' }}>
                                {doc.name}
                              </td>
                              <td style={{ padding: '12px 8px' }}>
                                <span style={{
                                  display: 'inline-block',
                                  padding: '4px 8px',
                                  borderRadius: '4px',
                                  backgroundColor: getStatusColor(doc.status),
                                  color: 'white',
                                  fontSize: '0.8rem',
                                }}>
                                  {getStatusName(doc.status)}
                                </span>
                              </td>
                              <td style={{ padding: '12px 8px', textAlign: 'center', fontSize: '0.8rem', color: '#9ca3af' }}>
                                {doc.id.slice(0, 8)}...
                              </td>
                              <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                                  <button
                                    onClick={() => handleView(doc.id, dataset.name)}
                                    disabled={actionLoading[`${doc.id}-view`]}
                                    data-testid={`browser-doc-view-${dataset.id}-${doc.id}`}
                                    title="查看"
                                    style={{
                                      padding: '6px 12px',
                                      backgroundColor: '#8b5cf6',
                                      color: 'white',
                                      border: 'none',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      fontSize: '0.85rem',
                                      opacity: actionLoading[`${doc.id}-view`] ? 0.6 : 1,
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '6px',
                                    }}
                                  >
                                    {actionLoading[`${doc.id}-view`] ? (
                                      <>
                                        <Spinner size={14} />
                                        <span>预览中</span>
                                      </>
                                    ) : (
                                      '查看'
                                    )}
                                  </button>
                                  {canDownload() && (
                                    <button
                                      onClick={() => handleDownload(doc.id, dataset.name)}
                                      disabled={actionLoading[`${doc.id}-download`]}
                                      data-testid={`browser-doc-download-${dataset.id}-${doc.id}`}
                                      title="下载"
                                      style={{
                                        padding: '6px 12px',
                                        backgroundColor: '#3b82f6',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        fontSize: '0.85rem',
                                        opacity: actionLoading[`${doc.id}-download`] ? 0.6 : 1,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                      }}
                                    >
                                      {actionLoading[`${doc.id}-download`] ? (
                                        <>
                                          <Spinner size={14} />
                                          <span>下载中</span>
                                        </>
                                      ) : (
                                        '下载'
                                      )}
                                    </button>
                                  )}
                                  {canDelete() && (
                                    <button
                                      onClick={() => handleDelete(doc.id, dataset.name)}
                                      disabled={actionLoading[`${doc.id}-delete`]}
                                      data-testid={`browser-doc-delete-${dataset.id}-${doc.id}`}
                                      title="删除"
                                      style={{
                                        padding: '6px 12px',
                                        backgroundColor: '#ef4444',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        fontSize: '0.85rem',
                                        opacity: actionLoading[`${doc.id}-delete`] ? 0.6 : 1,
                                      }}
                                    >
                                      删除
                                    </button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <DocumentPreviewModal
        open={previewOpen}
        target={previewTarget}
        onClose={closePreview}
        canDownloadFiles={typeof canDownload === 'function' ? !!canDownload() : false}
      />
    </div>
  );
};

export default DocumentBrowser;
