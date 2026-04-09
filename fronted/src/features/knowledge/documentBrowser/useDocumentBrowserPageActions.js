import { useCallback } from 'react';

import { documentsApi } from '../../documents/api';
import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';
import { documentBrowserApi } from './api';
import {
  buildBatchDownloadItems,
  buildExpandedNodeIds,
  buildPreviewTarget,
  resolveDatasetReference,
} from './documentBrowserPageHelpers';
import { ROOT, TEXT } from './constants';

export default function useDocumentBrowserPageActions({
  canDeleteDocs,
  canUploadDocs,
  clearAllSelections,
  datasetsInCurrentFolder,
  datasetsWithFolders,
  documents,
  fetchDocumentsForDataset,
  indexesById,
  recordDatasetUsage,
  selectedDocs,
  setActionLoading,
  setCurrentFolderId,
  setDocuments,
  setError,
  setExpandedDatasets,
  setExpandedFolderIds,
  setPreviewOpen,
  setPreviewTarget,
  visibleDatasets,
}) {
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

      if (!documents[datasetName]) {
        fetchDocumentsForDataset(datasetName);
      }
    },
    [documents, fetchDocumentsForDataset, recordDatasetUsage, setExpandedDatasets]
  );

  const openFolder = useCallback(
    (folderId) => {
      const nextFolderId = folderId || ROOT;
      setCurrentFolderId(nextFolderId);

      const pathIds = buildExpandedNodeIds(nextFolderId, indexesById);
      setExpandedFolderIds((previous) => Array.from(new Set([...previous, ...pathIds])));
    },
    [indexesById, setCurrentFolderId, setExpandedFolderIds]
  );

  const toggleFolderExpand = useCallback((folderId) => {
    setExpandedFolderIds((previous) =>
      previous.includes(folderId)
        ? previous.filter((id) => id !== folderId)
        : [...previous, folderId]
    );
  }, [setExpandedFolderIds]);

  const expandAll = useCallback(() => {
    setExpandedDatasets(new Set(datasetsInCurrentFolder.map((dataset) => dataset.name)));
    visibleDatasets.forEach((dataset) => {
      if (!documents[dataset.name]) {
        fetchDocumentsForDataset(dataset.name);
      }
    });
  }, [
    datasetsInCurrentFolder,
    documents,
    fetchDocumentsForDataset,
    setExpandedDatasets,
    visibleDatasets,
  ]);

  const collapseAll = useCallback(() => {
    setExpandedDatasets(new Set());
  }, [setExpandedDatasets]);

  const refreshAll = useCallback(() => {
    setDocuments({});
    visibleDatasets.forEach((dataset) => fetchDocumentsForDataset(dataset.name));
  }, [fetchDocumentsForDataset, setDocuments, visibleDatasets]);

  const handleView = useCallback(
    (docId, datasetName) => {
      recordDatasetUsage(datasetName);
      setPreviewTarget(buildPreviewTarget(docId, datasetName, documents));
      setPreviewOpen(true);
    },
    [documents, recordDatasetUsage, setPreviewOpen, setPreviewTarget]
  );

  const handleDownload = useCallback(
    async (docId, datasetName) => {
      recordDatasetUsage(datasetName);

      try {
        setActionLoading((previous) => ({ ...previous, [`${docId}-download`]: true }));
        await documentsApi.downloadToBrowser(buildPreviewTarget(docId, datasetName, documents));
      } catch (requestError) {
        setError(mapUserFacingErrorMessage(requestError?.message, TEXT.downloadFail));
      } finally {
        setActionLoading((previous) => ({ ...previous, [`${docId}-download`]: false }));
      }
    },
    [documents, recordDatasetUsage, setActionLoading, setError]
  );

  const handleDelete = useCallback(
    async (docId, datasetName) => {
      if (!window.confirm(TEXT.deleteConfirm)) return;

      try {
        setActionLoading((previous) => ({ ...previous, [`${docId}-delete`]: true }));
        await documentBrowserApi.deleteDocument(docId, datasetName);
        setDocuments((previous) => ({
          ...previous,
          [datasetName]: (previous[datasetName] || []).filter((item) => item.id !== docId),
        }));
      } catch (requestError) {
        setError(mapUserFacingErrorMessage(requestError?.message, TEXT.deleteFail));
      } finally {
        setActionLoading((previous) => ({ ...previous, [`${docId}-delete`]: false }));
      }
    },
    [setActionLoading, setDocuments, setError]
  );

  const openQuickDataset = useCallback(
    (datasetRef) => {
      const dataset = resolveDatasetReference(datasetRef, datasetsWithFolders);
      if (!dataset) return;

      const datasetName = dataset.name || dataset.id;
      recordDatasetUsage(datasetName);

      const nodeIds = buildExpandedNodeIds(dataset.node_id, indexesById);
      setCurrentFolderId(dataset.node_id || ROOT);
      setExpandedFolderIds((previous) => Array.from(new Set([...previous, ...nodeIds])));
      setExpandedDatasets((previous) => new Set([...previous, datasetName]));

      if (!documents[datasetName]) {
        fetchDocumentsForDataset(datasetName);
      }
    },
    [
      datasetsWithFolders,
      documents,
      fetchDocumentsForDataset,
      indexesById,
      recordDatasetUsage,
      setCurrentFolderId,
      setExpandedDatasets,
      setExpandedFolderIds,
    ]
  );

  const handleBatchDownload = useCallback(async () => {
    const items = buildBatchDownloadItems(selectedDocs, documents);
    if (!items.length) {
      setError(TEXT.needOne);
      return;
    }

    try {
      setActionLoading((previous) => ({ ...previous, 'batch-download': true }));
      await documentsApi.batchDownloadRagflowToBrowser(items);
      clearAllSelections();
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, TEXT.batchFail));
    } finally {
      setActionLoading((previous) => ({ ...previous, 'batch-download': false }));
    }
  }, [clearAllSelections, documents, selectedDocs, setActionLoading, setError]);

  const canDelete = useCallback(() => canDeleteDocs, [canDeleteDocs]);
  const canUpload = useCallback(() => canUploadDocs, [canUploadDocs]);

  return {
    toggleDataset,
    openFolder,
    toggleFolderExpand,
    expandAll,
    collapseAll,
    refreshAll,
    handleView,
    handleDownload,
    handleDelete,
    openQuickDataset,
    handleBatchDownload,
    canDelete,
    canUpload,
  };
}
