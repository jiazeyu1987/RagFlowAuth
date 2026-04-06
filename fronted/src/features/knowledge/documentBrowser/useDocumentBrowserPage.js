import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../../../hooks/useAuth';
import { DOCUMENT_SOURCE } from '../../../shared/documents/constants';
import { documentsApi } from '../../documents/api';
import { knowledgeApi } from '../api';
import { documentBrowserApi } from './api';
import { ROOT, TEXT } from './constants';
import { buildDatasetsWithFolders, buildIndexes, pathNodes } from './treeUtils';

export default function useDocumentBrowserPage() {
  const location = useLocation();
  const { user, can, canDownload, accessibleKbs } = useAuth();

  const [datasets, setDatasets] = useState([]);
  const [directoryTree, setDirectoryTree] = useState({ nodes: [], datasets: [] });
  const [datasetFilterKeyword, setDatasetFilterKeyword] = useState('');
  const [recentDatasetKeywords, setRecentDatasetKeywords] = useState([]);
  const [datasetUsageCounts, setDatasetUsageCounts] = useState({});
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
  const [canUploadDocs, setCanUploadDocs] = useState(false);
  const [transferDialog, setTransferDialog] = useState(null);
  const [batchTransferProgress, setBatchTransferProgress] = useState(null);
  const [currentFolderId, setCurrentFolderId] = useState(ROOT);
  const [expandedFolderIds, setExpandedFolderIds] = useState([]);
  const viewRef = useRef(null);

  const indexes = useMemo(() => buildIndexes(directoryTree), [directoryTree]);
  const datasetsWithFolders = useMemo(
    () => buildDatasetsWithFolders(datasets, directoryTree),
    [datasets, directoryTree]
  );

  const normalizedKeyword = String(datasetFilterKeyword || '').trim().toLowerCase();

  const visibleDatasets = useMemo(() => {
    if (!normalizedKeyword) return datasetsWithFolders;
    return datasetsWithFolders.filter((dataset) => {
      const folderText =
        dataset.node_path && dataset.node_path !== '/'
          ? `${TEXT.root} ${dataset.node_path}`
          : TEXT.root;
      return (
        String(dataset.name || '').toLowerCase().includes(normalizedKeyword) ||
        String(dataset.id || '').toLowerCase().includes(normalizedKeyword) ||
        folderText.toLowerCase().includes(normalizedKeyword)
      );
    });
  }, [datasetsWithFolders, normalizedKeyword]);

  const visibleNodeIds = useMemo(() => {
    const ids = new Set();
    visibleDatasets.forEach((dataset) => {
      pathNodes(dataset.node_id, indexes.byId).forEach((node) => ids.add(node.id));
    });
    return ids;
  }, [visibleDatasets, indexes.byId]);

  const folderBreadcrumb = useMemo(
    () => [
      { id: ROOT, name: TEXT.root },
      ...pathNodes(currentFolderId, indexes.byId).map((node) => ({
        id: node.id,
        name: node.name || TEXT.folder,
      })),
    ],
    [currentFolderId, indexes.byId]
  );

  const datasetsInCurrentFolder = useMemo(() => {
    const list = visibleDatasets.filter(
      (dataset) => (dataset.node_id || ROOT) === currentFolderId
    );
    return list.sort((a, b) =>
      String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN')
    );
  }, [visibleDatasets, currentFolderId]);

  const transferTargetOptions = useMemo(() => {
    const names = datasetsWithFolders
      .map((item) => String(item?.name || '').trim())
      .filter(Boolean);
    return Array.from(new Set(names)).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'));
  }, [datasetsWithFolders]);

  const usageStorageKey = useMemo(
    () => `ragflowauth_browser_dataset_usage_v1:${user?.user_id || 'anon'}`,
    [user?.user_id]
  );

  const quickDatasets = useMemo(() => {
    const counts = datasetUsageCounts || {};
    return [...datasetsWithFolders]
      .sort((a, b) => {
        const countA = Number(counts[a.name] || 0);
        const countB = Number(counts[b.name] || 0);
        if (countA !== countB) return countB - countA;
        return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN');
      })
      .slice(0, 10);
  }, [datasetUsageCounts, datasetsWithFolders]);

  useEffect(() => {
    const storageKey = `ragflowauth_recent_dataset_keywords_v1:${user?.user_id || 'anon'}`;
    try {
      const values = JSON.parse(window.localStorage.getItem(storageKey) || '[]');
      setRecentDatasetKeywords(
        Array.isArray(values)
          ? values
              .filter((value) => typeof value === 'string' && value.trim())
              .slice(0, 5)
          : []
      );
    } catch {
      setRecentDatasetKeywords([]);
    }
  }, [user?.user_id]);

  useEffect(() => {
    try {
      const raw = JSON.parse(window.localStorage.getItem(usageStorageKey) || '{}');
      if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
        setDatasetUsageCounts({});
        return;
      }
      const normalized = {};
      Object.entries(raw).forEach(([key, value]) => {
        const count = Number(value || 0);
        if (key && Number.isFinite(count) && count > 0) normalized[key] = count;
      });
      setDatasetUsageCounts(normalized);
    } catch {
      setDatasetUsageCounts({});
    }
  }, [usageStorageKey]);

  useEffect(() => {
    setDocuments({});
    setDocumentErrors({});
    setExpandedDatasets(new Set());
    setSelectedDocs({});
    setDirectoryTree({ nodes: [], datasets: [] });
    setCurrentFolderId(ROOT);
    setExpandedFolderIds([]);
    setDatasetUsageCounts({});
  }, [user?.user_id]);

  const recordDatasetUsage = useCallback(
    (datasetName) => {
      const name = String(datasetName || '').trim();
      if (!name) return;
      setDatasetUsageCounts((previous) => {
        const next = {
          ...(previous || {}),
          [name]: Number(previous?.[name] || 0) + 1,
        };
        try {
          window.localStorage.setItem(usageStorageKey, JSON.stringify(next));
        } catch {
          // ignore storage errors
        }
        return next;
      });
    },
    [usageStorageKey]
  );

  useEffect(() => {
    setCanDeleteDocs(can('ragflow_documents', 'delete'));
    setCanUploadDocs(can('ragflow_documents', 'upload'));
  }, [can, user?.user_id]);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [datasetResponse, treeResponse] = await Promise.all([
          knowledgeApi.listRagflowDatasets(),
          knowledgeApi.listKnowledgeDirectories(),
        ]);
        const nextDatasets = datasetResponse;
        setDatasets(nextDatasets);
        setDirectoryTree(treeResponse);
        setError(nextDatasets.length ? null : TEXT.noPermission);
      } catch (requestError) {
        setError(requestError?.message || TEXT.loadKbFail);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [accessibleKbs, user]);

  const fetchDocumentsForDataset = useCallback(async (datasetName) => {
    try {
      setDocumentErrors((previous) => {
        const next = { ...previous };
        delete next[datasetName];
        return next;
      });
      const items = await documentBrowserApi.listDocuments(datasetName);
      setDocuments((previous) => ({ ...previous, [datasetName]: items }));
    } catch (requestError) {
      setDocumentErrors((previous) => ({
        ...previous,
        [datasetName]: requestError?.message || TEXT.loadDocFail,
      }));
      setDocuments((previous) => ({ ...previous, [datasetName]: [] }));
    }
  }, []);

  useEffect(() => {
    visibleDatasets.forEach((dataset) => {
      if (!documents[dataset.name]) fetchDocumentsForDataset(dataset.name);
    });
  }, [documents, fetchDocumentsForDataset, visibleDatasets]);

  useEffect(() => {
    if (!location.state?.documentId || datasetsWithFolders.length === 0) return undefined;

    const { documentId, documentName, datasetId } = location.state;
    const targetDataset = datasetsWithFolders.find((dataset) => dataset.id === datasetId);
    if (!targetDataset) {
      setError(`${TEXT.cannotFindKb}: ${datasetId}`);
      return undefined;
    }

    const datasetName = targetDataset.name || targetDataset.id;
    const nodeIds = pathNodes(targetDataset.node_id, indexes.byId).map((node) => node.id);
    setCurrentFolderId(targetDataset.node_id || ROOT);
    setExpandedFolderIds((previous) => Array.from(new Set([...previous, ...nodeIds])));
    setExpandedDatasets((previous) => new Set([...previous, datasetName]));

    if (!documents[datasetName]) fetchDocumentsForDataset(datasetName);

    const timer = setInterval(() => {
      if (documents[datasetName]) {
        clearInterval(timer);
        const target = documents[datasetName].find((doc) => doc.id === documentId);
        if (target) viewRef.current?.(documentId, datasetName);
        else {
          setError(`${TEXT.cannotFindDocPrefix} "${datasetName}" found no doc: ${documentName}`);
        }
      }
    }, 300);

    const timeout = setTimeout(() => clearInterval(timer), 10000);
    return () => {
      clearInterval(timer);
      clearTimeout(timeout);
    };
  }, [datasetsWithFolders, documents, fetchDocumentsForDataset, indexes.byId, location.state]);

  const toggleDataset = useCallback(
    (datasetName) => {
      setExpandedDatasets((previous) => {
        const next = new Set(previous);
        if (next.has(datasetName)) {
          next.delete(datasetName);
        } else {
          next.add(datasetName);
          recordDatasetUsage(datasetName);
        }
        return next;
      });
      if (!documents[datasetName]) fetchDocumentsForDataset(datasetName);
    },
    [documents, fetchDocumentsForDataset, recordDatasetUsage]
  );

  const openFolder = useCallback(
    (folderId) => {
      const next = folderId || ROOT;
      setCurrentFolderId(next);
      const pathIds = pathNodes(next, indexes.byId).map((node) => node.id);
      setExpandedFolderIds((previous) => Array.from(new Set([...previous, ...pathIds])));
    },
    [indexes.byId]
  );

  const toggleFolderExpand = useCallback((folderId) => {
    setExpandedFolderIds((previous) =>
      previous.includes(folderId)
        ? previous.filter((id) => id !== folderId)
        : [...previous, folderId]
    );
  }, []);

  const expandAll = useCallback(() => {
    setExpandedDatasets(new Set(datasetsInCurrentFolder.map((dataset) => dataset.name)));
    visibleDatasets.forEach((dataset) => {
      if (!documents[dataset.name]) fetchDocumentsForDataset(dataset.name);
    });
  }, [datasetsInCurrentFolder, documents, fetchDocumentsForDataset, visibleDatasets]);

  const collapseAll = useCallback(() => setExpandedDatasets(new Set()), []);

  const refreshAll = useCallback(() => {
    setDocuments({});
    visibleDatasets.forEach((dataset) => fetchDocumentsForDataset(dataset.name));
  }, [fetchDocumentsForDataset, visibleDatasets]);

  const handleView = useCallback((docId, datasetName) => {
    recordDatasetUsage(datasetName);
    const doc = documents[datasetName]?.find((item) => item.id === docId);
    setPreviewTarget({
      source: DOCUMENT_SOURCE.RAGFLOW,
      docId,
      datasetName,
      filename: doc?.name || `document_${docId}`,
    });
    setPreviewOpen(true);
  }, [documents, recordDatasetUsage]);
  viewRef.current = handleView;

  const handleDownload = useCallback(async (docId, datasetName) => {
    recordDatasetUsage(datasetName);
    const doc = documents[datasetName]?.find((item) => item.id === docId);
    try {
      setActionLoading((previous) => ({ ...previous, [`${docId}-download`]: true }));
      await documentsApi.downloadToBrowser({
        source: DOCUMENT_SOURCE.RAGFLOW,
        docId,
        datasetName,
        filename: doc?.name || `document_${docId}`,
      });
    } catch (requestError) {
      setError(requestError?.message || TEXT.downloadFail);
    } finally {
      setActionLoading((previous) => ({ ...previous, [`${docId}-download`]: false }));
    }
  }, [documents, recordDatasetUsage]);

  const handleDelete = useCallback(async (docId, datasetName) => {
    if (!window.confirm(TEXT.deleteConfirm)) return;
    try {
      setActionLoading((previous) => ({ ...previous, [`${docId}-delete`]: true }));
      await documentBrowserApi.deleteDocument(docId, datasetName);
      setDocuments((previous) => ({
        ...previous,
        [datasetName]: (previous[datasetName] || []).filter((item) => item.id !== docId),
      }));
    } catch (requestError) {
      setError(requestError?.message || TEXT.deleteFail);
    } finally {
      setActionLoading((previous) => ({ ...previous, [`${docId}-delete`]: false }));
    }
  }, []);

  const openSingleTransferDialog = useCallback(
    (docId, sourceDatasetName, operation) => {
      recordDatasetUsage(sourceDatasetName);
      const candidates = transferTargetOptions.filter(
        (name) => name !== sourceDatasetName
      );
      if (!candidates.length) {
        setError(TEXT.noTargetKb);
        return;
      }
      setTransferDialog({
        scope: 'single',
        operation,
        docId,
        sourceDatasetName,
        targetDatasetName: candidates[0],
      });
    },
    [recordDatasetUsage, transferTargetOptions]
  );

  const openQuickDataset = useCallback(
    (datasetRef) => {
      if (!datasetRef) return;
      const dataset =
        typeof datasetRef === 'string'
          ? datasetsWithFolders.find((item) => item.name === datasetRef || item.id === datasetRef)
          : datasetRef;
      if (!dataset) return;
      const datasetName = dataset.name || dataset.id;
      recordDatasetUsage(datasetName);
      const nodeIds = pathNodes(dataset.node_id, indexes.byId).map((node) => node.id);
      setCurrentFolderId(dataset.node_id || ROOT);
      setExpandedFolderIds((previous) => Array.from(new Set([...previous, ...nodeIds])));
      setExpandedDatasets((previous) => new Set([...previous, datasetName]));
      if (!documents[datasetName]) fetchDocumentsForDataset(datasetName);
    },
    [datasetsWithFolders, documents, fetchDocumentsForDataset, indexes.byId, recordDatasetUsage]
  );

  const handleSelectDoc = useCallback((docId, datasetName) => {
    setSelectedDocs((previous) => {
      const list = previous[datasetName] || [];
      return {
        ...previous,
        [datasetName]: list.includes(docId)
          ? list.filter((id) => id !== docId)
          : [...list, docId],
      };
    });
  }, []);

  const handleSelectAllInDataset = useCallback(
    (datasetName) => {
      const datasetDocs = documents[datasetName] || [];
      const current = selectedDocs[datasetName] || [];
      setSelectedDocs((previous) => ({
        ...previous,
        [datasetName]:
          current.length === datasetDocs.length ? [] : datasetDocs.map((doc) => doc.id),
      }));
    },
    [documents, selectedDocs]
  );

  const isDocSelected = useCallback(
    (docId, datasetName) => (selectedDocs[datasetName] || []).includes(docId),
    [selectedDocs]
  );

  const isAllSelectedInDataset = useCallback(
    (datasetName) => {
      const datasetDocs = documents[datasetName] || [];
      const current = selectedDocs[datasetName] || [];
      return datasetDocs.length > 0 && current.length === datasetDocs.length;
    },
    [documents, selectedDocs]
  );

  const selectedCount = useMemo(
    () => Object.values(selectedDocs).reduce((sum, list) => sum + list.length, 0),
    [selectedDocs]
  );

  const totalDocs = useMemo(
    () =>
      visibleDatasets.reduce(
        (sum, dataset) => sum + (documents[dataset.name] || []).length,
        0
      ),
    [documents, visibleDatasets]
  );

  const canDelete = useCallback(() => canDeleteDocs, [canDeleteDocs]);
  const canUpload = useCallback(() => canUploadDocs, [canUploadDocs]);
  const clearAllSelections = useCallback(() => setSelectedDocs({}), []);

  const handleBatchDownload = useCallback(async () => {
    const items = [];
    Object.entries(selectedDocs).forEach(([dataset, docIds]) => {
      docIds.forEach((docId) => {
        const doc = (documents[dataset] || []).find((item) => item.id === docId);
        if (doc) items.push({ doc_id: docId, dataset, name: doc.name });
      });
    });
    if (!items.length) {
      setError(TEXT.needOne);
      return;
    }

    try {
      setActionLoading((previous) => ({ ...previous, 'batch-download': true }));
      await documentsApi.batchDownloadRagflowToBrowser(items);
      clearAllSelections();
    } catch (requestError) {
      setError(requestError?.message || TEXT.batchFail);
    } finally {
      setActionLoading((previous) => ({ ...previous, 'batch-download': false }));
    }
  }, [clearAllSelections, documents, selectedDocs]);

  const collectSelectedTransferItems = useCallback(
    (targetDatasetName) => {
      const items = [];
      Object.entries(selectedDocs).forEach(([sourceDatasetName, docIds]) => {
        docIds.forEach((docId) => {
          if (!docId || !sourceDatasetName || sourceDatasetName === targetDatasetName) {
            return;
          }
          items.push({
            docId,
            sourceDatasetName,
            targetDatasetName,
          });
        });
      });
      return items;
    },
    [selectedDocs]
  );

  const clearTransferredMoveSelections = useCallback((results) => {
    const movedItems = Array.isArray(results) ? results : [];
    if (movedItems.length === 0) return;
    setSelectedDocs((previous) => {
      const next = { ...previous };
      let changed = false;
      movedItems.forEach((item) => {
        const sourceDatasetName = String(item?.sourceDatasetName || '').trim();
        const sourceDocId = String(item?.sourceDocId || '').trim();
        if (!sourceDatasetName || !sourceDocId) return;
        const current = Array.isArray(next[sourceDatasetName]) ? next[sourceDatasetName] : [];
        if (!current.includes(sourceDocId)) return;
        next[sourceDatasetName] = current.filter((id) => id !== sourceDocId);
        changed = true;
      });
      return changed ? next : previous;
    });
  }, []);

  const openBatchTransferDialog = useCallback(
    (operation) => {
      if (!transferTargetOptions.length) {
        setError(TEXT.noTargetKb);
        return;
      }
      setTransferDialog({
        scope: 'batch',
        operation,
        docId: '',
        sourceDatasetName: '',
        targetDatasetName: transferTargetOptions[0],
      });
    },
    [transferTargetOptions]
  );

  const executeSingleTransfer = useCallback(
    async ({ docId, sourceDatasetName, targetDatasetName, operation }) => {
      try {
        setActionLoading((previous) => ({ ...previous, [`${docId}-${operation}`]: true }));
        await documentBrowserApi.transferDocument(
          docId,
          sourceDatasetName,
          targetDatasetName,
          operation
        );
        await Promise.all([
          fetchDocumentsForDataset(sourceDatasetName),
          fetchDocumentsForDataset(targetDatasetName),
        ]);
        if (operation === 'move') {
          setSelectedDocs((previous) => {
            const list = previous[sourceDatasetName] || [];
            if (!list.includes(docId)) return previous;
            return {
              ...previous,
              [sourceDatasetName]: list.filter((id) => id !== docId),
            };
          });
        }
      } catch (requestError) {
        setError(requestError?.message || (operation === 'move' ? TEXT.moveFail : TEXT.copyFail));
      } finally {
        setActionLoading((previous) => ({ ...previous, [`${docId}-${operation}`]: false }));
      }
    },
    [fetchDocumentsForDataset]
  );

  const executeBatchTransfer = useCallback(
    async ({ targetDatasetName, operation }) => {
      const items = collectSelectedTransferItems(targetDatasetName);
      if (!items.length) {
        setError(TEXT.needOne);
        return;
      }

      const loadingKey = operation === 'move' ? 'batch-move' : 'batch-copy';
      const progress = {
        operation,
        total: items.length,
        processed: 0,
        success: 0,
        failed: 0,
        current: targetDatasetName,
        done: false,
      };

      setBatchTransferProgress(progress);
      setActionLoading((previous) => ({ ...previous, [loadingKey]: true }));

      try {
        const result = await documentBrowserApi.transferDocumentsBatch(items, operation);
        const affected = new Set([targetDatasetName]);
        items.forEach((item) => affected.add(item.sourceDatasetName));

        await Promise.all(
          Array.from(affected).map((datasetName) => fetchDocumentsForDataset(datasetName))
        );

        if (operation === 'move') {
          clearTransferredMoveSelections(result.results);
        }

        setBatchTransferProgress({
          ...progress,
          processed: result.total,
          success: result.successCount,
          failed: result.failedCount,
          current: '',
          done: true,
        });

        if (result.failedCount > 0) {
          const firstFailed = result.failed[0];
          window.alert(
            `Done ${result.successCount}/${result.total}, failed ${result.failedCount}\nSample: ${firstFailed.sourceDatasetName}/${firstFailed.docId}: ${firstFailed.detail}`
          );
        }
      } catch (requestError) {
        setError(requestError?.message || (operation === 'move' ? TEXT.moveFail : TEXT.copyFail));
        setBatchTransferProgress({
          ...progress,
          current: '',
          done: true,
        });
      } finally {
        setActionLoading((previous) => ({ ...previous, [loadingKey]: false }));
      }
    },
    [clearTransferredMoveSelections, collectSelectedTransferItems, fetchDocumentsForDataset]
  );

  const handleTransferConfirm = useCallback(async () => {
    if (!transferDialog?.targetDatasetName) {
      setError(TEXT.selectTargetKb);
      return;
    }
    const payload = { ...transferDialog };
    setTransferDialog(null);
    if (payload.scope === 'single') {
      await executeSingleTransfer(payload);
      return;
    }
    await executeBatchTransfer(payload);
  }, [executeBatchTransfer, executeSingleTransfer, transferDialog]);

  const commitKeyword = useCallback(
    (value) => {
      const keyword = String(value || '').trim();
      if (!keyword) return;
      const next = [keyword, ...recentDatasetKeywords]
        .filter(Boolean)
        .filter(
          (item, idx, arr) =>
            arr.findIndex((candidate) => candidate.toLowerCase() === item.toLowerCase()) ===
            idx
        )
        .slice(0, 5);

      setRecentDatasetKeywords(next);
      try {
        window.localStorage.setItem(
          `ragflowauth_recent_dataset_keywords_v1:${user?.user_id || 'anon'}`,
          JSON.stringify(next)
        );
      } catch {
        // ignore storage error
      }
    },
    [recentDatasetKeywords, user?.user_id]
  );

  return {
    canDownload,
    datasetsWithFolders,
    visibleDatasets,
    visibleNodeIds,
    indexes,
    currentFolderId,
    expandedFolderIds,
    folderBreadcrumb,
    datasetsInCurrentFolder,
    transferTargetOptions,
    datasetFilterKeyword,
    recentDatasetKeywords,
    quickDatasets,
    documents,
    documentErrors,
    loading,
    error,
    expandedDatasets,
    actionLoading,
    selectedDocs,
    previewOpen,
    previewTarget,
    transferDialog,
    batchTransferProgress,
    selectedCount,
    totalDocs,
    setDatasetFilterKeyword,
    setPreviewOpen,
    setPreviewTarget,
    setTransferDialog,
    setBatchTransferProgress,
    expandAll,
    collapseAll,
    refreshAll,
    openQuickDataset,
    toggleDataset,
    fetchDocumentsForDataset,
    isAllSelectedInDataset,
    handleSelectAllInDataset,
    isDocSelected,
    handleSelectDoc,
    handleView,
    handleDownload,
    handleDelete,
    openSingleTransferDialog,
    canDelete,
    canUpload,
    clearAllSelections,
    handleBatchDownload,
    openBatchTransferDialog,
    handleTransferConfirm,
    commitKeyword,
    openFolder,
    toggleFolderExpand,
  };
}
