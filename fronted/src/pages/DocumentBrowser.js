import React from 'react';
import { TEXT } from '../features/knowledge/documentBrowser/constants';
import BatchTransferProgress from '../features/knowledge/documentBrowser/components/BatchTransferProgress';
import DatasetPanel from '../features/knowledge/documentBrowser/components/DatasetPanel';
import FolderTree from '../features/knowledge/documentBrowser/components/FolderTree';
import TransferDialog from '../features/knowledge/documentBrowser/components/TransferDialog';
import useDocumentBrowserPage from '../features/knowledge/documentBrowser/useDocumentBrowserPage';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';
import '../features/knowledge/documentBrowser/browserMedical.css';

const BTN_VARIANT = {
  primary: 'medui-btn medui-btn--primary',
  neutral: 'medui-btn medui-btn--neutral',
  success: 'medui-btn medui-btn--success',
  accent: 'medui-btn medui-btn--secondary',
  danger: 'medui-btn medui-btn--danger',
};

export default function DocumentBrowser() {
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
    totalDocs,
    setDatasetFilterKeyword,
    setPreviewOpen,
    setPreviewTarget,
    setTransferDialog,
    setBatchTransferProgress,
    expandAll,
    collapseAll,
    refreshAll,
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
  } = useDocumentBrowserPage();

  if (loading) {
    return <div className="medui-empty" style={{ height: 320, display: 'grid', placeItems: 'center' }}>{TEXT.loading}</div>;
  }

  return (
    <div data-testid="browser-page" className="browser-med-page">
      <div className="browser-med-head">
        <h2 style={{ margin: '0 0 8px 0', color: '#163f63' }}>{TEXT.title}</h2>
        <p className="medui-subtitle" style={{ margin: 0 }}>{TEXT.desc}</p>
      </div>

      <div className="browser-med-toolbar">
        <button onClick={expandAll} data-testid="browser-expand-all" className={BTN_VARIANT.primary}>
          {TEXT.expandAll}
        </button>
        <button onClick={collapseAll} data-testid="browser-collapse-all" className={BTN_VARIANT.neutral}>
          {TEXT.collapseAll}
        </button>
        <button onClick={refreshAll} data-testid="browser-refresh-all" className={BTN_VARIANT.success}>
          {TEXT.refresh}
        </button>
        {selectedCount > 0 && canDownload() ? (
          <button onClick={handleBatchDownload} data-testid="browser-batch-download" className={BTN_VARIANT.accent}>
            {actionLoading['batch-download'] ? TEXT.packing : `${TEXT.batch} (${selectedCount})`}
          </button>
        ) : null}
        {selectedCount > 0 && canUpload() ? (
          <button onClick={() => openBatchTransferDialog('copy')} data-testid="browser-batch-copy" className={BTN_VARIANT.primary}>
            {actionLoading['batch-copy'] ? TEXT.loading : `${TEXT.batchCopy} (${selectedCount})`}
          </button>
        ) : null}
        {selectedCount > 0 && canUpload() && canDelete() ? (
          <button onClick={() => openBatchTransferDialog('move')} data-testid="browser-batch-move" className={BTN_VARIANT.neutral}>
            {actionLoading['batch-move'] ? TEXT.loading : `${TEXT.batchMove} (${selectedCount})`}
          </button>
        ) : null}
        {selectedCount > 0 && (canDownload() || canUpload()) ? (
          <button onClick={clearAllSelections} data-testid="browser-clear-selection" className={BTN_VARIANT.danger}>
            {TEXT.clearSelection}
          </button>
        ) : null}
      </div>

      <div className="medui-surface medui-card-pad">
        <div className="browser-med-stats">
          <div>
            {TEXT.datasets}: <strong>{visibleDatasets.length}{visibleDatasets.length !== datasetsWithFolders.length ? ` / ${datasetsWithFolders.length}` : ''}</strong>
          </div>
          <div>
            {TEXT.docs}: <strong>{totalDocs}</strong>
          </div>
        </div>
      </div>

      <div className="medui-surface medui-card-pad">
        <div className="medui-subtitle" style={{ marginBottom: 6 }}>{TEXT.filter}</div>
        <div className="browser-med-filter">
          <input
            value={datasetFilterKeyword}
            onChange={(event) => setDatasetFilterKeyword(event.target.value)}
            onBlur={() => commitKeyword(datasetFilterKeyword)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') commitKeyword(datasetFilterKeyword);
            }}
            placeholder={TEXT.filterPlaceholder}
            data-testid="browser-dataset-filter"
            list="browser-dataset-filter-recent"
            className="medui-input"
            style={{ flex: 1 }}
          />
          <button onClick={() => setDatasetFilterKeyword('')} data-testid="browser-dataset-filter-clear" className={BTN_VARIANT.neutral}>
            {TEXT.clear}
          </button>
        </div>
        <datalist id="browser-dataset-filter-recent">
          {recentDatasetKeywords.map((value) => (
            <option key={value} value={value} />
          ))}
        </datalist>
        {recentDatasetKeywords.length ? (
          <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <div className="medui-subtitle">{TEXT.recent}</div>
            {recentDatasetKeywords.map((value) => (
              <button key={value} onClick={() => setDatasetFilterKeyword(value)} className={BTN_VARIANT.neutral} style={{ height: 30, padding: '0 10px' }}>
                {value}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {error ? (
        <div className="browser-med-error" data-testid="browser-error">
          {error}
        </div>
      ) : null}

      <BatchTransferProgress progress={batchTransferProgress} onClose={() => setBatchTransferProgress(null)} />

      {!datasetsWithFolders.length ? <div className="browser-med-empty">{TEXT.noKb}</div> : null}

      {datasetsWithFolders.length && !visibleDatasets.length ? (
        <div className="browser-med-empty">
          <div style={{ fontWeight: 700, color: '#365776', marginBottom: 6 }}>{TEXT.noMatch}</div>
          <div>{TEXT.noMatchDesc}</div>
        </div>
      ) : null}

      {datasetsWithFolders.length && visibleDatasets.length ? (
        <div className="browser-med-grid">
          <div className="medui-surface medui-card-pad browser-med-sticky">
            <FolderTree
              indexes={indexes}
              currentFolderId={currentFolderId}
              expandedFolderIds={expandedFolderIds}
              onToggleExpand={toggleFolderExpand}
              onOpenFolder={openFolder}
              visibleNodeIds={visibleNodeIds}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="medui-surface medui-card-pad">
              <div className="medui-subtitle" style={{ marginBottom: 8 }}>{TEXT.currentFolder}</div>
              <div className="browser-med-breadcrumb">
                {folderBreadcrumb.map((item, idx) => (
                  <React.Fragment key={item.id || `root-${idx}`}>
                    <button
                      type="button"
                      onClick={() => openFolder(item.id)}
                      className={currentFolderId === item.id ? 'is-current' : ''}
                    >
                      {item.name}
                    </button>
                    {idx < folderBreadcrumb.length - 1 ? <span style={{ color: '#9ca3af' }}>{'>'}</span> : null}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {datasetsInCurrentFolder.length ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
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
                    handleCopy={(docId, datasetName) => openSingleTransferDialog(docId, datasetName, 'copy')}
                    handleMove={(docId, datasetName) => openSingleTransferDialog(docId, datasetName, 'move')}
                    actionLoading={actionLoading}
                    canDownload={canDownload}
                    canUpload={canUpload}
                    canDelete={canDelete}
                  />
                ))}
              </div>
            ) : (
              <div className="browser-med-empty">{TEXT.emptyFolder}</div>
            )}
          </div>
        </div>
      ) : null}

      <DocumentPreviewModal
        open={previewOpen}
        target={previewTarget}
        onClose={() => {
          setPreviewOpen(false);
          setPreviewTarget(null);
        }}
        canDownloadFiles={typeof canDownload === 'function' ? !!canDownload() : false}
      />
      <TransferDialog
        transferDialog={transferDialog}
        selectedCount={selectedCount}
        transferTargetOptions={transferTargetOptions}
        onClose={() => setTransferDialog(null)}
        onConfirm={handleTransferConfirm}
        onChangeTarget={(targetDatasetName) =>
          setTransferDialog((previous) => ({ ...previous, targetDatasetName }))
        }
      />
    </div>
  );
}
