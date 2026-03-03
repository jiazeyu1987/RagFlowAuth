import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import authClient from '../api/authClient';
import { knowledgeApi } from '../features/knowledge/api';
import { useAuth } from '../hooks/useAuth';
import documentClient, { DOCUMENT_SOURCE } from '../shared/documents/documentClient';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

const ROOT = '';
const TEXT = {
  title: '\u6587\u6863\u6d4f\u89c8',
  desc: '\u6587\u6863\u6d4f\u89c8\u7684\u77e5\u8bc6\u5e93\u76ee\u5f55\u5c42\u7ea7\u4e0e\u77e5\u8bc6\u914d\u7f6e\u4fdd\u6301\u4e00\u81f4\u3002',
  root: '\u6839\u76ee\u5f55',
  folder: '\u6587\u4ef6\u5939',
  datasets: '\u77e5\u8bc6\u5e93\u6570\u91cf',
  docs: '\u6587\u6863\u603b\u6570',
  filter: '\u7b5b\u9009',
  filterPlaceholder: '\u8f93\u5165\u77e5\u8bc6\u5e93\u540d\u79f0\u3001ID \u6216\u76ee\u5f55\u5173\u952e\u8bcd',
  recent: '\u6700\u8fd1',
  clear: '\u6e05\u7a7a',
  noKb: '\u6682\u65e0\u77e5\u8bc6\u5e93',
  noMatch: '\u6ca1\u6709\u5339\u914d\u7684\u77e5\u8bc6\u5e93',
  noMatchDesc: '\u8bf7\u8c03\u6574\u5173\u952e\u8bcd\uff0c\u6216\u70b9\u51fb\u6e05\u7a7a\u663e\u793a\u5168\u90e8\u3002',
  expandAll: '\u5c55\u5f00\u5168\u90e8',
  collapseAll: '\u6298\u53e0\u5168\u90e8',
  refresh: '\u5237\u65b0',
  batch: '\u6279\u91cf\u4e0b\u8f7d',
  packing: '\u6253\u5305\u4e2d',
  clearSelection: '\u6e05\u9664\u9009\u62e9',
  loading: '\u52a0\u8f7d\u4e2d...',
  loadingDocs: '\u52a0\u8f7d\u6587\u6863\u4e2d...',
  noDocs: '\u5f53\u524d\u77e5\u8bc6\u5e93\u4e0b\u6682\u65e0\u6587\u6863',
  retry: 'Retry',
  docName: '\u6587\u6863\u540d\u79f0',
  view: '\u67e5\u770b',
  viewing: '\u9884\u89c8\u4e2d',
  download: '\u4e0b\u8f7d',
  downloading: '\u4e0b\u8f7d\u4e2d',
  delete: '\u5220\u9664',
  deleteConfirm: '\u786e\u5b9a\u8981\u5220\u9664\u8be5\u6587\u6863\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u6062\u590d\u3002',
  needOne: '\u8bf7\u81f3\u5c11\u9009\u62e9\u4e00\u4e2a\u6587\u6863',
  noPermission: '\u60a8\u6ca1\u6709\u88ab\u5206\u914d\u4efb\u4f55\u77e5\u8bc6\u5e93\u6743\u9650\uff0c\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458',
  loadKbFail: '\u52a0\u8f7d\u77e5\u8bc6\u5e93\u5931\u8d25',
  loadDocFail: '\u52a0\u8f7d\u6587\u6863\u5931\u8d25',
  downloadFail: '\u4e0b\u8f7d\u5931\u8d25',
  deleteFail: '\u5220\u9664\u5931\u8d25',
  batchFail: '\u6279\u91cf\u4e0b\u8f7d\u5931\u8d25',
  cannotFindKb: '\u65e0\u6cd5\u627e\u5230\u77e5\u8bc6\u5e93',
  cannotFindDocPrefix: '\u65e0\u6cd5\u5728\u77e5\u8bc6\u5e93',
  currentFolder: '\u5f53\u524d\u76ee\u5f55',
  emptyFolder: '\u5f53\u524d\u76ee\u5f55\u4e0b\u6682\u65e0\u77e5\u8bc6\u5e93',
};

