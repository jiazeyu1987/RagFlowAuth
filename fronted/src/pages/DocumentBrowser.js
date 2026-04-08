import React, { useEffect, useState } from 'react';

import BatchTransferProgress from '../features/knowledge/documentBrowser/components/BatchTransferProgress';
import DocumentBrowserDialogs from '../features/knowledge/documentBrowser/components/DocumentBrowserDialogs';
import DocumentBrowserFilterPanel from '../features/knowledge/documentBrowser/components/DocumentBrowserFilterPanel';
import DocumentBrowserQuickDatasets from '../features/knowledge/documentBrowser/components/DocumentBrowserQuickDatasets';
import DocumentBrowserWorkspace from '../features/knowledge/documentBrowser/components/DocumentBrowserWorkspace';
import { TEXT } from '../features/knowledge/documentBrowser/constants';
import useDocumentBrowserPage from '../features/knowledge/documentBrowser/useDocumentBrowserPage';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function DocumentBrowser() {
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const {
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
    documents,
    documentErrors,
    loading,
    error,
    expandedDatasets,
    actionLoading,
    previewOpen,
    previewTarget,
    transferDialog,
    batchTransferProgress,
    selectedCount,
    setDatasetFilterKeyword,
    setPreviewOpen,
    setPreviewTarget,
    setTransferDialog,
    setBatchTransferProgress,
    quickDatasets,
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
    handleTransferConfirm,
    commitKeyword,
    openFolder,
    toggleFolderExpand,
  } = useDocumentBrowserPage();

  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: 400,
          color: '#6b7280',
        }}
      >
        {TEXT.loading}
      </div>
    );
  }

  return (
    <div data-testid="browser-page">
      <DocumentBrowserQuickDatasets
        isMobile={isMobile}
        quickDatasets={quickDatasets}
        onOpenQuickDataset={openQuickDataset}
      />

      <DocumentBrowserFilterPanel
        isMobile={isMobile}
        datasetFilterKeyword={datasetFilterKeyword}
        recentDatasetKeywords={recentDatasetKeywords}
        setDatasetFilterKeyword={setDatasetFilterKeyword}
        commitKeyword={commitKeyword}
      />

      {error ? (
        <div
          style={{
            background: '#fee2e2',
            color: '#991b1b',
            padding: '12px 16px',
            borderRadius: 4,
            marginBottom: 20,
          }}
          data-testid="browser-error"
        >
          {error}
        </div>
      ) : null}

      <BatchTransferProgress
        progress={batchTransferProgress}
        onClose={() => setBatchTransferProgress(null)}
      />

      <DocumentBrowserWorkspace
        actionLoading={actionLoading}
        canDelete={canDelete}
        canDownload={canDownload}
        canUpload={canUpload}
        currentFolderId={currentFolderId}
        datasetsInCurrentFolder={datasetsInCurrentFolder}
        datasetsWithFolders={datasetsWithFolders}
        documentErrors={documentErrors}
        documents={documents}
        expandedDatasets={expandedDatasets}
        expandedFolderIds={expandedFolderIds}
        fetchDocumentsForDataset={fetchDocumentsForDataset}
        folderBreadcrumb={folderBreadcrumb}
        indexes={indexes}
        isAllSelectedInDataset={isAllSelectedInDataset}
        isDocSelected={isDocSelected}
        isMobile={isMobile}
        handleDelete={handleDelete}
        handleDownload={handleDownload}
        handleSelectAllInDataset={handleSelectAllInDataset}
        handleSelectDoc={handleSelectDoc}
        handleView={handleView}
        onCopyDoc={(docId, datasetName) => openSingleTransferDialog(docId, datasetName, 'copy')}
        onMoveDoc={(docId, datasetName) => openSingleTransferDialog(docId, datasetName, 'move')}
        openFolder={openFolder}
        toggleDataset={toggleDataset}
        toggleFolderExpand={toggleFolderExpand}
        visibleDatasets={visibleDatasets}
        visibleNodeIds={visibleNodeIds}
      />

      <DocumentBrowserDialogs
        canDownload={canDownload}
        handleTransferConfirm={handleTransferConfirm}
        previewOpen={previewOpen}
        previewTarget={previewTarget}
        selectedCount={selectedCount}
        setPreviewOpen={setPreviewOpen}
        setPreviewTarget={setPreviewTarget}
        setTransferDialog={setTransferDialog}
        transferDialog={transferDialog}
        transferTargetOptions={transferTargetOptions}
      />
    </div>
  );
}
