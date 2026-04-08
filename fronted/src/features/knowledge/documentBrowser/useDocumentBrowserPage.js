import { useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';

import { useAuth } from '../../../hooks/useAuth';
import { ROOT } from './constants';
import useDocumentBrowserData from './useDocumentBrowserData';
import useDocumentBrowserDerivedState from './useDocumentBrowserDerivedState';
import useDocumentBrowserPageActions from './useDocumentBrowserPageActions';
import useDocumentBrowserPageEffects from './useDocumentBrowserPageEffects';
import useDocumentBrowserPreferences from './useDocumentBrowserPreferences';
import useDocumentBrowserSelection from './useDocumentBrowserSelection';
import useDocumentBrowserTransfer from './useDocumentBrowserTransfer';
import { buildDatasetsWithFolders, buildIndexes } from './treeUtils';

export default function useDocumentBrowserPage() {
  const location = useLocation();
  const { user, can, canDownload, accessibleKbs } = useAuth();

  const [expandedDatasets, setExpandedDatasets] = useState(new Set());
  const [actionLoading, setActionLoading] = useState({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTarget, setPreviewTarget] = useState(null);
  const [currentFolderId, setCurrentFolderId] = useState(ROOT);
  const [expandedFolderIds, setExpandedFolderIds] = useState([]);

  const {
    datasets,
    directoryTree,
    documents,
    setDocuments,
    documentErrors,
    loading,
    error,
    setError,
    canDeleteDocs,
    canUploadDocs,
    fetchDocumentsForDataset,
  } = useDocumentBrowserData({ can, accessibleKbs, user });

  const indexes = useMemo(() => buildIndexes(directoryTree), [directoryTree]);
  const datasetsWithFolders = useMemo(
    () => buildDatasetsWithFolders(datasets, directoryTree),
    [datasets, directoryTree]
  );

  const preferences = useDocumentBrowserPreferences({
    userId: user?.user_id,
    datasetsWithFolders,
  });

  const derivedState = useDocumentBrowserDerivedState({
    currentFolderId,
    datasetFilterKeyword: preferences.datasetFilterKeyword,
    datasetsWithFolders,
    documents,
    indexes,
  });

  const {
    selectedDocs,
    setSelectedDocs,
    selectedCount,
    handleSelectDoc,
    handleSelectAllInDataset,
    isDocSelected,
    isAllSelectedInDataset,
    clearAllSelections,
    clearTransferredMoveSelections,
  } = useDocumentBrowserSelection({
    documents,
    resetKey: user?.user_id,
  });

  const {
    transferDialog,
    setTransferDialog,
    batchTransferProgress,
    setBatchTransferProgress,
    openSingleTransferDialog,
    openBatchTransferDialog,
    handleTransferConfirm,
  } = useDocumentBrowserTransfer({
    resetKey: user?.user_id,
    selectedDocs,
    setSelectedDocs,
    transferTargetOptions: derivedState.transferTargetOptions,
    fetchDocumentsForDataset,
    recordDatasetUsage: preferences.recordDatasetUsage,
    clearTransferredMoveSelections,
    setActionLoading,
    setError,
  });

  const actions = useDocumentBrowserPageActions({
    canDeleteDocs,
    canUploadDocs,
    clearAllSelections,
    datasetsInCurrentFolder: derivedState.datasetsInCurrentFolder,
    datasetsWithFolders,
    documents,
    fetchDocumentsForDataset,
    indexesById: indexes.byId,
    recordDatasetUsage: preferences.recordDatasetUsage,
    selectedDocs,
    setActionLoading,
    setCurrentFolderId,
    setDocuments,
    setError,
    setExpandedDatasets,
    setExpandedFolderIds,
    setPreviewOpen,
    setPreviewTarget,
    visibleDatasets: derivedState.visibleDatasets,
  });

  useDocumentBrowserPageEffects({
    datasetsWithFolders,
    documents,
    fetchDocumentsForDataset,
    handleView: actions.handleView,
    indexesById: indexes.byId,
    locationState: location.state,
    setActionLoading,
    setCurrentFolderId,
    setError,
    setExpandedDatasets,
    setExpandedFolderIds,
    setPreviewOpen,
    setPreviewTarget,
    userId: user?.user_id,
    visibleDatasets: derivedState.visibleDatasets,
  });

  return {
    canDownload,
    datasetsWithFolders,
    visibleDatasets: derivedState.visibleDatasets,
    visibleNodeIds: derivedState.visibleNodeIds,
    indexes,
    currentFolderId,
    expandedFolderIds,
    folderBreadcrumb: derivedState.folderBreadcrumb,
    datasetsInCurrentFolder: derivedState.datasetsInCurrentFolder,
    transferTargetOptions: derivedState.transferTargetOptions,
    datasetFilterKeyword: preferences.datasetFilterKeyword,
    recentDatasetKeywords: preferences.recentDatasetKeywords,
    quickDatasets: preferences.quickDatasets,
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
    totalDocs: derivedState.totalDocs,
    setDatasetFilterKeyword: preferences.setDatasetFilterKeyword,
    setPreviewOpen,
    setPreviewTarget,
    setTransferDialog,
    setBatchTransferProgress,
    expandAll: actions.expandAll,
    collapseAll: actions.collapseAll,
    refreshAll: actions.refreshAll,
    openQuickDataset: actions.openQuickDataset,
    toggleDataset: actions.toggleDataset,
    fetchDocumentsForDataset,
    isAllSelectedInDataset,
    handleSelectAllInDataset,
    isDocSelected,
    handleSelectDoc,
    handleView: actions.handleView,
    handleDownload: actions.handleDownload,
    handleDelete: actions.handleDelete,
    openSingleTransferDialog,
    canDelete: actions.canDelete,
    canUpload: actions.canUpload,
    clearAllSelections,
    handleBatchDownload: actions.handleBatchDownload,
    openBatchTransferDialog,
    handleTransferConfirm,
    commitKeyword: preferences.commitKeyword,
    openFolder: actions.openFolder,
    toggleFolderExpand: actions.toggleFolderExpand,
  };
}