function actionButtonStyle(kind, disabled) {
  const palette = {
    view: { background: '#eef2ff', color: '#4338ca', border: '#c7d2fe' },
    download: { background: '#eff6ff', color: '#1d4ed8', border: '#bfdbfe' },
    delete: { background: '#fef2f2', color: '#dc2626', border: '#fecaca' },
  };
  const tone = palette[kind] || palette.view;
  return {
    padding: '7px 12px',
    borderRadius: 999,
    border: `1px solid ${tone.border}`,
    background: tone.background,
    color: tone.color,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.55 : 1,
    fontSize: '0.84rem',
    fontWeight: 700,
    lineHeight: 1,
    boxShadow: disabled ? 'none' : '0 1px 2px rgba(15, 23, 42, 0.06)',
  };
}

function toolbarButtonStyle(kind, disabled = false) {
  const palette = {
    primary: { background: '#e0f2fe', color: '#075985', border: '#bae6fd' },
    neutral: { background: '#f3f4f6', color: '#374151', border: '#d1d5db' },
    success: { background: '#ecfdf5', color: '#047857', border: '#a7f3d0' },
    accent: { background: '#f5f3ff', color: '#6d28d9', border: '#ddd6fe' },
    danger: { background: '#fef2f2', color: '#dc2626', border: '#fecaca' },
  };
  const tone = palette[kind] || palette.neutral;
  return {
    padding: '9px 14px',
    borderRadius: 999,
    border: `1px solid ${tone.border}`,
    background: tone.background,
    color: tone.color,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.55 : 1,
    fontSize: '0.9rem',
    fontWeight: 700,
    lineHeight: 1,
    boxShadow: disabled ? 'none' : '0 1px 2px rgba(15, 23, 42, 0.06)',
    whiteSpace: 'nowrap',
  };
}

function buildIndexes(tree) {
  const byId = new Map();
  const childrenByParent = new Map();
  (tree?.nodes || []).forEach((n) => {
    if (!n?.id) return;
    byId.set(n.id, n);
    const parent = n.parent_id || ROOT;
    if (!childrenByParent.has(parent)) childrenByParent.set(parent, []);
    childrenByParent.get(parent).push(n);
  });
  for (const list of childrenByParent.values()) {
    list.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }
  return { byId, childrenByParent };
}

function pathNodes(nodeId, byId) {
  if (!nodeId) return [];
  const out = [];
  const seen = new Set();
  let cur = nodeId;
  while (cur && !seen.has(cur)) {
    seen.add(cur);
    const node = byId.get(cur);
    if (!node) break;
    out.push(node);
    cur = node.parent_id || ROOT;
  }
  return out.reverse();
}

function buildDatasetsWithFolders(datasets, tree) {
  const byId = new Map();
  const byName = new Map();
  (tree?.datasets || []).forEach((d) => {
    if (d?.id) byId.set(d.id, d);
    if (d?.name) byName.set(d.name, d);
  });
  return (datasets || []).map((dataset) => {
    const matched = byId.get(dataset.id) || byName.get(dataset.name);
    return {
      ...dataset,
      node_id: matched?.node_id || ROOT,
      node_path: matched?.node_path || '/',
    };
  });
}

