import { useEffect, useRef } from 'react';

import {
  buildExpandedNodeIds,
  resolveDatasetReference,
} from './documentBrowserPageHelpers';
import { ROOT, TEXT } from './constants';

export default function useDocumentBrowserPageEffects({
  datasetsWithFolders,
  documents,
  fetchDocumentsForDataset,
  handleView,
  indexesById,
  locationState,
  setActionLoading,
  setCurrentFolderId,
  setError,
  setExpandedDatasets,
  setExpandedFolderIds,
  setPreviewOpen,
  setPreviewTarget,
  userId,
  visibleDatasets,
}) {
  const handleViewRef = useRef(handleView);

  useEffect(() => {
    handleViewRef.current = handleView;
  }, [handleView]);

  useEffect(() => {
    setExpandedDatasets(new Set());
    setActionLoading({});
    setPreviewOpen(false);
    setPreviewTarget(null);
    setCurrentFolderId(ROOT);
    setExpandedFolderIds([]);
  }, [
    setActionLoading,
    setCurrentFolderId,
    setExpandedDatasets,
    setExpandedFolderIds,
    setPreviewOpen,
    setPreviewTarget,
    userId,
  ]);

  useEffect(() => {
    visibleDatasets.forEach((dataset) => {
      if (!documents[dataset.name]) {
        fetchDocumentsForDataset(dataset.name);
      }
    });
  }, [documents, fetchDocumentsForDataset, visibleDatasets]);

  useEffect(() => {
    if (!locationState?.documentId || datasetsWithFolders.length === 0) return undefined;

    const { documentId, documentName, datasetId } = locationState;
    const targetDataset = resolveDatasetReference(datasetId, datasetsWithFolders);

    if (!targetDataset) {
      setError(`${TEXT.cannotFindKb}: ${datasetId}`);
      return undefined;
    }

    const datasetName = targetDataset.name || targetDataset.id;
    const nodeIds = buildExpandedNodeIds(targetDataset.node_id, indexesById);

    setCurrentFolderId(targetDataset.node_id || ROOT);
    setExpandedFolderIds((previous) => Array.from(new Set([...previous, ...nodeIds])));
    setExpandedDatasets((previous) => new Set([...previous, datasetName]));

    if (!documents[datasetName]) {
      fetchDocumentsForDataset(datasetName);
    }

    const timer = setInterval(() => {
      const datasetDocuments = documents[datasetName];
      if (!datasetDocuments) return;

      clearInterval(timer);
      const target = datasetDocuments.find((doc) => doc.id === documentId);
      if (target) {
        handleViewRef.current?.(documentId, datasetName);
        return;
      }

      setError(`${TEXT.cannotFindDocPrefix} "${datasetName}" found no doc: ${documentName}`);
    }, 300);

    const timeout = setTimeout(() => clearInterval(timer), 10000);

    return () => {
      clearInterval(timer);
      clearTimeout(timeout);
    };
  }, [
    datasetsWithFolders,
    documents,
    fetchDocumentsForDataset,
    indexesById,
    locationState,
    setCurrentFolderId,
    setError,
    setExpandedDatasets,
    setExpandedFolderIds,
  ]);
}