function FolderTree({ indexes, currentFolderId, expandedFolderIds, onToggleExpand, onOpenFolder, visibleNodeIds }) {
  const renderFolder = (folder, depth) => {
    const children = (indexes.childrenByParent.get(folder.id) || []).filter((n) => visibleNodeIds.has(n.id));
    const hasChildren = children.length > 0;
    const isExpanded = expandedFolderIds.includes(folder.id);
    const isCurrent = currentFolderId === folder.id;
    return (
      <div key={folder.id}>
        <div
          style={{
            marginLeft: depth * 16,
            borderRadius: 6,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 6px',
            background: isCurrent ? '#dbeafe' : 'transparent',
          }}
        >
          <button
            type="button"
            onClick={() => hasChildren && onToggleExpand(folder.id)}
            style={{ width: 14, border: 'none', background: 'transparent', cursor: hasChildren ? 'pointer' : 'default', color: '#6b7280', padding: 0 }}
          >
            {hasChildren ? (isExpanded ? '▾' : '▸') : ''}
          </button>
          <button
            type="button"
            onClick={() => onOpenFolder(folder.id)}
            style={{ border: 'none', background: 'transparent', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}
            title={folder.path || folder.name}
          >
            {'📁 '} {folder.name || TEXT.folder}
          </button>
        </div>
        {isExpanded && children.map((child) => renderFolder(child, depth + 1))}
      </div>
    );
  };

  const roots = (indexes.childrenByParent.get(ROOT) || []).filter((n) => visibleNodeIds.has(n.id));
  return (
    <div>
      <div style={{ borderRadius: 6, padding: '3px 6px', marginBottom: 6, background: currentFolderId === ROOT ? '#dbeafe' : 'transparent' }}>
        <button type="button" onClick={() => onOpenFolder(ROOT)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', width: '100%', textAlign: 'left', padding: 0 }}>
          {'🖥️ '} {TEXT.root}
        </button>
      </div>
      {roots.map((folder) => renderFolder(folder, 0))}
      {!roots.length ? <div style={{ color: '#6b7280', fontSize: 13 }}>{TEXT.noKb}</div> : null}
    </div>
  );
}

function DatasetPanel({
  dataset,
  documents,
  documentErrors,
  expandedDatasets,
  toggleDataset,
  fetchDocumentsForDataset,
  isAllSelectedInDataset,
  handleSelectAllInDataset,
  isDocSelected,
  handleSelectDoc,
  handleView,
  handleDownload,
  handleDelete,
  actionLoading,
  canDownload,
  canDelete,
}) {
  const datasetDocs = documents[dataset.name] || [];
  const datasetError = documentErrors[dataset.name] || '';
  const isExpanded = expandedDatasets.has(dataset.name);
  const loadingDocs = !Object.prototype.hasOwnProperty.call(documents, dataset.name) && !datasetError;

  return (
    <div data-testid={`browser-dataset-${dataset.id}`} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
      <div data-testid={`browser-dataset-toggle-${dataset.id}`} onClick={() => toggleDataset(dataset.name)} style={{ padding: '14px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', background: '#f9fafb' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: '1rem', transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>{'>'}</div>
          <div>
            <div style={{ fontWeight: 700, color: '#111827' }}>{dataset.name}</div>
            <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: 2 }}>{dataset.node_path && dataset.node_path !== '/' ? `${TEXT.root} -> ${dataset.node_path.split('/').filter(Boolean).join(' -> ')}` : TEXT.root}</div>
          </div>
        </div>
        <span style={{ padding: '4px 8px', background: '#dbeafe', color: '#1e40af', borderRadius: 4, fontSize: '0.85rem' }}>{loadingDocs ? '...' : datasetDocs.length}</span>
      </div>

      {isExpanded ? (
        <div style={{ padding: 16 }}>
          {loadingDocs ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 20 }}>{TEXT.loadingDocs}</div> : null}
          {!loadingDocs && datasetError ? (
            <div style={{ color: '#dc2626', textAlign: 'center', padding: 20 }}>
              <div style={{ marginBottom: 10 }}>Load failed: {datasetError}</div>
              <button onClick={() => fetchDocumentsForDataset(dataset.name)}>{TEXT.retry}</button>
            </div>
          ) : null}
          {!loadingDocs && !datasetError && datasetDocs.length === 0 ? <div style={{ color: '#6b7280', textAlign: 'center', padding: 20 }}>{TEXT.noDocs}</div> : null}
          {!loadingDocs && !datasetError && datasetDocs.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ width: 40, textAlign: 'left', padding: '12px 8px' }}>
                    <input type="checkbox" checked={isAllSelectedInDataset(dataset.name)} onChange={() => handleSelectAllInDataset(dataset.name)} data-testid={`browser-dataset-selectall-${dataset.id}`} />
                  </th>
                  <th style={{ textAlign: 'left', padding: '12px 8px', color: '#6b7280' }}>{TEXT.docName}</th>
                  <th style={{ textAlign: 'right', padding: '12px 8px', color: '#6b7280', width: 260 }}>{'\u64cd\u4f5c'}</th>
                </tr>
              </thead>
              <tbody>
                {datasetDocs.map((doc) => (
                  <tr key={doc.id} data-testid={`browser-doc-row-${dataset.id}-${doc.id}`} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '12px 8px' }}>
                      <input type="checkbox" checked={isDocSelected(doc.id, dataset.name)} onChange={() => handleSelectDoc(doc.id, dataset.name)} data-testid={`browser-doc-select-${dataset.id}-${doc.id}`} />
                    </td>
                    <td style={{ padding: '12px 8px', fontWeight: 500, color: '#111827' }}>{doc.name}</td>
                    <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                        <button onClick={() => handleView(doc.id, dataset.name)} data-testid={`browser-doc-view-${dataset.id}-${doc.id}`} disabled={actionLoading[`${doc.id}-view`]} style={actionButtonStyle('view', actionLoading[`${doc.id}-view`])}>{actionLoading[`${doc.id}-view`] ? TEXT.viewing : `\u67e5\u770b`}</button>
                        {canDownload() ? <button onClick={() => handleDownload(doc.id, dataset.name)} data-testid={`browser-doc-download-${dataset.id}-${doc.id}`} disabled={actionLoading[`${doc.id}-download`]} style={actionButtonStyle('download', actionLoading[`${doc.id}-download`])}>{actionLoading[`${doc.id}-download`] ? TEXT.downloading : `\u4e0b\u8f7d`}</button> : null}
                        {canDelete() ? <button onClick={() => handleDelete(doc.id, dataset.name)} data-testid={`browser-doc-delete-${dataset.id}-${doc.id}`} disabled={actionLoading[`${doc.id}-delete`]} style={actionButtonStyle('delete', actionLoading[`${doc.id}-delete`])}>{`\u5220\u9664`}</button> : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default function DocumentBrowser() {
  const location = useLocation();
  const { user, can, canDownload, accessibleKbs } = useAuth();
  const [datasets, setDatasets] = useState([]);
  const [directoryTree, setDirectoryTree] = useState({ nodes: [], datasets: [] });
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
  const [canDeleteDocs, setCanDeleteDocs] = useState(false);
  const [currentFolderId, setCurrentFolderId] = useState(ROOT);
  const [expandedFolderIds, setExpandedFolderIds] = useState([]);
  const viewRef = useRef(null);

  const indexes = useMemo(() => buildIndexes(directoryTree), [directoryTree]);
  const datasetsWithFolders = useMemo(() => buildDatasetsWithFolders(datasets, directoryTree), [datasets, directoryTree]);
  const normalizedKeyword = String(datasetFilterKeyword || '').trim().toLowerCase();

  const visibleDatasets = useMemo(() => {
    if (!normalizedKeyword) return datasetsWithFolders;
    return datasetsWithFolders.filter((d) => {
      const folderText = d.node_path && d.node_path !== '/' ? `${TEXT.root} ${d.node_path}` : TEXT.root;
      return String(d.name || '').toLowerCase().includes(normalizedKeyword)
        || String(d.id || '').toLowerCase().includes(normalizedKeyword)
        || folderText.toLowerCase().includes(normalizedKeyword);
    });
  }, [datasetsWithFolders, normalizedKeyword]);

  const visibleNodeIds = useMemo(() => {
    const ids = new Set();
    visibleDatasets.forEach((d) => {
      pathNodes(d.node_id, indexes.byId).forEach((n) => ids.add(n.id));
    });
    return ids;
  }, [visibleDatasets, indexes.byId]);

  const folderBreadcrumb = useMemo(() => [
    { id: ROOT, name: TEXT.root },
    ...pathNodes(currentFolderId, indexes.byId).map((n) => ({ id: n.id, name: n.name || TEXT.folder })),
  ], [currentFolderId, indexes.byId]);

  const datasetsInCurrentFolder = useMemo(() => {
    const list = visibleDatasets.filter((d) => (d.node_id || ROOT) === currentFolderId);
    return list.sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN'));
  }, [visibleDatasets, currentFolderId]);

  useEffect(() => {
    const storageKey = `ragflowauth_recent_dataset_keywords_v1:${user?.user_id || 'anon'}`;
    try {
      const values = JSON.parse(window.localStorage.getItem(storageKey) || '[]');
      setRecentDatasetKeywords(Array.isArray(values) ? values.filter((x) => typeof x === 'string' && x.trim()).slice(0, 5) : []);
    } catch {
      setRecentDatasetKeywords([]);
    }
  }, [user?.user_id]);

  useEffect(() => {
    setDocuments({});
    setDocumentErrors({});
    setExpandedDatasets(new Set());
    setSelectedDocs({});
    setDirectoryTree({ nodes: [], datasets: [] });
    setCurrentFolderId(ROOT);
    setExpandedFolderIds([]);
  }, [user?.user_id]);

  useEffect(() => {
    setCanDeleteDocs(can('ragflow_documents', 'delete'));
  }, [can, user?.user_id]);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [datasetRes, treeRes] = await Promise.all([
          authClient.listRagflowDatasets(),
          knowledgeApi.listKnowledgeDirectories().catch(() => ({ nodes: [], datasets: [] })),
        ]);
        const nextDatasets = datasetRes?.datasets || [];
        setDatasets(nextDatasets);
        setDirectoryTree(treeRes && typeof treeRes === 'object' ? treeRes : { nodes: [], datasets: [] });
        setError(nextDatasets.length ? null : TEXT.noPermission);
      } catch (err) {
        setError(err?.message || TEXT.loadKbFail);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [accessibleKbs, user]);

  const fetchDocumentsForDataset = async (datasetName) => {
    try {
      setDocumentErrors((prev) => {
        const next = { ...prev };
        delete next[datasetName];
        return next;
      });
      const data = await authClient.listRagflowDocuments(datasetName);
      setDocuments((prev) => ({ ...prev, [datasetName]: data.documents || [] }));
    } catch (err) {
      setDocumentErrors((prev) => ({ ...prev, [datasetName]: err?.message || TEXT.loadDocFail }));
      setDocuments((prev) => ({ ...prev, [datasetName]: [] }));
    }
  };

  useEffect(() => {
    visibleDatasets.forEach((dataset) => {
      if (!documents[dataset.name]) fetchDocumentsForDataset(dataset.name);
    });
  }, [visibleDatasets, documents]);

  useEffect(() => {
    if (!location.state?.documentId || datasetsWithFolders.length === 0) return undefined;
    const { documentId, documentName, datasetId } = location.state;
    const targetDataset = datasetsWithFolders.find((d) => d.id === datasetId);
    if (!targetDataset) {
      setError(`${TEXT.cannotFindKb}: ${datasetId}`);
      return undefined;
    }
    const datasetName = targetDataset.name || targetDataset.id;
    const nodeIds = pathNodes(targetDataset.node_id, indexes.byId).map((n) => n.id);
    setCurrentFolderId(targetDataset.node_id || ROOT);
    setExpandedFolderIds((prev) => Array.from(new Set([...prev, ...nodeIds])));
    setExpandedDatasets((prev) => new Set([...prev, datasetName]));
    if (!documents[datasetName]) fetchDocumentsForDataset(datasetName);
    const timer = setInterval(() => {
      if (documents[datasetName]) {
        clearInterval(timer);
        const target = documents[datasetName].find((doc) => doc.id === documentId);
        if (target) viewRef.current?.(documentId, datasetName);
        else setError(`${TEXT.cannotFindDocPrefix} "${datasetName}" found no doc: ${documentName}`);
      }
    }, 300);
    const timeout = setTimeout(() => clearInterval(timer), 10000);
    return () => {
      clearInterval(timer);
      clearTimeout(timeout);
    };
  }, [location.state, datasetsWithFolders, documents, indexes.byId]);

  const toggleDataset = (datasetName) => {
    setExpandedDatasets((prev) => {
      const next = new Set(prev);
      if (next.has(datasetName)) next.delete(datasetName);
      else next.add(datasetName);
      return next;
    });
    if (!documents[datasetName]) fetchDocumentsForDataset(datasetName);
  };

  const openFolder = (folderId) => {
    const next = folderId || ROOT;
    setCurrentFolderId(next);
    const pathIds = pathNodes(next, indexes.byId).map((n) => n.id);
    setExpandedFolderIds((prev) => Array.from(new Set([...prev, ...pathIds])));
  };

  const toggleFolderExpand = (folderId) => {
    setExpandedFolderIds((prev) => (prev.includes(folderId) ? prev.filter((id) => id !== folderId) : [...prev, folderId]));
  };

  const expandAll = () => {
    setExpandedDatasets(new Set(datasetsInCurrentFolder.map((d) => d.name)));
    visibleDatasets.forEach((d) => {
      if (!documents[d.name]) fetchDocumentsForDataset(d.name);
    });
  };

  const collapseAll = () => setExpandedDatasets(new Set());
  const refreshAll = () => {
    setDocuments({});
    visibleDatasets.forEach((d) => fetchDocumentsForDataset(d.name));
  };

  const handleView = (docId, datasetName) => {
    const doc = documents[datasetName]?.find((x) => x.id === docId);
    setPreviewTarget({ source: DOCUMENT_SOURCE.RAGFLOW, docId, datasetName, filename: doc?.name || `document_${docId}` });
    setPreviewOpen(true);
  };
  viewRef.current = handleView;

  const handleDownload = async (docId, datasetName) => {
    const doc = documents[datasetName]?.find((x) => x.id === docId);
    try {
      setActionLoading((prev) => ({ ...prev, [`${docId}-download`]: true }));
      await documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.RAGFLOW, docId, datasetName, filename: doc?.name || `document_${docId}` });
    } catch (err) {
      setError(err?.message || TEXT.downloadFail);
    } finally {
      setActionLoading((prev) => ({ ...prev, [`${docId}-download`]: false }));
    }
  };

  const handleDelete = async (docId, datasetName) => {
    if (!window.confirm(TEXT.deleteConfirm)) return;
    try {
      setActionLoading((prev) => ({ ...prev, [`${docId}-delete`]: true }));
      await documentClient.delete({ source: DOCUMENT_SOURCE.RAGFLOW, docId, datasetName });
      setDocuments((prev) => ({ ...prev, [datasetName]: (prev[datasetName] || []).filter((x) => x.id !== docId) }));
    } catch (err) {
      setError(err?.message || TEXT.deleteFail);
    } finally {
      setActionLoading((prev) => ({ ...prev, [`${docId}-delete`]: false }));
    }
  };

  const handleSelectDoc = (docId, datasetName) => {
    setSelectedDocs((prev) => {
      const list = prev[datasetName] || [];
      return { ...prev, [datasetName]: list.includes(docId) ? list.filter((id) => id !== docId) : [...list, docId] };
    });
  };
  const handleSelectAllInDataset = (datasetName) => {
    const datasetDocs = documents[datasetName] || [];
    const current = selectedDocs[datasetName] || [];
    setSelectedDocs((prev) => ({ ...prev, [datasetName]: current.length === datasetDocs.length ? [] : datasetDocs.map((d) => d.id) }));
  };
  const isDocSelected = (docId, datasetName) => (selectedDocs[datasetName] || []).includes(docId);
  const isAllSelectedInDataset = (datasetName) => {
    const datasetDocs = documents[datasetName] || [];
    const current = selectedDocs[datasetName] || [];
    return datasetDocs.length > 0 && current.length === datasetDocs.length;
  };

  const selectedCount = Object.values(selectedDocs).reduce((sum, list) => sum + list.length, 0);
  const totalDocs = visibleDatasets.reduce((sum, d) => sum + ((documents[d.name] || []).length), 0);
  const canDelete = () => canDeleteDocs;
  const clearAllSelections = () => setSelectedDocs({});

  const handleBatchDownload = async () => {
    const items = [];
    Object.entries(selectedDocs).forEach(([dataset, docIds]) => {
      docIds.forEach((docId) => {
        const doc = (documents[dataset] || []).find((x) => x.id === docId);
        if (doc) items.push({ doc_id: docId, dataset, name: doc.name });
      });
    });
    if (!items.length) {
      setError(TEXT.needOne);
      return;
    }
    try {
      setActionLoading((prev) => ({ ...prev, 'batch-download': true }));
      await documentClient.batchDownloadRagflowToBrowser(items);
      clearAllSelections();
    } catch (err) {
      setError(err?.message || TEXT.batchFail);
    } finally {
      setActionLoading((prev) => ({ ...prev, 'batch-download': false }));
    }
  };

  const commitKeyword = (value) => {
    const v = String(value || '').trim();
    if (!v) return;
    const next = [v, ...recentDatasetKeywords].filter(Boolean).filter((x, i, arr) => arr.findIndex((y) => y.toLowerCase() === x.toLowerCase()) === i).slice(0, 5);
    setRecentDatasetKeywords(next);
    try {
      window.localStorage.setItem(`ragflowauth_recent_dataset_keywords_v1:${user?.user_id || 'anon'}`, JSON.stringify(next));
    } catch {
      // ignore
    }
  };

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400, color: '#6b7280' }}>{TEXT.loading}</div>;
  }

  return (
    <div data-testid="browser-page">
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: '0 0 8px 0' }}>{TEXT.title}</h2>
        <p style={{ margin: 0, color: '#6b7280', fontSize: '0.9rem' }}>{TEXT.desc}</p>
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 24 }}>
        <button onClick={expandAll} data-testid="browser-expand-all" style={toolbarButtonStyle('primary')}>{TEXT.expandAll}</button>
        <button onClick={collapseAll} data-testid="browser-collapse-all" style={toolbarButtonStyle('neutral')}>{TEXT.collapseAll}</button>
        <button onClick={refreshAll} data-testid="browser-refresh-all" style={toolbarButtonStyle('success')}>{TEXT.refresh}</button>
        {selectedCount > 0 && canDownload() ? <button onClick={handleBatchDownload} data-testid="browser-batch-download" style={toolbarButtonStyle('accent', actionLoading['batch-download'])}>{actionLoading['batch-download'] ? TEXT.packing : `${TEXT.batch} (${selectedCount})`}</button> : null}
        {selectedCount > 0 && canDownload() ? <button onClick={clearAllSelections} data-testid="browser-clear-selection" style={toolbarButtonStyle('danger')}>{TEXT.clearSelection}</button> : null}
      </div>

      <div style={{ background: '#f9fafb', padding: 16, borderRadius: 8, marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
          <div>{TEXT.datasets}: <strong>{visibleDatasets.length}{visibleDatasets.length !== datasetsWithFolders.length ? ` / ${datasetsWithFolders.length}` : ''}</strong></div>
          <div>{TEXT.docs}: <strong>{totalDocs}</strong></div>
        </div>
      </div>

      <div style={{ background: '#fff', padding: 16, borderRadius: 8, border: '1px solid #e5e7eb', marginBottom: 16 }}>
        <div style={{ marginBottom: 6, color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.filter}</div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <input value={datasetFilterKeyword} onChange={(e) => setDatasetFilterKeyword(e.target.value)} onBlur={() => commitKeyword(datasetFilterKeyword)} onKeyDown={(e) => { if (e.key === 'Enter') commitKeyword(datasetFilterKeyword); }} placeholder={TEXT.filterPlaceholder} data-testid="browser-dataset-filter" list="browser-dataset-filter-recent" style={{ flex: 1, padding: '10px 12px', borderRadius: 6, border: '1px solid #d1d5db' }} />
          <button onClick={() => setDatasetFilterKeyword('')} data-testid="browser-dataset-filter-clear" style={toolbarButtonStyle('neutral')}>{TEXT.clear}</button>
        </div>
        <datalist id="browser-dataset-filter-recent">
          {recentDatasetKeywords.map((value) => <option key={value} value={value} />)}
        </datalist>
        {recentDatasetKeywords.length ? (
          <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ color: '#6b7280', fontSize: '0.85rem' }}>{TEXT.recent}</div>
            {recentDatasetKeywords.map((value) => <button key={value} onClick={() => setDatasetFilterKeyword(value)} style={toolbarButtonStyle('neutral')}>{value}</button>)}
          </div>
        ) : null}
      </div>

      {error ? <div style={{ background: '#fee2e2', color: '#991b1b', padding: '12px 16px', borderRadius: 4, marginBottom: 20 }} data-testid="browser-error">{error}</div> : null}

      {!datasetsWithFolders.length ? <div style={{ background: '#fff', padding: 48, borderRadius: 8, textAlign: 'center', color: '#6b7280' }}>{TEXT.noKb}</div> : null}
      {datasetsWithFolders.length && !visibleDatasets.length ? <div style={{ background: '#fff', padding: 48, borderRadius: 8, textAlign: 'center', color: '#6b7280', border: '1px solid #e5e7eb' }}><div style={{ fontWeight: 700, color: '#374151', marginBottom: 6 }}>{TEXT.noMatch}</div><div>{TEXT.noMatchDesc}</div></div> : null}

      {datasetsWithFolders.length && visibleDatasets.length ? (
        <div style={{ display: 'grid', gridTemplateColumns: '260px minmax(0, 1fr)', gap: 16, alignItems: 'start' }}>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, position: 'sticky', top: 12 }}>
            <FolderTree
              indexes={indexes}
              currentFolderId={currentFolderId}
              expandedFolderIds={expandedFolderIds}
              onToggleExpand={toggleFolderExpand}
              onOpenFolder={openFolder}
              visibleNodeIds={visibleNodeIds}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: 8 }}>{TEXT.currentFolder}</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                {folderBreadcrumb.map((item, idx) => (
                  <React.Fragment key={item.id || `root-${idx}`}>
                    <button type="button" onClick={() => openFolder(item.id)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: currentFolderId === item.id ? '#1d4ed8' : '#374151', fontWeight: currentFolderId === item.id ? 700 : 500, padding: 0 }}>
                      {item.name}
                    </button>
                    {idx < folderBreadcrumb.length - 1 ? <span style={{ color: '#9ca3af' }}>{'>'}</span> : null}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {datasetsInCurrentFolder.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {datasetsInCurrentFolder.map((dataset) => (
                  <DatasetPanel
                    key={dataset.id}
                    dataset={dataset}
                    documents={documents}
                    documentErrors={documentErrors}
                    expandedDatasets={expandedDatasets}
                    toggleDataset={toggleDataset}
                    fetchDocumentsForDataset={fetchDocumentsForDataset}
                    isAllSelectedInDataset={isAllSelectedInDataset}
                    handleSelectAllInDataset={handleSelectAllInDataset}
                    isDocSelected={isDocSelected}
                    handleSelectDoc={handleSelectDoc}
                    handleView={handleView}
                    handleDownload={handleDownload}
                    handleDelete={handleDelete}
                    actionLoading={actionLoading}
                    canDownload={canDownload}
                    canDelete={canDelete}
                  />
                ))}
              </div>
            ) : (
              <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 48, textAlign: 'center', color: '#6b7280' }}>{TEXT.emptyFolder}</div>
            )}
          </div>
        </div>
      ) : null}

      <DocumentPreviewModal open={previewOpen} target={previewTarget} onClose={() => { setPreviewOpen(false); setPreviewTarget(null); }} canDownloadFiles={typeof canDownload === 'function' ? !!canDownload() : false} />
    </div>
  );
}
